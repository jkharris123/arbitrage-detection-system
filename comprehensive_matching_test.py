
"""
COMPREHENSIVE CONTRACT MATCHING TEST
Goal: ZERO FALSE MATCHES with MAXIMUM COVERAGE!

Two-Phase Strategy:
- Phase 1: Brute force ALL available contracts
- Phase 2: Targeted economic indicator search
- Output: ONE row per Kalshi contract with BEST match (not all matches)
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
class FinalMatchedPair:
    """FINAL matched pair - ONE row per Kalshi contract"""
    # Kalshi contract (always present)
    kalshi_ticker: str
    kalshi_question: str
    kalshi_category: str
    kalshi_expiry: str
    kalshi_volume: float
    kalshi_dates_found: str
    kalshi_keywords: str
    
    # Match status
    has_match: str  # "YES" or "NO"
    match_confidence: float  # 0.0 if no match
    
    # Best Polymarket match (empty if no match)
    poly_condition_id: str
    poly_question: str
    poly_category: str
    poly_expiry: str
    poly_volume: float
    poly_dates_found: str
    poly_keywords: str
    
    # Matching scores
    text_similarity: float
    date_alignment: float
    keyword_overlap: float
    date_penalty: float
    
    # Safety assessment
    risk_level: str  # "SAFE", "RISKY", "DANGEROUS", "NO_MATCH"
    recommendation: str  # "SAFE_FOR_AUTOMATION", "MANUAL_REVIEW", "REJECT", "NO_OPPORTUNITY"
    confidence_notes: str
    
    # Metadata
    match_timestamp: str
    candidates_tested: int
    
    def to_dict(self) -> Dict:
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
        
        print(f"🎯 ENHANCED COMPREHENSIVE MATCHING TEST")
        print(f"📁 Final pairs CSV: {self.output_file}")
        print(f"🚨 Goal: ZERO FALSE MATCHES + MAXIMUM COVERAGE!")
        print(f"📊 Output: ONE row per Kalshi contract with BEST match")
    
    async def run_comprehensive_test(self):
        """Run the full comprehensive matching test"""
        print(f"\n🚀 Starting comprehensive matching test...")
        
        # Phase 1: Maximum contract collection
        print(f"\n📊 PHASE 1: Maximum contract collection...")
        kalshi_contracts = await self.fetch_maximum_kalshi_contracts()
        polymarket_contracts = await self.fetch_maximum_polymarket_contracts()
        
        # Phase 2: Targeted economic search if needed
        if len(kalshi_contracts) < 300:
            print(f"\n🎯 PHASE 2: Targeted economic data search...")
            additional_kalshi = await self.fetch_targeted_economic_contracts()
            kalshi_contracts = self.merge_and_deduplicate_kalshi(kalshi_contracts, additional_kalshi)
        
        print(f"✅ Fetched {len(kalshi_contracts)} Kalshi contracts")
        print(f"✅ Fetched {len(polymarket_contracts)} Polymarket contracts")
        
        # Phase 3: Find BEST matches (not all matches)
        print(f"\n🔍 PHASE 3: Finding BEST match for each Kalshi contract...")
        final_pairs = await self.find_best_matches_for_all(kalshi_contracts, polymarket_contracts)
        
        # Phase 4: Generate final pairs CSV
        print(f"\n📈 PHASE 4: Generating final matched pairs CSV...")
        await self.generate_final_pairs_csv(final_pairs)
        
        # Phase 5: Enhanced analysis
        print(f"\n📊 PHASE 5: Enhanced analysis...")
        self.print_enhanced_analysis(final_pairs)
        
        print(f"\n🎉 Comprehensive test complete!")
        print(f"📁 Results saved to: {self.output_file}")
        print(f"🔍 Please review CSV for manual verification of matches")
        
        return final_pairs
    
    async def fetch_maximum_kalshi_contracts(self) -> List[Dict]:
        """Fetch ALL available Kalshi contracts (no limits)"""
        try:
            print(f"📡 Fetching ALL Kalshi markets (no limits)...")
            raw_markets = self.kalshi_client.get_markets()
            print(f"🔍 Raw Kalshi response: {len(raw_markets)} total markets")
            
            # Process ALL valid contracts
            contracts = []
            categories = {}
            
            for market in raw_markets:
                try:
                    title = market.get('title', market.get('question', ''))
                    ticker = market.get('ticker', '')
                    
                    if title and ticker and len(title.strip()) > 10:  # Quality filter
                        category = self._categorize_contract(title)
                        categories[category] = categories.get(category, 0) + 1
                        
                        contract = {
                            'ticker': ticker,
                            'question': title,
                            'category': category,
                            'expiry': market.get('close_date', ''),
                            'status': market.get('status', 'active'),
                            'volume': float(market.get('volume', 0)),
                            'raw_data': market
                        }
                        contracts.append(contract)
                        
                except Exception as e:
                    print(f"⚠️ Error processing Kalshi market: {e}")
                    continue
            
            print(f"✅ Processed {len(contracts)} valid Kalshi contracts")
            print(f"📊 Categories: {dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))}")
            return contracts
            
        except Exception as e:
            print(f"❌ Error fetching Kalshi contracts: {e}")
            return []
    
    async def fetch_maximum_polymarket_contracts(self) -> List[PolymarketMarket]:
        """Fetch maximum possible Polymarket contracts"""
        try:
            print(f"📡 Fetching maximum Polymarket markets...")
            
            async with EnhancedPolymarketClient() as client:
                all_markets = []
                
                # Multiple API calls to get more contracts
                for batch in range(3):  # Try 3 batches
                    try:
                        batch_size = 500
                        print(f"🔍 Batch {batch + 1}: Fetching {batch_size} markets...")
                        
                        markets_batch = await client.get_active_markets_with_pricing(limit=batch_size)
                        if not markets_batch:
                            break
                        
                        all_markets.extend(markets_batch)
                        print(f"📊 Batch {batch + 1}: Got {len(markets_batch)} markets")
                        
                        if len(markets_batch) < batch_size:
                            break
                            
                    except Exception as e:
                        print(f"⚠️ Batch {batch + 1} failed: {e}")
                        continue
                
                # Deduplicate by condition_id
                seen_ids = set()
                unique_markets = []
                categories = {}
                
                for market in all_markets:
                    if (market.condition_id not in seen_ids and 
                        market.question and 
                        len(market.question.strip()) > 10):
                        
                        seen_ids.add(market.condition_id)
                        unique_markets.append(market)
                        categories[market.category] = categories.get(market.category, 0) + 1
                
                print(f"✅ Processed {len(unique_markets)} unique Polymarket contracts")
                print(f"📊 Categories: {dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))}")
                
                return unique_markets
            
        except Exception as e:
            print(f"❌ Error fetching Polymarket contracts: {e}")
            return []
    
    async def fetch_targeted_economic_contracts(self) -> List[Dict]:
        """Phase 2: Targeted search for specific economic indicators"""
        print(f"🎯 Targeted search for economic indicators...")
        
        # High-value economic keywords for arbitrage
        economic_targets = [
            'CPI', 'consumer price index', 'inflation',
            'Fed', 'FOMC', 'federal reserve', 'interest rate', 'rate decision',
            'unemployment', 'jobs report', 'payroll', 'employment',
            'GDP', 'recession', 'economic growth',
            'S&P 500', 'Nasdaq', 'stock market',
            'Bitcoin', 'crypto', 'BTC'
        ]
        
        additional_contracts = []
        
        try:
            # Get ALL markets again and filter for economic indicators
            raw_markets = self.kalshi_client.get_markets()
            
            for market in raw_markets:
                title = market.get('title', '').lower()
                
                # Check if this market contains high-value economic keywords
                if any(keyword.lower() in title for keyword in economic_targets):
                    ticker = market.get('ticker', '')
                    if title and ticker:
                        contract = {
                            'ticker': ticker,
                            'question': market.get('title', ''),
                            'category': self._categorize_contract(market.get('title', '')),
                            'expiry': market.get('close_date', ''),
                            'status': market.get('status', ''),
                            'volume': float(market.get('volume', 0)),
                            'raw_data': market,
                            'source': 'targeted_economic'
                        }
                        additional_contracts.append(contract)
            
            print(f"✅ Found {len(additional_contracts)} targeted economic contracts")
            
        except Exception as e:
            print(f"⚠️ Error in targeted search: {e}")
        
        return additional_contracts
    
    def merge_and_deduplicate_kalshi(self, contracts1: List[Dict], contracts2: List[Dict]) -> List[Dict]:
        """Merge and deduplicate Kalshi contracts by ticker"""
        seen_tickers = set()
        merged = []
        
        for contract_list in [contracts1, contracts2]:
            for contract in contract_list:
                ticker = contract.get('ticker', '')
                if ticker and ticker not in seen_tickers:
                    seen_tickers.add(ticker)
                    merged.append(contract)
        
        print(f"🔄 Merged: {len(merged)} unique Kalshi contracts")
        return merged
    
    async def find_best_matches_for_all(self, kalshi_contracts: List[Dict], 
                                      polymarket_contracts: List[PolymarketMarket]) -> List[FinalMatchedPair]:
        """Find the BEST match for each Kalshi contract - KEY CHANGE!"""
        final_pairs = []
        
        print(f"🔍 Finding BEST match for each of {len(kalshi_contracts)} Kalshi contracts...")
        print(f"📊 Testing against {len(polymarket_contracts)} Polymarket contracts")
        print(f"⚡ Total combinations: {len(kalshi_contracts) * len(polymarket_contracts):,}")
        
        for i, kalshi_contract in enumerate(kalshi_contracts):
            if i % 25 == 0:
                print(f"📊 Progress: {i}/{len(kalshi_contracts)} ({(i/len(kalshi_contracts)*100):.1f}%)")
            
            kalshi_question = kalshi_contract['question']
            kalshi_dates = self.matcher.extract_dates(kalshi_question)
            kalshi_keywords = self.matcher.extract_keywords(kalshi_question)
            
            # Find the SINGLE BEST match for this Kalshi contract
            best_match_poly = None
            best_score = 0.0
            best_scores_detail = None
            candidates_tested = 0
            
            for poly_contract in polymarket_contracts:
                try:
                    candidates_tested += 1
                    scores = self.matcher.enhanced_similarity_score(
                        kalshi_question, 
                        poly_contract.question
                    )
                    
                    if scores['final_score'] > best_score:
                        best_score = scores['final_score']
                        best_match_poly = poly_contract
                        best_scores_detail = scores
                        
                except Exception as e:
                    continue
            
            # Create final pair (with or without match)
            pair = self._create_final_pair(
                kalshi_contract, 
                best_match_poly, 
                best_scores_detail, 
                kalshi_dates, 
                kalshi_keywords, 
                candidates_tested
            )
            
            final_pairs.append(pair)
        
        print(f"✅ Generated {len(final_pairs)} final pairs")
        
        # Count matches
        matched_count = len([p for p in final_pairs if p.has_match == "YES"])
        print(f"📊 Matches found: {matched_count}/{len(final_pairs)} ({(matched_count/len(final_pairs)*100):.1f}%)")
        
        return final_pairs
    
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
    
    def _create_final_pair(self, kalshi_contract: Dict, best_match_poly: Optional[PolymarketMarket], 
                          best_scores_detail: Optional[Dict], kalshi_dates: List, 
                          kalshi_keywords: set, candidates_tested: int) -> FinalMatchedPair:
        """Create a final matched pair entry"""
        
        # Kalshi data (always present)
        kalshi_data = {
            'kalshi_ticker': kalshi_contract['ticker'],
            'kalshi_question': kalshi_contract['question'],
            'kalshi_category': kalshi_contract['category'],
            'kalshi_expiry': kalshi_contract['expiry'],
            'kalshi_volume': kalshi_contract['volume'],
            'kalshi_dates_found': json.dumps(kalshi_dates),
            'kalshi_keywords': ', '.join(kalshi_keywords),
        }
        
        # Check if we have a valid match
        if best_match_poly and best_scores_detail and best_scores_detail['final_score'] > 0.3:  # LOWERED THRESHOLD
            # We have a match!
            poly_dates = self.matcher.extract_dates(best_match_poly.question)
            poly_keywords = self.matcher.extract_keywords(best_match_poly.question)
            
            # Debug output for first few matches
            if len([p for p in [] if hasattr(p, 'has_match')]) < 5:  # First 5 matches
                print(f"🔍 MATCH FOUND: {kalshi_contract['ticker']}")
                print(f"   Kalshi: {kalshi_contract['question'][:60]}...")
                print(f"   Poly:   {best_match_poly.question[:60]}...")
                print(f"   Score:  {best_scores_detail['final_score']:.3f}")
                print(f"   Date:   {best_scores_detail['date_alignment']:.3f}")
            
            # Assess risk and recommendation
            risk_level = self.matcher.assess_match_risk(kalshi_contract['question'], best_match_poly.question)
            recommendation = self._generate_recommendation(best_scores_detail, risk_level)
            confidence_notes = self._generate_confidence_notes(best_scores_detail, kalshi_dates, poly_dates)
            
            return FinalMatchedPair(
                **kalshi_data,
                
                has_match="YES",
                match_confidence=best_scores_detail['final_score'],
                
                poly_condition_id=best_match_poly.condition_id,
                poly_question=best_match_poly.question,
                poly_category=best_match_poly.category,
                poly_expiry=best_match_poly.end_date,
                poly_volume=best_match_poly.volume,
                poly_dates_found=json.dumps(poly_dates),
                poly_keywords=', '.join(poly_keywords),
                
                text_similarity=best_scores_detail['text_similarity'],
                date_alignment=best_scores_detail['date_alignment'],
                keyword_overlap=best_scores_detail['keyword_score'],
                date_penalty=best_scores_detail.get('date_penalty', 1.0),
                
                risk_level=risk_level,
                recommendation=recommendation,
                confidence_notes=confidence_notes,
                
                match_timestamp=datetime.now().isoformat(),
                candidates_tested=candidates_tested
            )
        else:
            # No match found
            return FinalMatchedPair(
                **kalshi_data,
                
                has_match="NO",
                match_confidence=0.0,
                
                poly_condition_id="",
                poly_question="",
                poly_category="",
                poly_expiry="",
                poly_volume=0.0,
                poly_dates_found="",
                poly_keywords="",
                
                text_similarity=0.0,
                date_alignment=0.0,
                keyword_overlap=0.0,
                date_penalty=1.0,
                
                risk_level="NO_MATCH",
                recommendation="NO_ARBITRAGE_OPPORTUNITY",
                confidence_notes="No suitable Polymarket match found above threshold",
                
                match_timestamp=datetime.now().isoformat(),
                candidates_tested=candidates_tested
            )
    
    def _generate_recommendation(self, scores: Dict, risk_level: str) -> str:
        """Generate recommendation for the match"""
        if risk_level == "DANGEROUS":
            return "REJECT_DANGEROUS"
        elif scores['final_score'] > 0.8 and scores['date_alignment'] > 0.7 and risk_level == "SAFE":
            return "SAFE_FOR_AUTOMATION"
        elif scores['final_score'] > 0.6:
            return "MANUAL_REVIEW_REQUIRED"
        else:
            return "WEAK_MATCH_CONSIDER_REJECT"
    
    def _generate_confidence_notes(self, scores: Dict, kalshi_dates: List, poly_dates: List) -> str:
        """Generate detailed confidence notes"""
        notes = []
        
        # Score analysis
        if scores['final_score'] > 0.9:
            notes.append("EXCELLENT match confidence")
        elif scores['final_score'] > 0.8:
            notes.append("GOOD match confidence")
        elif scores['final_score'] > 0.6:
            notes.append("MODERATE match confidence")
        else:
            notes.append("LOW match confidence")
        
        # Date analysis
        if scores['date_alignment'] == 0:
            notes.append("NO DATE ALIGNMENT - HIGH RISK")
        elif scores['date_alignment'] < 0.3:
            notes.append("POOR date alignment - verify manually")
        elif scores['date_alignment'] > 0.8:
            notes.append("EXCELLENT date alignment")
        
        # Penalty analysis
        if scores.get('date_penalty', 1.0) < 0.5:
            notes.append("SEVERE date penalty applied")
        elif scores.get('date_penalty', 1.0) < 1.0:
            notes.append("Date penalty applied")
        
        # Missing data
        if not kalshi_dates:
            notes.append("No dates found in Kalshi")
        if not poly_dates:
            notes.append("No dates found in Polymarket")
        
        return "; ".join(notes)
    
    async def generate_final_pairs_csv(self, final_pairs: List[FinalMatchedPair]):
        """Generate final matched pairs CSV (one row per Kalshi contract)"""
        print(f"💾 Writing {len(final_pairs)} final pairs to CSV...")
        
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            if final_pairs:
                fieldnames = list(final_pairs[0].to_dict().keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for pair in final_pairs:
                    writer.writerow(pair.to_dict())
        
        print(f"✅ Final pairs CSV generated successfully")
    
    def print_enhanced_analysis(self, final_pairs: List[FinalMatchedPair]):
        """Print enhanced analysis of final matched pairs"""
        matched_pairs = [p for p in final_pairs if p.has_match == "YES"]
        
        if not final_pairs:
            print("⚠️ No final pairs to analyze")
            return
        
        # Overall statistics
        total_contracts = len(final_pairs)
        total_matches = len(matched_pairs)
        
        # Confidence analysis
        high_confidence = len([p for p in matched_pairs if p.match_confidence > 0.8])
        medium_confidence = len([p for p in matched_pairs if 0.6 < p.match_confidence <= 0.8])
        low_confidence = len([p for p in matched_pairs if p.match_confidence <= 0.6])
        
        # Recommendation analysis
        safe_automation = len([p for p in matched_pairs if p.recommendation == "SAFE_FOR_AUTOMATION"])
        manual_review = len([p for p in matched_pairs if p.recommendation == "MANUAL_REVIEW_REQUIRED"])
        dangerous_rejected = len([p for p in matched_pairs if p.recommendation == "REJECT_DANGEROUS"])
        
        # Date analysis
        no_date_alignment = len([p for p in matched_pairs if p.date_alignment == 0])
        good_date_alignment = len([p for p in matched_pairs if p.date_alignment > 0.7])
        
        print(f"\n📊 ENHANCED MATCHING ANALYSIS")
        print(f"=" * 70)
        
        print(f"📈 COVERAGE RESULTS:")
        print(f"   📋 Total Kalshi contracts analyzed: {total_contracts}")
        print(f"   ✅ Contracts with matches: {total_matches}")
        print(f"   ❌ Contracts without matches: {total_contracts - total_matches}")
        print(f"   📊 Coverage rate: {(total_matches / total_contracts * 100):.1f}%")
        
        print(f"\n🎯 MATCH QUALITY:")
        print(f"   🟢 High confidence (>80%): {high_confidence}")
        print(f"   🟡 Medium confidence (60-80%): {medium_confidence}")
        print(f"   🔴 Low confidence (<60%): {low_confidence}")
        
        print(f"\n🔒 SAFETY ASSESSMENT:")
        print(f"   ✅ SAFE for automation: {safe_automation}")
        print(f"   🟡 MANUAL review required: {manual_review}")
        print(f"   🔴 DANGEROUS (rejected): {dangerous_rejected}")
        
        print(f"\n📅 DATE ALIGNMENT ANALYSIS:")
        print(f"   ❌ No date alignment: {no_date_alignment}")
        print(f"   ✅ Good date alignment (>70%): {good_date_alignment}")
        if total_matches > 0:
            print(f"   📊 Date alignment rate: {(good_date_alignment/total_matches)*100:.1f}%")
        
        if dangerous_rejected > 0:
            print(f"\n🚨 DANGEROUS MATCHES (PROPERLY REJECTED):")
            dangerous = [p for p in matched_pairs if p.recommendation == "REJECT_DANGEROUS"]
            for i, pair in enumerate(dangerous[:3], 1):  # Show top 3
                print(f"   {i}. {pair.kalshi_ticker}")
                print(f"      Kalshi: {pair.kalshi_question[:60]}...")
                print(f"      Poly:   {pair.poly_question[:60]}...")
                print(f"      Score: {pair.match_confidence:.2f} | Date: {pair.date_alignment:.2f}")
        
        if safe_automation > 0:
            print(f"\n✅ TOP SAFE MATCHES FOR AUTOMATION:")
            safe_matches = [p for p in matched_pairs if p.recommendation == "SAFE_FOR_AUTOMATION"]
            top_safe = sorted(safe_matches, key=lambda x: x.match_confidence, reverse=True)[:5]
            for i, pair in enumerate(top_safe, 1):
                print(f"   {i}. {pair.kalshi_ticker} → {pair.match_confidence:.3f}")
                print(f"      📝 {pair.kalshi_question[:60]}...")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if dangerous_rejected == 0:
            print(f"   ✅ Excellent! Zero dangerous matches - system is SAFE!")
        else:
            print(f"   🔒 {dangerous_rejected} dangerous matches properly rejected")
        
        if safe_automation >= 10:
            print(f"   🎯 Excellent! {safe_automation} contracts ready for automated arbitrage")
        elif safe_automation >= 5:
            print(f"   👍 Good start: {safe_automation} safe contracts available")
        else:
            print(f"   📊 Limited safe matches - consider threshold tuning")
        
        if total_matches / total_contracts < 0.1:
            print(f"   📈 Low match rate - may need more Polymarket contracts")
        else:
            print(f"   📊 Match rate looks reasonable for arbitrage opportunities")

async def main():
    """Run the comprehensive matching test"""
    print(f"🚀 ENHANCED COMPREHENSIVE CONTRACT MATCHING TEST")
    print(f"🎯 Goal: ZERO FALSE MATCHES + MAXIMUM COVERAGE")
    print(f"📊 Strategy: Two-phase brute force + targeted search")
    print(f"🔍 Output: ONE row per Kalshi contract with BEST match")
    
    tester = ComprehensiveMatchingTester()
    final_pairs = await tester.run_comprehensive_test()
    
    print(f"\n🎉 ENHANCED TEST COMPLETE!")
    print(f"📁 Review final pairs CSV for BEST matches only")
    print(f"✅ SAFE_FOR_AUTOMATION contracts ready for arbitrage")
    print(f"🔍 Each row = one Kalshi contract with its best match (or no match)")
    
    return final_pairs

if __name__ == "__main__":
    asyncio.run(main())
