#!/usr/bin/env python3
"""
DIAGNOSTIC TEST - Verify Contract Collection & Matching
Goal: Find out exactly what's happening with our data
"""

import asyncio
import sys
import json
from datetime import datetime

# Add paths
sys.path.append('./data_collectors')
sys.path.append('./arbitrage')
sys.path.append('./')

from kalshi_client import KalshiClient
from polymarket_client_enhanced import EnhancedPolymarketClient

# Import matching
try:
    from contract_matcher import DateAwareContractMatcher
except ImportError:
    from detector_enhanced import DateAwareContractMatcher

async def diagnostic_test():
    """Comprehensive diagnostic of what's actually happening"""
    print("🔍 DIAGNOSTIC TEST - Let's see what's really happening")
    print("=" * 70)
    
    # Test 1: Kalshi Data Quality
    print("\n📊 TEST 1: Kalshi Data Quality")
    try:
        kalshi_client = KalshiClient()
        kalshi_raw = kalshi_client.get_markets(limit_per_page=1000)
        print(f"📈 Raw Kalshi markets returned: {len(kalshi_raw)}")
        
        # Check for duplicates
        tickers = [m.get('ticker', '') for m in kalshi_raw if m.get('ticker')]
        unique_tickers = set(tickers)
        print(f"📊 Unique tickers: {len(unique_tickers)}")
        print(f"📊 Total tickers: {len(tickers)}")
        print(f"🔍 Duplicates: {len(tickers) - len(unique_tickers)}")
        
        # Show sample data
        print(f"\n📋 Sample Kalshi contracts:")
        for i, market in enumerate(kalshi_raw[:5], 1):
            title = market.get('title', market.get('question', 'NO_TITLE'))
            ticker = market.get('ticker', 'NO_TICKER')
            print(f"   {i}. {ticker}: {title[:60]}...")
        
        # Process valid contracts
        valid_kalshi = []
        categories = {}
        
        for market in kalshi_raw:
            title = market.get('title', market.get('question', ''))
            ticker = market.get('ticker', '')
            
            if title and ticker and len(title.strip()) > 10:
                category = 'economics' if any(word in title.lower() for word in ['cpi', 'fed', 'gdp']) else 'other'
                categories[category] = categories.get(category, 0) + 1
                
                valid_kalshi.append({
                    'ticker': ticker,
                    'question': title,
                    'category': category,
                    'volume': float(market.get('volume', 0))
                })
        
        print(f"✅ Valid Kalshi contracts after processing: {len(valid_kalshi)}")
        print(f"📊 Categories: {categories}")
        
    except Exception as e:
        print(f"❌ Kalshi test failed: {e}")
        valid_kalshi = []
    
    # Test 2: Polymarket Data Quality
    print(f"\n📊 TEST 2: Polymarket Data Quality")
    try:
        async with EnhancedPolymarketClient() as client:
            poly_markets = await client.get_active_markets_with_pricing(limit=2000)
            print(f"📈 Polymarket markets returned: {len(poly_markets)}")
            
            # Check for duplicates
            condition_ids = [m.condition_id for m in poly_markets]
            unique_ids = set(condition_ids)
            print(f"📊 Unique condition IDs: {len(unique_ids)}")
            print(f"📊 Total markets: {len(condition_ids)}")
            print(f"🔍 Duplicates: {len(condition_ids) - len(unique_ids)}")
            
            # Check pricing
            with_pricing = [m for m in poly_markets if m.has_pricing]
            print(f"📊 Markets with pricing: {len(with_pricing)}")
            
            # Show sample data
            print(f"\n📋 Sample Polymarket contracts:")
            for i, market in enumerate(poly_markets[:5], 1):
                print(f"   {i}. {market.condition_id[:12]}...: {market.question[:60]}...")
                if market.has_pricing:
                    print(f"      YES: ${market.yes_token.price:.3f} | NO: ${market.no_token.price:.3f}")
                else:
                    print(f"      NO PRICING DATA")
            
            # Categories
            categories = {}
            for market in poly_markets:
                categories[market.category] = categories.get(market.category, 0) + 1
            print(f"📊 Categories: {dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))}")
            
    except Exception as e:
        print(f"❌ Polymarket test failed: {e}")
        poly_markets = []
    
    # Test 3: Matching Logic
    print(f"\n📊 TEST 3: Matching Logic Test")
    try:
        matcher = DateAwareContractMatcher()
        
        # Test with sample similar contracts
        test_cases = [
            {
                'kalshi': 'Will the Fed cut interest rates by 25 basis points in December 2024?',
                'poly': 'Fed will cut rates by 0.25% in December 2024',
                'expected': 'HIGH'
            },
            {
                'kalshi': 'Will CPI inflation be above 3% in November 2024?',
                'poly': 'US CPI inflation rate will exceed 3.0% in November',
                'expected': 'HIGH'
            },
            {
                'kalshi': 'Will Bitcoin close above $50,000 on December 31?',
                'poly': 'Will the S&P 500 hit a new high?',
                'expected': 'LOW'
            }
        ]
        
        print(f"🔍 Testing matching algorithm with sample pairs:")
        for i, test in enumerate(test_cases, 1):
            try:
                scores = matcher.enhanced_similarity_score(test['kalshi'], test['poly'])
                print(f"\n   Test {i} ({test['expected']} expected):")
                print(f"   Kalshi: {test['kalshi'][:50]}...")
                print(f"   Poly:   {test['poly'][:50]}...")
                print(f"   Score:  {scores['final_score']:.3f}")
                print(f"   Text:   {scores['text_similarity']:.3f}")
                print(f"   Date:   {scores['date_alignment']:.3f}")
                print(f"   Keywords: {scores['keyword_score']:.3f}")
                
                if scores['final_score'] > 0.5:
                    print(f"   ✅ WOULD MATCH (above 0.5 threshold)")
                else:
                    print(f"   ❌ Would not match (below 0.5 threshold)")
                    
            except Exception as e:
                print(f"   ❌ Matching test {i} failed: {e}")
    
    except Exception as e:
        print(f"❌ Matching logic test failed: {e}")
    
    # Test 4: Real Cross-Platform Matching
    print(f"\n📊 TEST 4: Real Cross-Platform Matching Sample")
    if len(valid_kalshi) > 0 and len(poly_markets) > 0:
        print(f"🔍 Testing first 5 Kalshi contracts against all Polymarket contracts...")
        
        matcher = DateAwareContractMatcher()
        
        for i, kalshi_contract in enumerate(valid_kalshi[:5], 1):
            print(f"\n   Testing Kalshi {i}: {kalshi_contract['ticker']}")
            print(f"   Question: {kalshi_contract['question'][:60]}...")
            
            best_score = 0.0
            best_match = None
            matches_above_threshold = 0
            
            for poly_contract in poly_markets:
                try:
                    scores = matcher.enhanced_similarity_score(
                        kalshi_contract['question'], 
                        poly_contract.question
                    )
                    
                    if scores['final_score'] > best_score:
                        best_score = scores['final_score']
                        best_match = poly_contract
                    
                    if scores['final_score'] > 0.3:  # Count how many above threshold
                        matches_above_threshold += 1
                        
                except Exception as e:
                    continue
            
            print(f"   Best Score: {best_score:.3f}")
            print(f"   Matches above 0.3: {matches_above_threshold}")
            if best_match:
                print(f"   Best Match: {best_match.question[:60]}...")
            else:
                print(f"   No good matches found")
    
    # Test 5: Data Format Verification
    print(f"\n📊 TEST 5: Data Format Verification")
    
    if len(valid_kalshi) > 0:
        sample_kalshi = valid_kalshi[0]
        print(f"📋 Sample Kalshi format:")
        for key, value in sample_kalshi.items():
            print(f"   {key}: {str(value)[:50]}...")
    
    if len(poly_markets) > 0:
        sample_poly = poly_markets[0]
        print(f"📋 Sample Polymarket format:")
        print(f"   condition_id: {sample_poly.condition_id}")
        print(f"   question: {sample_poly.question[:50]}...")
        print(f"   category: {sample_poly.category}")
        print(f"   has_pricing: {sample_poly.has_pricing}")
        if sample_poly.has_pricing:
            print(f"   yes_price: {sample_poly.yes_token.price}")
            print(f"   no_price: {sample_poly.no_token.price}")
    
    # Summary
    print(f"\n🎯 DIAGNOSTIC SUMMARY")
    print(f"=" * 70)
    print(f"📊 Kalshi: {len(valid_kalshi)} valid contracts")
    print(f"📊 Polymarket: {len(poly_markets)} contracts")
    if len(poly_markets) > 0:
        with_pricing = len([m for m in poly_markets if m.has_pricing])
        print(f"📊 Polymarket with pricing: {with_pricing}")
    
    if len(valid_kalshi) == 0:
        print(f"🚨 ISSUE: No valid Kalshi contracts - check data processing")
    elif len(valid_kalshi) > 10000:
        print(f"🚨 ISSUE: Too many Kalshi contracts ({len(valid_kalshi)}) - likely duplicates")
    else:
        print(f"✅ Kalshi contract count looks reasonable")
    
    if len(poly_markets) == 0:
        print(f"🚨 ISSUE: No Polymarket contracts - check API connection")
    elif len(poly_markets) < 100:
        print(f"🚨 ISSUE: Too few Polymarket contracts - may need more API calls")
    else:
        print(f"✅ Polymarket contract count looks good")

if __name__ == "__main__":
    asyncio.run(diagnostic_test())
