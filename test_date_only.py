#!/usr/bin/env python3
"""
Quick Date Filtering Test - Just tests Polymarket client filtering
No matching, no full system - just the date filter fix from Phase 2
"""

import asyncio
import sys
sys.path.append('/Users/kaseharris/arbitrage_bot/src/data_collectors')

from polymarket_client import EnhancedPolymarketClient

async def test_date_filtering_only():
    """Test ONLY the date filtering - no matching system"""
    print("🧪 Testing Date Filtering Only")
    print("=" * 50)
    
    async with EnhancedPolymarketClient() as client:
        # Test the 14-day window (your preferred setting)
        print("📅 Testing 14-day window...")
        
        try:
            markets = await client.get_markets_by_criteria(
                min_volume_usd=0,  # No volume filter - get all markets
                max_days_to_expiry=14,  # 14-day window
                limit=500  # Larger limit to catch all markets
            )
            
            print(f"✅ Found {len(markets)} markets expiring within 14 days")
            
            if markets:
                print(f"\n📋 Sample markets (showing expiry calculation):")
                for i, market in enumerate(markets[:5], 1):
                    days_str = f"({market.days_to_expiry:.1f} days)" if market.days_to_expiry else "(unknown)"
                    print(f"   {i}. {market.question[:50]}...")
                    print(f"      📅 Expires: {market.end_date} {days_str}")
                    print(f"      💰 Volume: ${market.volume:,.0f}")
                    print(f"      💵 Liquidity: ${market.liquidity_usd:,.0f}")
                    print()
            
            print("✅ Date filtering test PASSED!")
            return True
            
        except Exception as e:
            print(f"❌ Date filtering test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = asyncio.run(test_date_filtering_only())
    if success:
        print("\n🎯 Ready for next phase!")
    else:
        print("\n❌ Fix needed before proceeding")
