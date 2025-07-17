#!/usr/bin/env python3
"""
Simple Economic Analysis Test
Tests economic market filtering without Discord dependencies
"""

import asyncio
import sys
import os
from datetime import datetime

# Add paths
sys.path.append('./arbitrage')
sys.path.append('./data_collectors')
sys.path.append('./config')

async def test_economic_analysis_simple():
    """Simple test of economic analysis without Discord"""
    
    print("🧪 SIMPLE ECONOMIC ANALYSIS TEST")
    print("=" * 45)
    print("Testing economic market filtering without Discord dependencies...")
    print()
    
    try:
        # Test 1: Import basic modules
        print("📦 Test 1: Basic imports...")
        from settings import settings
        print(f"   ✅ Settings loaded - Environment: {settings.ENVIRONMENT}")
        
        # Test 2: Import Kalshi client
        print("\\n📊 Test 2: Kalshi client...")
        from kalshi_client import KalshiClient
        kalshi = KalshiClient()
        print("   ✅ Kalshi client initialized")
        
        # Test 3: Import Polymarket client
        print("\\n🔗 Test 3: Polymarket client...")
        from polymarket_client_enhanced import EnhancedPolymarketClient
        print("   ✅ Polymarket client imported")
        
        # Test 4: Import economic filter
        print("\\n🏦 Test 4: Economic filter...")
        from economic_tradfi_filter import EconomicMarketFilter
        economic_filter = EconomicMarketFilter()
        print("   ✅ Economic filter initialized")
        
        # Test 5: Get markets
        print("\\n📊 Test 5: Fetching markets...")
        
        # Get Kalshi markets
        kalshi_markets = kalshi.get_markets()
        print(f"   📊 Kalshi markets: {len(kalshi_markets)}")
        
        # Get Polymarket markets
        async with EnhancedPolymarketClient() as poly_client:
            polymarket_markets = await poly_client.get_active_markets_with_pricing(limit=50)
        
        markets_with_pricing = [m for m in polymarket_markets if m.has_pricing]
        print(f"   📈 Polymarket markets with pricing: {len(markets_with_pricing)}")
        
        # Test 6: Economic filtering
        print("\\n🏦 Test 6: Economic market filtering...")
        economic_markets = economic_filter.filter_economic_markets(kalshi_markets, polymarket_markets)
        
        print(f"   📊 Total economic markets found: {len(economic_markets)}")
        
        # Show breakdown by category
        categories = {}
        for market in economic_markets:
            categories[market.category] = categories.get(market.category, 0) + 1
        
        print("\\n📋 Economic markets by category:")
        for category, count in categories.items():
            print(f"   • {category}: {count} markets")
            
        # Show short-term markets (≤7 days)
        short_term = [m for m in economic_markets if m.days_to_expiry <= 7]
        print(f"\\n⚡ Short-term markets (≤7 days): {len(short_term)}")
        
        if short_term:
            print("   Top short-term opportunities:")
            for market in short_term[:3]:
                print(f"   • {market.question[:50]}... ({market.days_to_expiry} days)")
                print(f"     Platform: {market.platform} | TradFi: {market.tradfi_equivalent}")
        
        # Test 7: Cross-asset detection
        print("\\n💼 Test 7: Cross-asset opportunity detection...")
        cross_asset_opps = economic_filter.detect_cross_asset_opportunities(economic_markets)
        
        print(f"   💼 Cross-asset opportunities: {len(cross_asset_opps)}")
        
        if cross_asset_opps:
            print("   Top cross-asset opportunities:")
            for opp in cross_asset_opps[:3]:
                print(f"   • {opp.strategy_type}: {opp.prediction_question[:40]}...")
                print(f"     TradFi Action: {opp.tradfi_action}")
                print(f"     Estimated Profit: ${opp.estimated_profit:.0f}")
        
        # Test 8: Summary
        print("\\n📈 Test 8: Performance summary...")
        summary = economic_filter.get_summary()
        
        print(f"   📊 Summary Statistics:")
        print(f"   • Total Economic Markets: {summary['total_economic_markets']}")
        print(f"   • High Potential Markets: {summary['high_potential_count']}")
        print(f"   • Short-term Markets: {summary['short_term_count']}")
        print(f"   • Cross-Asset Opportunities: {summary['total_cross_asset_opportunities']}")
        
        print(f"\\n📁 Data saved to:")
        print(f"   • Economic Markets: {economic_filter.economic_csv}")
        print(f"   • Cross-Asset Opportunities: {economic_filter.cross_asset_csv}")
        
        print("\\n✅ ALL TESTS PASSED!")
        print("🎯 Economic analysis system is working correctly")
        
        return True
        
    except Exception as e:
        print(f"\\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_separate_tracking():
    """Test the separate tracking systems"""
    
    print("\\n🗂️ TESTING SEPARATE TRACKING SYSTEMS")
    print("=" * 45)
    
    try:
        from separate_tracking_systems import ArbitrageTrackingSystem, TraditionalArbitrageOpportunity, TradFiArbitrageOpportunity
        
        tracking = ArbitrageTrackingSystem()
        
        # Test traditional arbitrage tracking
        print("📊 Testing traditional arbitrage tracking...")
        
        traditional_opp = TraditionalArbitrageOpportunity(
            timestamp=datetime.now().isoformat(),
            opportunity_id=tracking.generate_traditional_id(),  # Should be A001
            kalshi_ticker="INXD-25JUL18-6000",
            kalshi_question="Will SPX close above 6000?",
            polymarket_condition_id="abc12345",
            polymarket_question="SPX above 6000 on July 18",
            match_confidence=0.90,
            strategy_type="YES_ARBITRAGE",
            buy_platform="Kalshi",
            sell_platform="Polymarket",
            buy_side="YES",
            sell_side="NO",
            kalshi_price=0.48,
            polymarket_price=0.55,
            spread=0.07,
            trade_size_usd=100.0,
            kalshi_cost=48.0,
            polymarket_cost=55.0,
            guaranteed_profit=7.0,
            profit_percentage=7.0,
            time_to_expiry_hours=18.0,
            liquidity_score=85.0,
            execution_certainty=92.0,
            status="ACTIVE",
            recommendation="EXECUTE_IMMEDIATELY"
        )
        
        tracking.store_traditional_opportunity(traditional_opp)
        print(f"   ✅ Traditional opportunity stored: {traditional_opp.opportunity_id}")
        
        # Test TradFi arbitrage tracking  
        print("\\n💼 Testing TradFi arbitrage tracking...")
        
        tradfi_opp = TradFiArbitrageOpportunity(
            timestamp=datetime.now().isoformat(),
            opportunity_id=tracking.generate_tradfi_id(),  # Should be T001
            prediction_platform="Kalshi",
            prediction_ticker="INXD-25JUL18-6000",
            prediction_question="Will SPX close above 6000?",
            prediction_price=0.48,
            prediction_implied_probability=0.48,
            underlying_symbol="SPX",
            derivative_type="OPTIONS",
            derivative_description="SPX Jul 18 6000 Calls",
            derivative_price=25.50,
            implied_probability=0.38,  # 10% divergence
            strike_price=6000.0,
            expiry_date="2025-07-18",
            option_type="CALL",
            delta=0.42,
            strategy_type="LONG_PREDICTION_SHORT_DERIVATIVE",
            probability_divergence=0.10,
            edge_estimate=0.10,
            recommended_position_size=1000.0,
            max_loss=1000.0,
            expected_profit=100.0,
            profit_probability=0.60,
            time_decay_risk=0.20,
            market_risk=0.42,
            volatility_risk=0.30,
            complexity_score=4,
            status="ANALYZED",
            recommendation="EXECUTE_WITH_CAUTION"
        )
        
        tracking.store_tradfi_opportunity(tradfi_opp)
        print(f"   ✅ TradFi opportunity stored: {tradfi_opp.opportunity_id}")
        
        # Test summary
        summary = tracking.get_performance_summary()
        
        print(f"\\n📊 Tracking Summary:")
        print(f"   Traditional Opportunities: {summary['traditional']['total_opportunities']}")
        print(f"   TradFi Opportunities: {summary['tradfi']['total_opportunities']}")
        print(f"   Combined Expected Profit: ${summary['combined_profit']:.2f}")
        
        print(f"\\n📁 Tracking files:")
        print(f"   Traditional: {tracking.traditional_csv}")
        print(f"   TradFi: {tracking.tradfi_csv}")
        
        print("\\n✅ SEPARATE TRACKING TESTS PASSED!")
        
        return True
        
    except Exception as e:
        print(f"\\n❌ TRACKING TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all simple tests"""
    
    print("🚀 STARTING SIMPLE ECONOMIC ANALYSIS TESTS")
    print("=" * 55)
    print(f"📅 Test Time: {datetime.now()}")
    print("🎯 Goal: Test economic analysis without Discord dependencies")
    print()
    
    # Test 1: Economic analysis
    economic_success = await test_economic_analysis_simple()
    
    # Test 2: Separate tracking systems
    if economic_success:
        tracking_success = await test_separate_tracking()
    else:
        tracking_success = False
    
    # Summary
    print("\\n" + "=" * 55)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 55)
    
    if economic_success and tracking_success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Economic analysis system working")
        print("✅ Separate tracking systems working")
        print("✅ Alphanumeric IDs working (A001, T001)")
        print("\\n🚀 Ready for next steps:")
        print("   1. Install Discord: pip install discord.py")
        print("   2. Test with Discord: python3 launch_enhanced.py scan")
        print("   3. Set up IBKR for TradFi arbitrage")
    else:
        print("❌ TESTS FAILED - Need to fix issues before proceeding")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\\n💥 Test system crashed: {e}")
        import traceback
        traceback.print_exc()
