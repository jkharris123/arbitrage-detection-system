#!/usr/bin/env python3
"""
Enhanced OpenAI (GPT-4o-mini) Contract Matching System
Handles individual contract matching with specific thresholds
Using GPT-4o-mini for best cost effectiveness and performance
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
import csv
from dataclasses import dataclass, asdict
import sys

# Add paths
sys.path.append('./data_collectors')
sys.path.append('./arbitrage')

from kalshi_client import KalshiClient
from polymarket_client import EnhancedPolymarketClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ContractMatch:
    """Represents a matched individual contract pair"""
    kalshi_ticker: str
    kalshi_question: str
    kalshi_event_ticker: str
    polymarket_condition_id: str
    polymarket_question: str
    confidence: float
    match_type: str  # 'exact', 'threshold', 'similar', 'fuzzy'
    threshold_value: Optional[float]  # For threshold-based matches (e.g., >3.0%)
    notes: str
    matched_at: str
    expiry_alignment: bool  # Do expiry dates align?
    
    def to_csv_row(self):
        """Convert to CSV row format"""
        return [
            self.kalshi_ticker,
            self.kalshi_question,
            self.polymarket_condition_id,
            self.polymarket_question,
            self.confidence,
            self.match_type,
            self.notes,
            'YES' if self.confidence > 0.8 else 'NO',
            'SAFE_FOR_AUTOMATION' if self.confidence > 0.9 else 'NEEDS_REVIEW'
        ]

class EnhancedOpenAIMatchingSystem:
    """Enhanced system that matches individual contracts using OpenAI GPT-3.5-turbo"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.kalshi_client = KalshiClient()
        self.matches_file = "output/enhanced_matches.csv"
        self.cache_file = "data/enhanced_match_cache.json"
        self.cache = self._load_cache()
        
        # Enhanced matching prompt
        self.matching_prompt = """You are an expert at matching prediction market contracts between Kalshi and Polymarket.

CRITICAL RULES:
1. Match INDIVIDUAL contracts, not just event groups
2. For events with multiple thresholds (like Fed rates: 0%, 0.25%, 0.5%), match each specific threshold
3. Pay attention to exact numerical values - "above 3.0%" must match "above 3.0%", NOT "above 3.5%"
4. Consider date alignment - contracts should expire around the same time
5. Binary outcomes must be equivalent (YES on one side = NO on the other is OK)

For each match, provide:
- kalshi_ticker: The specific Kalshi contract ticker
- polymarket_condition_id: The specific Polymarket condition ID
- confidence: 0.0-1.0 (use 0.9+ for exact matches, 0.7-0.9 for very similar)
- match_type: 'exact', 'threshold', 'similar', or 'fuzzy'
- threshold_value: The specific threshold if applicable (e.g., 3.0 for "above 3.0%")
- notes: Brief explanation of the match

Return ONLY a JSON array of matches. Focus on HIGH CONFIDENCE matches only. No additional text."""
    
    def _load_cache(self) -> Dict:
        """Load match cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {"matches": {}, "last_updated": None}
    
    def _save_cache(self):
        """Save match cache"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        self.cache["last_updated"] = datetime.now().isoformat()
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    async def fetch_live_markets(self) -> Tuple[List[Dict], List[Dict]]:
        """Fetch current markets from both platforms"""
        logger.info("📡 Fetching live markets from both platforms...")
        
        # Kalshi markets with filtering
        kalshi_markets = self.kalshi_client.get_markets_by_criteria(
            min_liquidity_usd=500,
            max_days_to_expiry=14,
            min_volume=50,
            status_filter=['active', 'open']
        )
        
        # Polymarket markets
        async with EnhancedPolymarketClient() as poly_client:
            poly_markets = await poly_client.get_markets_by_criteria(
                min_volume_usd=500,
                max_days_to_expiry=14,
                limit=3000
            )
            # Convert to dict format
            poly_dicts = []
            for market in poly_markets:
                poly_dict = {
                    'condition_id': market.condition_id,
                    'question': market.question,
                    'description': market.description[:200] if market.description else '',
                    'yes_price': market.yes_token.price if market.yes_token else 0,
                    'no_price': market.no_token.price if market.no_token else 0,
                    'volume_24h': market.volume_24h,
                    'liquidity': market.liquidity,
                    'end_date': market.end_date_iso,
                    'tags': ','.join(market.tags) if hasattr(market, 'tags') else ''
                }
                poly_dicts.append(poly_dict)
        
        logger.info(f"✅ Fetched {len(kalshi_markets)} Kalshi and {len(poly_dicts)} Polymarket markets")
        return kalshi_markets, poly_dicts
    
    def group_kalshi_by_event(self, kalshi_markets: List[Dict]) -> Dict[str, List[Dict]]:
        """Group Kalshi markets by event ticker to identify multi-threshold events"""
        events = {}
        for market in kalshi_markets:
            event_ticker = market.get('event_ticker', 'UNKNOWN')
            if event_ticker not in events:
                events[event_ticker] = []
            events[event_ticker].append(market)
        
        # Log events with multiple contracts
        multi_contract_events = {k: v for k, v in events.items() if len(v) > 1}
        if multi_contract_events:
            logger.info(f"📊 Found {len(multi_contract_events)} events with multiple contracts:")
            for event, contracts in list(multi_contract_events.items())[:5]:
                logger.info(f"   {event}: {len(contracts)} contracts")
                for contract in contracts[:3]:
                    logger.info(f"      - {contract['ticker']}: {contract.get('title', '')[:50]}...")
        
        return events
    
    def extract_threshold_value(self, question: str) -> Optional[float]:
        """Extract numerical threshold from question text"""
        import re
        
        # Patterns for common threshold formats
        patterns = [
            r'above (\d+\.?\d*)%?',
            r'below (\d+\.?\d*)%?',
            r'greater than (\d+\.?\d*)%?',
            r'less than (\d+\.?\d*)%?',
            r'over (\d+\.?\d*)%?',
            r'under (\d+\.?\d*)%?',
            r'(\d+\.?\d*)%? or (higher|lower|more|less)',
            r'between (\d+\.?\d*)%? and (\d+\.?\d*)%?'
        ]
        
        question_lower = question.lower()
        for pattern in patterns:
            match = re.search(pattern, question_lower)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        
        return None
    
    async def match_contracts_with_openai(self, kalshi_batch: List[Dict], 
                                        poly_markets: List[Dict]) -> List[ContractMatch]:
        """Send batch to OpenAI for matching"""
        try:
            # Import openai - install with: pip install openai
            try:
                import openai
            except ImportError:
                logger.error("openai package not installed! Run: pip install openai")
                return []
            
            openai.api_key = self.api_key
            
            # Prepare market summaries
            kalshi_summary = self._prepare_kalshi_summary(kalshi_batch)
            poly_summary = self._prepare_polymarket_summary(poly_markets)
            
            message = f"""{self.matching_prompt}

## Kalshi Contracts ({len(kalshi_batch)} contracts)
{kalshi_summary}

## Polymarket Contracts ({len(poly_markets)} contracts)
{poly_summary}

Analyze these contracts and return matches as a JSON array. Remember to match INDIVIDUAL contracts with specific thresholds."""

            # Call OpenAI API with GPT-4o-mini (most cost effective)
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # Using GPT-4o-mini for best cost/performance ratio
                messages=[
                    {"role": "system", "content": "You are a prediction market contract matching expert. Always return valid JSON arrays only."},
                    {"role": "user", "content": message}
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=2048,  # Reasonable limit for cost control
                n=1
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            matches = self._parse_openai_response(response_text, kalshi_batch, poly_markets)
            return matches
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return []
    
    def _prepare_kalshi_summary(self, markets: List[Dict]) -> str:
        """Prepare Kalshi markets summary for OpenAI"""
        lines = []
        for market in markets:
            ticker = market.get('ticker', '')
            title = market.get('title', '')
            question = market.get('question', title)
            event = market.get('event_ticker', '')
            expiry = market.get('close_time', '')[:10]  # Date only
            
            # Extract threshold if present
            threshold = self.extract_threshold_value(question)
            threshold_str = f" [Threshold: {threshold}]" if threshold else ""
            
            lines.append(f"{ticker} ({event}): {question}{threshold_str} - Expires: {expiry}")
        
        return "\n".join(lines)
    
    def _prepare_polymarket_summary(self, markets: List[Dict]) -> str:
        """Prepare Polymarket summary for OpenAI"""
        lines = []
        for market in markets[:200]:  # Limit to avoid token limits
            cond_id = market.get('condition_id', '')[:16]
            question = market.get('question', '')
            end_date = market.get('end_date', '')[:10]  # Date only
            
            # Extract threshold if present
            threshold = self.extract_threshold_value(question)
            threshold_str = f" [Threshold: {threshold}]" if threshold else ""
            
            lines.append(f"{cond_id}...: {question}{threshold_str} - Expires: {end_date}")
        
        if len(markets) > 200:
            lines.append(f"... and {len(markets) - 200} more markets")
        
        return "\n".join(lines)
    
    def _parse_openai_response(self, response_text: str, 
                             kalshi_markets: List[Dict], 
                             poly_markets: List[Dict]) -> List[ContractMatch]:
        """Parse OpenAI's response into ContractMatch objects"""
        matches = []
        
        try:
            # Extract JSON from response
            import re
            # Try to find JSON array in the response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                # If no array found, try to parse the whole response
                json_text = response_text.strip()
            
            match_data = json.loads(json_text)
            
            # Create lookup dictionaries
            kalshi_lookup = {m['ticker']: m for m in kalshi_markets}
            poly_lookup = {m['condition_id']: m for m in poly_markets}
            
            for match in match_data:
                try:
                    kalshi_ticker = match['kalshi_ticker']
                    poly_cond_id = match['polymarket_condition_id']
                    
                    # Get full market data
                    kalshi_market = kalshi_lookup.get(kalshi_ticker, {})
                    poly_market = poly_lookup.get(poly_cond_id, {})
                    
                    # Check expiry alignment
                    expiry_aligned = self._check_expiry_alignment(
                        kalshi_market.get('close_time', ''),
                        poly_market.get('end_date', '')
                    )
                    
                    contract_match = ContractMatch(
                        kalshi_ticker=kalshi_ticker,
                        kalshi_question=kalshi_market.get('question', kalshi_market.get('title', '')),
                        kalshi_event_ticker=kalshi_market.get('event_ticker', ''),
                        polymarket_condition_id=poly_cond_id,
                        polymarket_question=poly_market.get('question', ''),
                        confidence=float(match['confidence']),
                        match_type=match.get('match_type', 'unknown'),
                        threshold_value=match.get('threshold_value'),
                        notes=match.get('notes', ''),
                        matched_at=datetime.now().isoformat(),
                        expiry_alignment=expiry_aligned
                    )
                    
                    # Only include high-confidence matches
                    if contract_match.confidence >= 0.7:
                        matches.append(contract_match)
                        logger.info(f"✅ Match: {kalshi_ticker} ↔ {poly_cond_id[:16]}... (confidence: {contract_match.confidence:.1%})")
                
                except Exception as e:
                    logger.warning(f"Failed to parse match: {e}")
        
        except Exception as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            logger.debug(f"Response was: {response_text[:500]}...")
        
        return matches
    
    def _check_expiry_alignment(self, kalshi_date: str, poly_date: str) -> bool:
        """Check if expiry dates align (within 48 hours)"""
        try:
            kalshi_dt = datetime.fromisoformat(kalshi_date.replace('Z', '+00:00'))
            poly_dt = datetime.fromisoformat(poly_date.replace('Z', '+00:00'))
            
            diff = abs((kalshi_dt - poly_dt).total_seconds())
            return diff < 48 * 3600  # Within 48 hours
        except:
            return False
    
    async def run_enhanced_matching(self) -> Dict:
        """Run the enhanced matching process"""
        logger.info("🚀 Starting Enhanced OpenAI (ChatGPT) Matching System")
        
        # Fetch live markets
        kalshi_markets, poly_markets = await self.fetch_live_markets()
        
        # Group Kalshi by event to identify multi-contract events
        kalshi_events = self.group_kalshi_by_event(kalshi_markets)
        
        # Process in batches
        all_matches = []
        batch_size = 30  # Smaller batches for better accuracy
        
        for i in range(0, len(kalshi_markets), batch_size):
            batch = kalshi_markets[i:i + batch_size]
            logger.info(f"🔄 Processing batch {i//batch_size + 1}/{(len(kalshi_markets) + batch_size - 1)//batch_size}")
            
            # Get matches from OpenAI
            matches = await self.match_contracts_with_openai(batch, poly_markets)
            all_matches.extend(matches)
            
            # Rate limiting (OpenAI has generous rate limits but let's be nice)
            await asyncio.sleep(2)  # Much shorter delay than Claude
        
        # Save matches to CSV
        self.save_matches_to_csv(all_matches)
        
        # Generate statistics
        stats = {
            'total_matches': len(all_matches),
            'high_confidence': len([m for m in all_matches if m.confidence >= 0.9]),
            'exact_matches': len([m for m in all_matches if m.match_type == 'exact']),
            'threshold_matches': len([m for m in all_matches if m.match_type == 'threshold']),
            'multi_contract_events': len([e for e in kalshi_events.values() if len(e) > 1]),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"\n📊 Matching Complete!")
        logger.info(f"   Total matches: {stats['total_matches']}")
        logger.info(f"   High confidence: {stats['high_confidence']}")
        logger.info(f"   Exact matches: {stats['exact_matches']}")
        logger.info(f"   Threshold matches: {stats['threshold_matches']}")
        
        return stats
    
    def save_matches_to_csv(self, matches: List[ContractMatch]):
        """Save matches in the format expected by the arbitrage detector"""
        os.makedirs('output', exist_ok=True)
        
        # Save in the expected format
        with open('manual_matches.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Header matching what claude_matched_detector.py expects
            writer.writerow([
                'kalshi_ticker', 'kalshi_question', 'poly_condition_id', 'poly_question',
                'match_confidence', 'match_type', 'notes', 'has_match', 'recommendation'
            ])
            
            for match in matches:
                writer.writerow(match.to_csv_row())
        
        # Also save enhanced version with more details
        with open(self.matches_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'kalshi_ticker', 'kalshi_event', 'kalshi_question', 
                'poly_condition_id', 'poly_question',
                'confidence', 'match_type', 'threshold_value', 
                'expiry_aligned', 'notes', 'matched_at'
            ])
            
            for match in matches:
                writer.writerow([
                    match.kalshi_ticker,
                    match.kalshi_event_ticker,
                    match.kalshi_question,
                    match.polymarket_condition_id,
                    match.polymarket_question,
                    match.confidence,
                    match.match_type,
                    match.threshold_value,
                    match.expiry_alignment,
                    match.notes,
                    match.matched_at
                ])
        
        logger.info(f"✅ Saved {len(matches)} matches to manual_matches.csv and {self.matches_file}")

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced OpenAI Contract Matching')
    parser.add_argument('--test', action='store_true', help='Run test with small batch')
    parser.add_argument('--full', action='store_true', help='Run full matching')
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found!")
        print("Please set: export OPENAI_API_KEY='your-key-here'")
        print("Get key from: https://platform.openai.com/api-keys")
        return
    
    matcher = EnhancedOpenAIMatchingSystem()
    
    if args.test:
        print("🧪 Running test matching with limited markets...")
        # For testing, limit the markets
        # This would be implemented by modifying the fetch criteria
        
    stats = await matcher.run_enhanced_matching()
    
    print("\n✅ Matching complete! Check manual_matches.csv for results.")
    print("📊 You can now run: python claude_matched_detector.py")

if __name__ == "__main__":
    asyncio.run(main())
