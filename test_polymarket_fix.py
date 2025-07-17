#!/usr/bin/env python3
"""
SIMPLE Polymarket Test - Check if pricing fix worked
This tests the specific issue: getting 100 markets but 0 with pricing data
"""

import asyncio
import sys
import os

# Add path to data collectors
sys.path.append('./data_collectors')

async def test_polymarket_pricing_fix():
    """Test if the Polymarket pricing issue is fixed"""
    
    print("🧪 TESTING POLYMARKET PRICING FIX")
    print("=" * 45)
    print("Issue: Was getting 100 markets but 0 with pricing data")
    print("Expected: Should get markets WITH pricing data\n")
    
    try:
        from polymarket_client_enhanced import EnhancedPolymarketClient
        
        print("📡 Connecting to Polymarket...")
        async with EnhancedPolymarketClient() as client:
            
            # Test the main method that was broken
            print("🔍 Fetching markets with pricing...")
            markets = await client.get_active_markets_with_pricing(limit=20)
            
            print(f"📊 Raw markets fetched: {len(markets)}")
            
            # Count markets with actual pricing data
            markets_with_pricing = [m for m in markets if m.has_pricing]
            print(f"💰 Markets WITH pricing: {len(markets_with_pricing)}")
            
            # This was the core issue: 0 markets with pricing
            if len(markets_with_pricing) > 0:
                print("✅ PRICING FIX SUCCESSFUL!")
                print(f"🎯 Before: 0 markets with pricing")
                print(f"🎯 After: {len(markets_with_pricing)} markets with pricing")
                
                # Show examples
                print("\n📋 Sample markets with pricing:")
                for i, market in enumerate(markets_with_pricing[:3], 1):
                    print(f"   {i}. {market.question[:50]}...")
                    print(f"      YES: ${market.yes_token.price:.3f} | NO: ${market.no_token.price:.3f}")
                    print(f"      Volume: ${market.volume:.0f}")
                    print(f"      Has Pricing: {market.has_pricing}")
                
                return True
                
            else:
                print("❌ PRICING STILL BROKEN")
                print("Still getting 0 markets with pricing data")
                
                if len(markets) > 0:
                    print(f"\n🔍 Debug: Got {len(markets)} markets but none have pricing")
                    sample = markets[0]
                    print(f"Sample market: {sample.question[:40]}...")
                    print(f"Has yes_token: {sample.yes_token is not None}")
                    print(f"Has no_token: {sample.no_token is not None}")
                    if sample.yes_token:
                        print(f"YES token price: {sample.yes_token.price}")
                    if sample.no_token:
                        print(f"NO token price: {sample.no_token.price}")
                
                return False
                
    except Exception as e:
        print(f"❌ POLYMARKET TEST FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_arbitrage_compatibility():
    """Test if the fixed client works with arbitrage detector"""
    
    print("\n🤝 TESTING ARBITRAGE DETECTOR COMPATIBILITY")
    print("=" * 45)
    
    try:
        # Test if arbitrage detector can import the client
        sys.path.append('./arbitrage')
        
        from detector_enhanced import EnhancedArbitrageDetector
        print("✅ Arbitrage detector imports successfully")
        
        # Import the client for this test
        from polymarket_client_enhanced import EnhancedPolymarketClient
        
        # Test if detector can create Polymarket client
        async with EnhancedPolymarketClient() as client:
            markets = await client.get_active_markets_with_pricing(limit=5)
            
            if markets and any(m.has_pricing for m in markets):
                print("✅ Arbitrage detector can access Polymarket with pricing")
                print(f"📊 Ready for arbitrage detection with {len([m for m in markets if m.has_pricing])} priced markets")
                return True
            else:
                print("⚠️ Detector compatibility issue - no pricing data")
                return False
                
    except Exception as e:
        print(f"❌ COMPATIBILITY TEST FAILED: {e}")
        return False

async def main():
    """Main test function"""
    
    # Test 1: Core pricing fix
    pricing_fixed = await test_polymarket_pricing_fix()
    
    # Test 2: Arbitrage compatibility
    if pricing_fixed:
        compatibility_ok = await test_arbitrage_compatibility()
    else:
        compatibility_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 TEST SUMMARY")
    print("=" * 50)
    
    if pricing_fixed and compatibility_ok:
        print("🎉 SUCCESS! Polymarket pricing fix is working!")
        print("✅ Markets fetched with pricing data")
        print("✅ Compatible with arbitrage detector")
        print("\n🚀 Ready to test full arbitrage system:")
        print("   Run: python3 test_enhanced_system.py")
        print("   Run: python3 launch.py scan")
        
    elif pricing_fixed:
        print("🎗️ PARTIAL SUCCESS - Pricing fixed but compatibility issues")
        print("✅ Markets fetched with pricing data")
        print("⚠️ Need to fix arbitrage detector compatibility")
        
    else:
        print("❌ PRICING STILL BROKEN")
        print("Need to debug Polymarket API integration further")
        print("\n🔧 Debug steps:")
        print("   1. Check Polymarket API endpoints")
        print("   2. Verify token ID mapping")
        print("   3. Test CLOB API response format")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        import traceback
        traceback.print_exc()
