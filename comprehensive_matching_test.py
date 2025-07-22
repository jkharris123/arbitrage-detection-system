#!/usr/bin/env python3
"""
COMPREHENSIVE CONTRACT MATCHING TEST
Goal: ZERO FALSE MATCHES!

Tests the enhanced date-aware matching system with 200 contracts from each platform.
Outputs detailed CSV for manual verification to ensure NO false positives.
"""

import asyncio
import csv
import time
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import sys
import os

# Add paths
sys.path.append('./data_collectors')
sys.path.append('./arbitrage')
sys.path.append('./')

from kalshi_client import KalshiClient
from polymarket_client_enhanced import EnhancedPolymarketClient, PolymarketMarket

# Import our dedicated matching module
try:
    from contract_matcher import DateAwareContractMatcher
except ImportError:
    # Fallback to detector_enhanced
    from detector_enhanced import DateAwareContractMatcher

@dataclass
class MatchAnalysis:
    """Detailed match analysis for CSV output"""
    # Match information
    match_id: str
    timestamp: str
    confidence_score: float
    
    # Kalshi contract details
    kalshi_ticker: str
    kalshi_question: str
    kalshi_category: str
    kalshi_expiry: str
    kalshi_extracted_dates: str
    kalshi_keywords: str
    
    # Polymarket contract details
    poly_condition_id: str
    poly_question: str
    poly_category: str
    poly_expiry: str
    poly_extracted_dates: str
    poly_keywords: str
    
    # Scoring breakdown
    text_similarity: float
    date_alignment: float
    keyword_score: float
    final_score: float
    
    # Manual verification fields
    is_same_event: str  # "YES", "NO", "UNCERTAIN" - for manual review
    notes: str
    risk_level: str  # "SAFE", "RISKY", "DANGEROUS"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for CSV writing"""
        return asdict(self)

class ComprehensiveMatchingTester:
    """Comprehensive testing system for contract matching"""
    
    def __init__(self):
        self.kalshi_client = KalshiClient()
        self.matcher = DateAwareContractMatcher()
        self.match_count = 0
        
        # Setup output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        self.output_file = f"./output/comprehensive_matching_test_{timestamp}.csv"
        os.makedirs('./output', exist_ok=True)
        
        print(f"🎯 COMPREHENSIVE MATCHING TEST")
        print(f"📁 Output file: {self.output_file}")
        print(f"🚨 Goal: ZERO FALSE MATCHES!")
    
    async def run_comprehensive_test(self):
        """Run the full comprehensive matching test"""
        print(f"\n🚀 Starting comprehensive matching test...")
        
        # Step 1: Fetch contracts from both platforms
        print(f"\n📊 Step 1: Fetching contracts from both platforms...")
        kalshi_contracts = await self.fetch_kalshi_contracts(200)
        polymarket_contracts = await self.fetch_polymarket_contracts(200)
        
        print(f"✅ Fetched {len(kalshi_contracts)} Kalshi contracts")
        print(f"✅ Fetched {len(polymarket_contracts)} Polymarket contracts")
        
        # Step 2: Run enhanced matching analysis
        print(f"\n🔍 Step 2: Running enhanced matching analysis...")
        matches = await self.analyze_all_matches(kalshi_contracts, polymarket_contracts)
        
        # Step 3: Generate detailed CSV
        print(f"\n📈 Step 3: Generating detailed analysis CSV...")
        await self.generate_detailed_csv(matches)
        
        # Step 4: Summary analysis
        print(f"\n📊 Step 4: Summary analysis...")
        self.print_summary_analysis(matches)
        
        print(f"\n🎉 Comprehensive test complete!")
        print(f"📁 Results saved to: {self.output_file}")
        print(f"🔍 Please review CSV for manual verification of matches")
        
        return matches
    
    async def fetch_kalshi_contracts(self, limit: int) -> List[Dict]:
        """Fetch Kalshi contracts with full details"""
        try:
            print(f"📡 Fetching Kalshi markets...")
            raw_markets = self.kalshi_client.get_markets()
            
            # Process and enrich contract data
            contracts = []
            for market in raw_markets[:limit]:
                try:
                    contract = {
                        'ticker': market.get('ticker', ''),
                        'question': market.get('title', market.get('question', '')),
                        'category': self._categorize_contract(market.get('title', '')),
                        'expiry': market.get('close_date', ''),
                        'status': market.get('status', ''),
                        'volume': market.get('volume', 0),
                        'raw_data': market
                    }
                    
                    if contract['question'] and contract['ticker']:
                        contracts.append(contract)
                        
                except Exception as e:
                    print(f"⚠️ Error processing Kalshi market: {e}")
                    continue
            
            print(f"✅ Processed {len(contracts)} valid Kalshi contracts")
            return contracts
            
        except Exception as e:
            print(f"❌ Error fetching Kalshi contracts: {e}")
            return []
    
    async def fetch_polymarket_contracts(self, limit: int) -> List[PolymarketMarket]:
        """Fetch Polymarket contracts with full details"""
        try:
            print(f"📡 Fetching Polymarket markets...")
            async with EnhancedPolymarketClient() as client:
                markets = await client.get_active_markets_with_pricing(limit=limit)
            
            # Filter for valid contracts
            valid_contracts = []
            for market in markets:
                if market.question and market.condition_id:
                    valid_contracts.append(market)
            
            print(f"✅ Processed {len(valid_contracts)} valid Polymarket contracts")
            return valid_contracts
            
        except Exception as e:
            print(f"❌ Error fetching Polymarket contracts: {e}")
            return []
    
    async def analyze_all_matches(self, kalshi_contracts: List[Dict], 
                                polymarket_contracts: List[PolymarketMarket]) -> List[MatchAnalysis]:
        """Analyze all possible matches between platforms"""
        matches = []
        
        print(f"🔍 Analyzing {len(kalshi_contracts)} x {len(polymarket_contracts)} = {len(kalshi_contracts) * len(polymarket_contracts)} possible combinations...")
        
        for i, kalshi_contract in enumerate(kalshi_contracts):
            if i % 20 == 0:
                print(f"📊 Progress: {i}/{len(kalshi_contracts)} Kalshi contracts analyzed...")
            
            kalshi_question = kalshi_contract['question']
            
            for poly_contract in polymarket_contracts:
                try:
                    # Get enhanced similarity scores
                    scores = self.matcher.enhanced_similarity_score(
                        kalshi_question, 
                        poly_contract.question
                    )
                    
                    # Only record matches above minimum threshold
                    if scores['final_score'] > 0.3:  # Lower threshold for analysis
                        self.match_count += 1
                        
                        # Extract detailed information for analysis
                        kalshi_dates = self.matcher.extract_dates(kalshi_question)
                        poly_dates = self.matcher.extract_dates(poly_contract.question)
                        kalshi_keywords = self.matcher.extract_keywords(kalshi_question)
                        poly_keywords = self.matcher.extract_keywords(poly_contract.question)
                        
                        # Determine risk level
                        risk_level = self._assess_match_risk(scores, kalshi_dates, poly_dates)
                        
                        # Create match analysis
                        match = MatchAnalysis(
                            match_id=f"M{self.match_count:04d}",
                            timestamp=datetime.now().isoformat(),
                            confidence_score=scores['final_score'],
                            
                            kalshi_ticker=kalshi_contract['ticker'],
                            kalshi_question=kalshi_question,
                            kalshi_category=kalshi_contract['category'],
                            kalshi_expiry=kalshi_contract['expiry'],
                            kalshi_extracted_dates=json.dumps(kalshi_dates),
                            kalshi_keywords=', '.join(kalshi_keywords),
                            
                            poly_condition_id=poly_contract.condition_id[:16] + "...",  # Truncated for readability
                            poly_question=poly_contract.question,
                            poly_category=poly_contract.category,
                            poly_expiry=poly_contract.end_date,
                            poly_extracted_dates=json.dumps(poly_dates),
                            poly_keywords=', '.join(poly_keywords),
                            
                            text_similarity=scores['text_similarity'],
                            date_alignment=scores['date_alignment'],
                            keyword_score=scores['keyword_score'],
                            final_score=scores['final_score'],
                            
                            is_same_event="REVIEW_NEEDED",  # Manual review required
                            notes=self._generate_match_notes(scores, kalshi_dates, poly_dates),
                            risk_level=risk_level
                        )
                        
                        matches.append(match)
                
                except Exception as e:
                    print(f"⚠️ Error analyzing match: {e}")
                    continue
        
        # Sort by confidence score (highest first)
        matches.sort(key=lambda x: x.confidence_score, reverse=True)
        
        print(f"✅ Found {len(matches)} potential matches for analysis")
        return matches
    
    def _categorize_contract(self, question: str) -> str:
        """Categorize contract based on question content"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['fed', 'federal reserve', 'fomc', 'interest rate']):
            return 'fed_rates'
        elif any(word in question_lower for word in ['cpi', 'inflation', 'consumer price']):
            return 'inflation'
        elif any(word in question_lower for word in ['unemployment', 'jobs', 'payroll']):
            return 'employment'
        elif any(word in question_lower for word in ['sp500', 's&p', 'nasdaq', 'dow']):
            return 'markets'
        elif any(word in question_lower for word in ['bitcoin', 'btc', 'ethereum', 'crypto']):
            return 'crypto'
        elif any(word in question_lower for word in ['election', 'president', 'vote', 'midterm']):
            return 'politics'
        elif any(word in question_lower for word in ['gdp', 'recession', 'growth']):
            return 'economy'
        else:
            return 'other'
    
    def _assess_match_risk(self, scores: Dict, kalshi_dates: List, poly_dates: List) -> str:
        """Assess the risk level of a match"""
        # High confidence with good date alignment = SAFE
        if scores['final_score'] > 0.8 and scores['date_alignment'] > 0.7:
            return "SAFE"
        
        # Good keyword match but poor dates = DANGEROUS (could be wrong event)
        elif scores['keyword_score'] > 0.7 and scores['date_alignment'] < 0.3:
            return "DANGEROUS"
        
        # Medium confidence = RISKY
        elif 0.5 < scores['final_score'] <= 0.8:
            return "RISKY"
        
        # Low confidence = SAFE (unlikely to be matched anyway)
        else:
            return "SAFE"
    
    def _generate_match_notes(self, scores: Dict, kalshi_dates: List, poly_dates: List) -> str:
        """Generate notes about the match for manual review"""
        notes = []
        
        if scores['date_alignment'] == 0:
            notes.append("NO DATE ALIGNMENT - verify dates manually")
        elif scores['date_alignment'] < 0.5:
            notes.append("WEAK DATE ALIGNMENT - check if same timeframe")
        
        if scores['keyword_score'] == 0:
            notes.append("NO KEYWORD OVERLAP - may be unrelated")
        elif scores['keyword_score'] > 0.8:
            notes.append("STRONG KEYWORD MATCH")
        
        if scores['text_similarity'] < 0.3:
            notes.append("LOW TEXT SIMILARITY - different wording")
        
        if not kalshi_dates:
            notes.append("NO DATES FOUND IN KALSHI")
        if not poly_dates:
            notes.append("NO DATES FOUND IN POLYMARKET")
        
        return "; ".join(notes) if notes else "Standard match"
    
    async def generate_detailed_csv(self, matches: List[MatchAnalysis]):
        """Generate detailed CSV for manual verification"""
        print(f"💾 Writing {len(matches)} matches to CSV...")
        
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            if matches:
                fieldnames = list(matches[0].to_dict().keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for match in matches:
                    writer.writerow(match.to_dict())
        
        print(f"✅ CSV generated successfully")
    
    def print_summary_analysis(self, matches: List[MatchAnalysis]):
        """Print summary analysis of matches"""
        if not matches:
            print("⚠️ No matches found to analyze")
            return
        
        # Overall statistics
        total_matches = len(matches)
        high_confidence = len([m for m in matches if m.confidence_score > 0.8])
        medium_confidence = len([m for m in matches if 0.5 < m.confidence_score <= 0.8])
        low_confidence = len([m for m in matches if m.confidence_score <= 0.5])
        
        # Risk analysis
        safe_matches = len([m for m in matches if m.risk_level == "SAFE"])
        risky_matches = len([m for m in matches if m.risk_level == "RISKY"])
        dangerous_matches = len([m for m in matches if m.risk_level == "DANGEROUS"])
        
        # Date analysis
        no_date_alignment = len([m for m in matches if m.date_alignment == 0])
        good_date_alignment = len([m for m in matches if m.date_alignment > 0.7])
        
        print(f"\n📊 COMPREHENSIVE MATCHING ANALYSIS SUMMARY")
        print(f"=" * 60)
        print(f"📈 CONFIDENCE DISTRIBUTION:")
        print(f"   🟢 High Confidence (>80%): {high_confidence}")
        print(f"   🟡 Medium Confidence (50-80%): {medium_confidence}")
        print(f"   🔴 Low Confidence (<50%): {low_confidence}")
        print(f"   📊 Total Matches: {total_matches}")
        
        print(f"\n🚨 RISK ASSESSMENT:")
        print(f"   ✅ SAFE matches: {safe_matches}")
        print(f"   ⚠️  RISKY matches: {risky_matches}")
        print(f"   🚨 DANGEROUS matches: {dangerous_matches}")
        
        print(f"\n📅 DATE ALIGNMENT ANALYSIS:")
        print(f"   ❌ No date alignment: {no_date_alignment}")
        print(f"   ✅ Good date alignment (>70%): {good_date_alignment}")
        print(f"   📊 Date alignment rate: {(good_date_alignment/total_matches)*100:.1f}%")
        
        if dangerous_matches > 0:
            print(f"\n🚨 DANGEROUS MATCHES REQUIRE IMMEDIATE REVIEW:")
            dangerous = [m for m in matches if m.risk_level == "DANGEROUS"]
            for i, match in enumerate(dangerous[:5], 1):  # Show top 5
                print(f"   {i}. {match.kalshi_ticker} ↔ {match.poly_condition_id}")
                print(f"      Kalshi: {match.kalshi_question[:60]}...")
                print(f"      Poly:   {match.poly_question[:60]}...")
                print(f"      Score: {match.confidence_score:.2f} | Date: {match.date_alignment:.2f}")
        
        print(f"\n🎯 TOP HIGH-CONFIDENCE MATCHES:")
        top_matches = [m for m in matches if m.confidence_score > 0.8][:5]
        for i, match in enumerate(top_matches, 1):
            print(f"   {i}. {match.kalshi_ticker} ↔ {match.poly_condition_id}")
            print(f"      Score: {match.confidence_score:.2f} | Date: {match.date_alignment:.2f} | Risk: {match.risk_level}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if dangerous_matches > 5:
            print(f"   🚨 HIGH ALERT: {dangerous_matches} dangerous matches found!")
            print(f"   📋 Action: Review all DANGEROUS matches before enabling automated trading")
        elif dangerous_matches > 0:
            print(f"   ⚠️  {dangerous_matches} dangerous matches found - review required")
        else:
            print(f"   ✅ No dangerous matches found - system appears safe")
        
        if high_confidence > 10:
            print(f"   🎯 Good news: {high_confidence} high-confidence matches available")
        else:
            print(f"   📊 Limited high-confidence matches - may need threshold adjustment")

async def main():
    """Run the comprehensive matching test"""
    print(f"🚀 COMPREHENSIVE CONTRACT MATCHING TEST")
    print(f"🎯 Goal: Test enhanced matching system with ZERO FALSE MATCHES")
    print(f"📊 Analysis: 200 contracts from each platform")
    print(f"🔍 Output: Detailed CSV for manual verification")
    
    tester = ComprehensiveMatchingTester()
    matches = await tester.run_comprehensive_test()
    
    print(f"\n🎉 TEST COMPLETE!")
    print(f"📁 Review the CSV file for detailed analysis")
    print(f"🚨 Pay special attention to DANGEROUS matches")
    print(f"✅ SAFE matches can be used for automated trading")
    
    return matches

if __name__ == "__main__":
    asyncio.run(main())
