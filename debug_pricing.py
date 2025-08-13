#!/usr/bin/env python3
"""
Debug pricing extraction from Gamma API
"""

import asyncio
import sys
import json
sys.path.append('/Users/kaseharris/arbitrage_bot/src/data_collectors')

from polymarket_client import EnhancedPolymarketClient

async def debug_pricing():
    """Debug why pricing extraction is failing"""
    print("🔍 Debugging Pricing Extraction")
    print("=" * 50)
    
    async with EnhancedPolymarketClient() as client:
        # Get more raw gamma data to find active markets
        gamma_markets = await client._get_all_gamma_markets(limit=200)
        
        print(f"📊 Got {len(gamma_markets)} raw markets")
        
        # Analyze market states
        active_count = 0
        closed_count = 0
        resolved_count = 0
        future_count = 0
        
        active_markets = []
        
        for market in gamma_markets:
            is_closed = market.get('closed', False)
            is_resolved = market.get('umaResolutionStatus') == 'resolved'
            prices = market.get('outcomePrices', '[]')
            
            if is_closed:
                closed_count += 1
            elif is_resolved:
                resolved_count += 1
            else:
                active_count += 1
                active_markets.append(market)
                
        print(f"\n📈 Market Analysis:")
        print(f"   ✅ Active: {active_count}")
        print(f"   🔒 Closed: {closed_count}")
        print(f"   ✅ Resolved: {resolved_count}")
        
        if active_markets:
            print(f"\n🎯 Found {len(active_markets)} active markets!")
            
            # Test conversion on first active market
            first_active = active_markets[0]
            print(f"\n🔍 Testing active market:")
            print(f"   Question: {first_active.get('question', 'N/A')}")
            print(f"   Closed: {first_active.get('closed', False)}")
            print(f"   Resolved: {first_active.get('umaResolutionStatus', 'N/A')}")
            print(f"   OutcomePrices: {first_active.get('outcomePrices', 'N/A')}")
            print(f"   End Date: {first_active.get('endDate', 'N/A')}")
            
            # Try conversion
            try:
                converted = client._gamma_market_to_polymarket(first_active)
                if converted:
                    print(f"\n✅ Conversion SUCCESS!")
                    print(f"   Question: {converted.question}")
                    print(f"   Has pricing: {converted.has_pricing}")
                    if converted.yes_token:
                        print(f"   YES price: ${converted.yes_token.price:.3f}")
                    if converted.no_token:
                        print(f"   NO price: ${converted.no_token.price:.3f}")
                    print(f"   Volume: ${converted.volume:,.0f}")
                    print(f"   End date: {converted.end_date}")
                else:
                    print(f"\n❌ Conversion returned None (probably rejected for good reason)")
            except Exception as e:
                print(f"\n❌ Conversion failed: {e}")
                import traceback
                traceback.print_exc()
                
        else:
            print(f"\n⚠️ No active markets found - all are closed/resolved")
            print(f"This is normal for sports betting markets that update frequently")

if __name__ == "__main__":
    asyncio.run(debug_pricing())
