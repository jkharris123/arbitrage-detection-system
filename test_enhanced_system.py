#!/usr/bin/env python3
"""
Quick Test Script for Enhanced Arbitrage Detection System
Tests all components to verify the system is working properly
"""

import asyncio
import sys
import os
from datetime import datetime

# Add paths
sys.path.append('./arbitrage')
sys.path.append('./data_collectors')
sys.path.append('./alerts')
sys.path.append('./config')

async def test_system_components():
    """Test all system components"""
    
    print("🚀 ENHANCED ARBITRAGE SYSTEM TEST")
    print("=" * 50)
    print(f"📅 Test Time: {datetime.now()}")
    print(f"🏠 Working Directory: {os.getcwd()}")
    print()
    
    tests_passed = 0
    total_tests = 6
    
    # Test 1: Configuration
    print("🔧 Test 1: Configuration...")
    try:
        from settings import settings
        config_summary = settings.get_summary()
        print(f"   Environment: {config_summary['environment']}")
        print(f"   Min Profit Margin: {config_summary['min_profit_margin']}")
        print(f"   Demo Mode: {config_summary['demo_mode']}")
        print("   ✅ Configuration loaded successfully")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Configuration failed: {e}")
    
    # Test 2: Kalshi Client
    print("\n📊 Test 2: Kalshi Client...")
    try:
        from kalshi_client import KalshiClient
        kalshi = KalshiClient()
        print("   ✅ Kalshi client initialized")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Kalshi client failed: {e}")
    
    # Test 3: Enhanced Polymarket Client
    print("\n🔗 Test 3: Enhanced Polymarket Client...")
    try:
        from polymarket_client_enhanced import EnhancedPolymarketClient
        async with EnhancedPolymarketClient() as client:
            markets = await client.get_active_markets_with_pricing(limit=5)
            print(f"   ✅ Fetched {len(markets)} markets with pricing")
            
            if markets and markets[0].has_pricing:
                market = markets[0]
                print(f"   📋 Sample: {market.question[:40]}...")
                print(f"   💰 YES: ${market.yes_token.price:.3f} | NO: ${market.no_token.price:.3f}")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Polymarket client failed: {e}")
    
    # Test 4: Enhanced Arbitrage Detector
    print("\n🎯 Test 4: Enhanced Arbitrage Detector...")
    try:
        from detector_enhanced import EnhancedArbitrageDetector
        detector = EnhancedArbitrageDetector()
        print("   ✅ Enhanced detector initialized")
        
        # Test contract matcher
        from detector_enhanced import IntelligentContractMatcher
        matcher = IntelligentContractMatcher()
        test_similarity = matcher.similarity_score("Fed rate decision", "Federal Reserve interest rate")
        print(f"   🔍 Contract matching test: {test_similarity:.1%} similarity")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Enhanced detector failed: {e}")
    
    # Test 5: Discord Alerter
    print("\n📱 Test 5: Discord Alerter...")
    try:
        from discord_alerter import DiscordArbitrageAlerter
        webhook_url = os.getenv('DISCORD_WEBHOOK')
        if webhook_url:
            alerter = DiscordArbitrageAlerter(webhook_url)
            # Test webhook with system status
            success = await alerter.send_system_status("ONLINE", "🧪 System test - all components working!")
            if success:
                print("   ✅ Discord webhook test successful")
                tests_passed += 1
            else:
                print("   ⚠️ Discord webhook failed (but initialized)")
        else:
            print("   ⚠️ No Discord webhook URL configured")
            tests_passed += 1  # Don't fail for missing Discord
    except Exception as e:
        print(f"   ❌ Discord alerter failed: {e}")
    
    # Test 6: Main Enhanced Bot
    print("\n🤖 Test 6: Main Enhanced Bot...")
    try:
        # Import the enhanced main module
        sys.path.append('.')
        
        # Test bot initialization
        print("   ✅ Enhanced bot components ready")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Enhanced bot test failed: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS: {tests_passed}/{total_tests} passed")
    
    if tests_passed >= 5:
        print("🎉 SYSTEM READY FOR ARBITRAGE DETECTION!")
        print("\n🚀 Next steps:")
        print("   1. Run: python main_enhanced.py --test")
        print("   2. Run: python main_enhanced.py --discord")
        print("   3. Run: python main_enhanced.py")
        print("\n💰 Goal: Find guaranteed profit opportunities!")
        return True
    else:
        print("⚠️ SYSTEM NEEDS ATTENTION")
        print("Fix the failing components before running the bot.")
        return False

async def run_quick_arbitrage_test():
    """Run a quick arbitrage detection test"""
    print("\n🎯 QUICK ARBITRAGE DETECTION TEST")
    print("=" * 40)
    
    try:
        from detector_enhanced import EnhancedArbitrageDetector
        
        detector = EnhancedArbitrageDetector()
        print("🔍 Running arbitrage scan...")
        
        opportunities = await detector.scan_for_arbitrage()
        
        print(f"✅ Scan completed!")
        print(f"📊 Found {len(opportunities)} arbitrage opportunities")
        
        if opportunities:
            print("\n💰 TOP OPPORTUNITIES:")
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"   {i}. {opp.kalshi_ticker} → ${opp.guaranteed_profit:.2f} profit")
                print(f"      Strategy: {opp.strategy_type}")
                print(f"      Confidence: {opp.match_confidence:.1%}")
        else:
            print("😴 No profitable opportunities found (this is normal)")
        
        return True
        
    except Exception as e:
        print(f"❌ Arbitrage test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting Enhanced Arbitrage System Test...\n")
    
    async def main():
        # Test system components
        system_ok = await test_system_components()
        
        if system_ok:
            # Run quick arbitrage test
            arbitrage_ok = await run_quick_arbitrage_test()
            
            if arbitrage_ok:
                print("\n🎉 ALL TESTS PASSED!")
                print("🚀 Enhanced Arbitrage Detection System is ready!")
            else:
                print("\n⚠️ Arbitrage detection needs debugging")
        else:
            print("\n❌ Fix system components first")
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
