#!/usr/bin/env python3
"""
CONTRACT MATCHING TEST WITH DATE ANALYSIS

Tests current matching system and shows how date matching should work
for economic indicators and financial forecasts.
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

# Import our dedicated matching module
try:
    from contract_matcher import DateAwareContractMatcher
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from contract_matcher import DateAwareContractMatcher

@dataclass
class TestContract:
    """Test contract for matching analysis"""
    platform: str
    ticker: str
    question: str
    category: str
    expiry_date: str
    
@dataclass
class MatchResult:
    """Result of contract matching"""
    kalshi_contract: TestContract
    polymarket_contract: TestContract
    similarity_score: float
    date_alignment_score: float
    keyword_score: float
    final_score: float
    should_match: bool
    match_reason: str

def create_test_contracts() -> Tuple[List[TestContract], List[TestContract]]:
    """Create realistic test contracts for matching analysis - JULY 2025 FORWARD-LOOKING"""
    
    kalshi_contracts = [
        TestContract("Kalshi", "CPIAUG25", "Will CPI inflation be 3.0% or higher for August 2025?", "inflation", "2025-09-15"),
        TestContract("Kalshi", "FEDSEP25", "Will the Fed cut rates by 25 bps in September 2025?", "fed", "2025-09-18"),
        TestContract("Kalshi", "NASDAQ31DEC25", "Will NASDAQ close above 20000 on December 31, 2025?", "markets", "2025-12-31"),
        TestContract("Kalshi", "UNEMPLOYAUG25", "Will unemployment be below 4.0% in August 2025?", "employment", "2025-09-06"),
        TestContract("Kalshi", "BTCEND25", "Will Bitcoin close above $150k by end of 2025?", "crypto", "2026-01-01"),
        TestContract("Kalshi", "GDPQ325", "Will Q3 2025 GDP growth exceed 2.5%?", "gdp", "2025-10-30"),
        TestContract("Kalshi", "ELECTION26", "Will Republicans control House in 2026 midterms?", "election", "2026-11-03"),
    ]
    
    polymarket_contracts = [
        TestContract("Polymarket", "0x123abc", "CPI inflation above 3% in August 2025", "inflation", "2025-09-15"),
        TestContract("Polymarket", "0x456def", "Fed rate cut September 2025 meeting", "fed", "2025-09-18"),
        TestContract("Polymarket", "0x789ghi", "NASDAQ above 20000 end of year 2025", "markets", "2025-12-31"),
        TestContract("Polymarket", "0xabcdef", "Unemployment below 4% August 2025", "employment", "2025-09-06"),
        TestContract("Polymarket", "0xfedcba", "Bitcoin over $150,000 by 2025 end", "crypto", "2026-01-01"),
        TestContract("Polymarket", "0x111222", "US GDP growth Q3 2025 above 2.5%", "gdp", "2025-10-30"),
        TestContract("Polymarket", "0x333444", "Republicans win House majority 2026", "election", "2026-11-03"),
        TestContract("Polymarket", "0x555666", "Will CPI be above 3% in September 2025?", "inflation", "2025-10-15"),  # Different date
        TestContract("Polymarket", "0x777888", "Fed rate decision October 2025", "fed", "2025-10-29"),  # Different date
    ]
    
    return kalshi_contracts, polymarket_contracts

async def test_contract_matching():
    """Test the enhanced contract matching with date analysis"""
    print("🔍 TESTING CONTRACT MATCHING WITH DATE ANALYSIS")
    print("=" * 60)
    print("🎯 Goal: Ensure contracts with same dates + topics match strongly")
    print("⚠️  Issue: Current system may miss date importance")
    print()
    
    # Create test data
    kalshi_contracts, poly_contracts = create_test_contracts()
    matcher = DateAwareContractMatcher()
    
    print(f"📊 TEST DATA:")
    print(f"   Kalshi contracts: {len(kalshi_contracts)}")
    print(f"   Polymarket contracts: {len(poly_contracts)}")
    print()
    
    # Test matching for each Kalshi contract
    matches = []
    
    print("🔄 RUNNING ENHANCED MATCHING ANALYSIS...")
    print("=" * 60)
    
    for kalshi_contract in kalshi_contracts:
        print(f"\n📋 KALSHI: {kalshi_contract.question}")
        print(f"    Date: {kalshi_contract.expiry_date} | Category: {kalshi_contract.category}")
        
        best_match = None
        best_score = 0.0
        all_scores = []
        
        for poly_contract in poly_contracts:
            scores = matcher.enhanced_similarity_score(
                kalshi_contract.question, 
                poly_contract.question
            )
            
            all_scores.append({
                'poly_contract': poly_contract,
                'scores': scores
            })
            
            if scores['final_score'] > best_score:
                best_score = scores['final_score']
                best_match = poly_contract
        
        # Show top 3 matches for this Kalshi contract
        sorted_scores = sorted(all_scores, key=lambda x: x['scores']['final_score'], reverse=True)
        
        print(f"    🎯 TOP MATCHES:")
        for i, result in enumerate(sorted_scores[:3], 1):
            poly = result['poly_contract']
            scores = result['scores']
            
            match_quality = "🟢 EXCELLENT" if scores['final_score'] > 0.8 else \
                           "🟡 GOOD" if scores['final_score'] > 0.6 else \
                           "🟠 WEAK" if scores['final_score'] > 0.4 else "🔴 POOR"
            
            print(f"        #{i} {match_quality} ({scores['final_score']:.2f})")
            print(f"            📝 {poly.question}")
            print(f"            📊 Date: {scores['date_alignment']:.2f} | Keywords: {scores['keyword_score']:.2f} | Text: {scores['text_similarity']:.2f}")
            
            # Check if dates match
            k_dates = matcher.extract_dates(kalshi_contract.question)
            p_dates = matcher.extract_dates(poly.question)
            print(f"            📅 Kalshi dates: {k_dates}")
            print(f"            📅 Poly dates: {p_dates}")
        
        # Create match result
        if best_match and best_score > 0.5:
            match_result = MatchResult(
                kalshi_contract=kalshi_contract,
                polymarket_contract=best_match,
                similarity_score=sorted_scores[0]['scores']['text_similarity'],
                date_alignment_score=sorted_scores[0]['scores']['date_alignment'],
                keyword_score=sorted_scores[0]['scores']['keyword_score'],
                final_score=best_score,
                should_match=best_score > 0.7,
                match_reason="Date + keyword alignment" if sorted_scores[0]['scores']['date_alignment'] > 0.5 else "Keyword only"
            )
            matches.append(match_result)
    
    # Summary analysis
    print(f"\n📈 MATCHING ANALYSIS SUMMARY")
    print("=" * 50)
    
    high_quality_matches = [m for m in matches if m.final_score > 0.7]
    medium_quality_matches = [m for m in matches if 0.5 < m.final_score <= 0.7]
    
    print(f"🟢 High Quality Matches (>70%): {len(high_quality_matches)}")
    print(f"🟡 Medium Quality Matches (50-70%): {len(medium_quality_matches)}")
    print(f"🔴 Poor Matches (<50%): {len(kalshi_contracts) - len(matches)}")
    
    if high_quality_matches:
        print(f"\n✅ BEST MATCHES:")
        for match in high_quality_matches:
            print(f"   {match.kalshi_contract.ticker} ↔ {match.polymarket_contract.ticker[-6:]}")
            print(f"   Score: {match.final_score:.2f} (Date: {match.date_alignment_score:.2f})")
    
    # Show matches that should exist but scored poorly
    print(f"\n⚠️  POTENTIAL MISSED MATCHES (Poor Date Alignment):")
    poor_date_matches = [m for m in matches if m.keyword_score > 0.5 and m.date_alignment_score < 0.3]
    for match in poor_date_matches:
        print(f"   {match.kalshi_contract.ticker}: Good keywords but dates misaligned")
    
    return matches

async def test_date_extraction():
    """Test the date extraction functionality"""
    print("\n🗓️  TESTING DATE EXTRACTION")
    print("=" * 40)
    
    matcher = DateAwareContractMatcher()
    
    test_questions = [
        "Will CPI inflation be 3.0% or higher for August 2025?",
        "NASDAQ close above 20000 on December 31, 2025",
        "Fed rate cut in Q3 2025",
        "Bitcoin over $150k by end of 2025",
        "Unemployment below 4% in Aug 2025",
        "GDP growth Q3 2025 above 2.5%",
        "Election results November 5th, 2026",
        "CPI release September 15, 2025",
    ]
    
    for question in test_questions:
        dates = matcher.extract_dates(question)
        print(f"📝 '{question[:40]}...'")
        print(f"    📅 Extracted dates: {dates}")
    
    print(f"\n✅ Date extraction test complete!")

if __name__ == "__main__":
    async def run_all_tests():
        await test_date_extraction()
        await test_contract_matching()
        
        print(f"\n🎯 KEY INSIGHTS:")
        print(f"   ✅ Date alignment is CRITICAL for economic indicators")
        print(f"   ✅ Same event + same date = high confidence arbitrage")
        print(f"   ⚠️  Current system may underweight date importance")
        print(f"   💡 Solution: Increase date alignment weight to 50%")
    
    asyncio.run(run_all_tests())
