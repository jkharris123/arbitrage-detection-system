#!/usr/bin/env python3
"""
Quick test of the updated Polymarket client
Focus on getting OPEN markets only
"""

import asyncio
import sys
sys.path.append('/Users/kaseharris/arbitrage_bot')

from src.data_collectors.polymarket_client import EnhancedPolymarketClient
from datetime import datetime, timezone

async def test_polymarket_client():
    """Test the updated Polymarket client"""
    print("🔍 Testing Updated Polymarket Client")
    print(f"📅 Current time: {datetime.now(timezone.utc)}")
    print("="*60)
    
    async with EnhancedPolymarketClient() as client:
        # Test 1: Get all active markets
        print("\n1️⃣ Getting active markets with pricing...")
        markets = await client.get_active_markets_with_pricing(limit=500)
        
        print(f"\n✅ Found {len(markets)} OPEN markets")
        
        if markets:
            # Show first 10 markets
            print("\n📋 First 10 open markets:")
            for i, market in enumerate(markets[:10], 1):
                print(f"\n{i}. {market.question[:80]}...")
                print(f"   YES: ${market.yes_token.price:.3f} | NO: ${market.no_token.price:.3f}")
                print(f"   Volume: ${market.volume:,.2f} | Liquidity: ${market.liquidity_usd:,.2f}")
                print(f"   End date: {market.end_date}")
                print(f"   Condition ID: {market.condition_id}")
        
        # Test 2: Get markets with criteria
        print("\n2️⃣ Testing filtered markets (min volume $1000, max 30 days)...")
        filtered_markets = await client.get_markets_by_criteria(
            min_volume_usd=1000,
            max_days_to_expiry=30,
            limit=100
        )
        
        print(f"\n✅ Found {len(filtered_markets)} filtered markets")
        
        if filtered_markets:
            print("\n📋 First 5 filtered markets:")
            for i, market in enumerate(filtered_markets[:5], 1):
                print(f"\n{i}. {market.question[:80]}...")
                print(f"   Volume: ${market.volume:,.2f} | Liquidity: ${market.liquidity_usd:,.2f}")
                if hasattr(market, 'days_to_expiry'):
                    print(f"   Days to expiry: {market.days_to_expiry:.1f}")
        
        return len(markets) > 0

if __name__ == "__main__":
    success = asyncio.run(test_polymarket_client())
    if success:
        print("\n✅ SUCCESS! Polymarket client is working!")
    else:
        print("\n❌ FAILED! No markets found")
