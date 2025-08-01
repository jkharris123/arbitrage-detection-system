#!/usr/bin/env python3
"""
Test Individual Contract Fetching
Verify we get individual Fed rate contracts (0%, 0.25%, 0.5%, etc.)
"""

import sys
sys.path.append('./data_collectors')

from kalshi_client import KalshiClient
import asyncio
from polymarket_client import EnhancedPolymarketClient

def test_kalshi_individual_contracts():
    """Test Kalshi for individual threshold contracts"""
    print("🔍 Testing Kalshi Individual Contracts\n")
    
    client = KalshiClient(verbose=False)
    
    # Get all active markets
    markets = client.get_markets_by_criteria(
        max_days_to_expiry=30,
        min_volume=10
    )
    
    print(f"📊 Total Kalshi markets found: {len(markets)}")
    
    # Group by event
    events = {}
    for market in markets:
        event = market.get('event_ticker', 'UNKNOWN')
        if event not in events:
            events[event] = []
        events[event].append(market)
    
    # Find Fed-related events
    fed_events = {k: v for k, v in events.items() if 'FED' in k.upper()}
    
    print(f"\n🏦 Fed-related events: {len(fed_events)}")
    
    for event_ticker, contracts in fed_events.items():
        print(f"\n📍 Event: {event_ticker}")
        print(f"   Number of contracts: {len(contracts)}")
        
        # Show all contracts for this event
        for contract in contracts:
            title = contract.get('title', '')
            ticker = contract.get('ticker', '')
            yes_price = contract.get('yes_price', 0)
            no_price = contract.get('no_price', 0)
            volume = contract.get('volume', 0)
            
            print(f"\n   Contract: {ticker}")
            print(f"   Title: {title}")
            print(f"   YES: ${yes_price:.2f} | NO: ${no_price:.2f}")
            print(f"   Volume: {volume:,}")
    
    # Also look for CPI, unemployment, etc.
    interesting_events = ['CPI', 'UNEMPLOYMENT', 'GDP', 'PAYROLL', 'INFLATION']
    
    print("\n\n📈 Other multi-threshold events:")
    for keyword in interesting_events:
        matching_events = {k: v for k, v in events.items() if keyword in k.upper() and len(v) > 1}
        
        if matching_events:
            for event_ticker, contracts in list(matching_events.items())[:2]:  # Show first 2
                print(f"\n📍 {event_ticker} ({len(contracts)} contracts):")
                for i, contract in enumerate(contracts[:5]):  # Show first 5 contracts
                    print(f"   {i+1}. {contract['ticker']}: {contract.get('title', '')[:60]}...")

async def test_polymarket_individual_contracts():
    """Test Polymarket for individual threshold contracts"""
    print("\n\n🔍 Testing Polymarket Individual Contracts\n")
    
    async with EnhancedPolymarketClient() as client:
        markets = await client.get_markets_by_criteria(
            max_days_to_expiry=30,
            min_volume_usd=100,
            limit=500
        )
        
        print(f"📊 Total Polymarket markets found: {len(markets)}")
        
        # Look for Fed-related markets
        fed_markets = [m for m in markets if 'fed' in m.question.lower() or 'rate' in m.question.lower()]
        
        print(f"\n🏦 Fed/rate-related markets: {len(fed_markets)}")
        
        for i, market in enumerate(fed_markets[:10]):  # Show first 10
            print(f"\n{i+1}. {market.question}")
            if market.has_pricing:
                print(f"   YES: ${market.yes_token.price:.3f} | NO: ${market.no_token.price:.3f}")
                print(f"   Volume: ${market.volume_24h:,.0f}")
        
        # Look for threshold patterns
        print("\n\n🎯 Markets with specific thresholds:")
        
        import re
        threshold_pattern = r'\b(\d+\.?\d*)\s*%'
        
        threshold_markets = []
        for market in markets:
            matches = re.findall(threshold_pattern, market.question)
            if matches:
                threshold_markets.append((market, matches))
        
        print(f"Found {len(threshold_markets)} markets with percentage thresholds")
        
        # Group similar questions
        question_groups = {}
        for market, thresholds in threshold_markets[:20]:  # Analyze first 20
            # Extract base question (remove numbers)
            base = re.sub(r'\d+\.?\d*\s*%?', 'X', market.question)
            base = base.strip()
            
            if base not in question_groups:
                question_groups[base] = []
            question_groups[base].append((market, thresholds))
        
        # Show groups with multiple thresholds
        print("\n📊 Question groups with multiple threshold values:")
        for base, group in question_groups.items():
            if len(group) > 1:
                print(f"\n🔹 Base: {base[:80]}...")
                print(f"   Variants: {len(group)}")
                for market, thresholds in group[:5]:
                    print(f"      - Threshold {thresholds[0]}%: {market.condition_id[:16]}...")

def main():
    """Run all tests"""
    print("🚀 Testing Individual Contract Fetching\n")
    print("Goal: Verify we get individual contracts for different thresholds")
    print("=" * 60)
    
    # Test Kalshi
    test_kalshi_individual_contracts()
    
    # Test Polymarket
    asyncio.run(test_polymarket_individual_contracts())
    
    print("\n\n✅ Test complete!")
    print("\n📝 Key things to verify:")
    print("1. Fed events should have multiple contracts (0%, 0.25%, 0.5%, etc.)")
    print("2. Each contract should have a unique ticker/condition_id")
    print("3. Similar questions with different thresholds should be separate contracts")

if __name__ == "__main__":
    main()
