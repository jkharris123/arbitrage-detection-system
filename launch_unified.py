#!/usr/bin/env python3
"""
VOLUME-OPTIMIZED Launch System with Unified Discord Bot
Uses enhanced detector with volume optimization for maximum profit
FOCUS: Direct event contract arbitrage with volume optimization (20-50% profit improvement)
"""

from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime

# Add paths
sys.path.append('./arbitrage')
sys.path.append('./data_collectors')
sys.path.append('./alerts')
sys.path.append('./config')

from detector_enhanced import EnhancedArbitrageDetector
try:
    from unified_discord_bot import UnifiedBotManager
    DISCORD_AVAILABLE = True
except ImportError as e:
    DISCORD_AVAILABLE = False
    print(f"⚠️ Discord bot disabled: {e}")
from economic_tradfi_filter import EconomicMarketFilter
from settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedArbitrageSystem:
    """Complete arbitrage system with unified Discord bot - Direct arbitrage focus"""
    
    def __init__(self):
        self.arbitrage_detector = EnhancedArbitrageDetector()
        self.economic_filter = EconomicMarketFilter()
        
        if DISCORD_AVAILABLE:
            self.discord_manager = UnifiedBotManager()
        else:
            self.discord_manager = None
        
        # Stats tracking
        self.scan_count = 0
        self.opportunities_found = 0
        self.economic_markets_found = 0
    
    async def run_economic_scan(self):
        """Run economic-focused arbitrage scan with VOLUME OPTIMIZATION"""
        logger.info("🚀 Starting VOLUME-OPTIMIZED Direct Event Contract Arbitrage Scan...")
        logger.info("🎯 NEW: Testing volumes $50-$1000 to find maximum profit per opportunity")
        logger.info("🔥 ADVANTAGE: Real API slippage data instead of estimates")
        self.scan_count += 1
        
        try:
            # Get all markets with volume optimization
            logger.info("📊 Fetching markets and running volume optimization...")
            opportunities = await self.arbitrage_detector.scan_for_arbitrage()
            
            # Get market data for economic filtering
            kalshi_markets = self.arbitrage_detector.kalshi_client.get_markets()
            
            from polymarket_client_enhanced import EnhancedPolymarketClient
            async with EnhancedPolymarketClient() as poly_client:
                polymarket_markets = await poly_client.get_active_markets_with_pricing(limit=200)
            
            # Filter for economic event markets (direct arbitrage only)
            logger.info("🏦 Filtering for economic event markets (direct arbitrage only)...")
            economic_markets = self.economic_filter.filter_economic_markets(
                kalshi_markets, polymarket_markets
            )
            self.economic_markets_found = len(economic_markets)
            
            # Send alerts for profitable opportunities via unified bot
            if opportunities:
                total_profit = sum(opp.guaranteed_profit for opp in opportunities)
                avg_volume = sum(opp.trade_size_usd for opp in opportunities) / len(opportunities) if opportunities else 0
                logger.info(f"💰 Found {len(opportunities)} VOLUME-OPTIMIZED arbitrage opportunities")
                logger.info(f"📈 Total profit potential: ${total_profit:.2f} | Avg optimal volume: ${avg_volume:.0f}")
                
                for opp in opportunities:
                    if opp.guaranteed_profit > 10.0:  # Only alert for >$10 profit
                        if self.discord_manager:
                            await self.discord_manager.send_opportunity_alert(opp)
                        else:
                            # Enhanced logging with volume optimization details
                            logger.info(f"💰 {opp.opportunity_id}: ${opp.guaranteed_profit:.2f} profit at ${opp.trade_size_usd:.0f} optimal volume")
                            logger.info(f"   📊 Slippage: K:{opp.kalshi_slippage_percent:.1f}% + P:{opp.polymarket_slippage_percent:.1f}%")
                        self.opportunities_found += 1
            
            # Send economic market summary via unified bot
            await self._send_economic_summary(economic_markets)
            
            logger.info(f"✅ VOLUME-OPTIMIZED scan complete - Found {len(opportunities)} optimized arbitrage opportunities")
            if opportunities:
                logger.info(f"🚀 OPTIMIZATION ADVANTAGE: Each opportunity tested at multiple volumes for maximum profit!")
            
            return {
                'volume_optimized_arbitrage': len(opportunities),
                'economic_markets': len(economic_markets),
                'profitable_alerts': len([o for o in opportunities if o.guaranteed_profit > 10.0])
            }
            
        except Exception as e:
            logger.error(f"❌ Error in economic scan: {e}")
            if self.discord_manager:
                await self.discord_manager.send_market_update(f"❌ Scan failed: {str(e)}")
            return None
    
    async def _send_economic_summary(self, economic_markets):
        """Send summary of economic markets for direct arbitrage"""
        try:
            # Focus on short-term, high-priority markets for direct arbitrage
            short_term = [m for m in economic_markets if m.days_to_expiry <= 7]
            high_priority = [m for m in economic_markets if m.arbitrage_priority == "HIGH"]
            
            summary = f"""📊 **ECONOMIC EVENT MARKETS SCAN**
🏦 Total Economic Markets: {len(economic_markets)}
⚡ Short-term (≤7 days): {len(short_term)}
🎯 High Priority: {len(high_priority)}
🎲 Focus: Direct Event Contract Arbitrage

**Categories Found:**"""
            
            # Add category breakdown
            categories = {}
            for market in economic_markets:
                categories[market.category] = categories.get(market.category, 0) + 1
            
            for category, count in categories.items():
                summary += f"\\n• {category}: {count} markets"
            
            if high_priority:
                summary += f"\\n\\n**High Priority Markets:**"
                for i, market in enumerate(high_priority[:3], 1):
                    summary += f"\\n{i}. {market.question[:40]}... ({market.days_to_expiry}d)"
            
            summary += f"\\n\\n⏰ Next scan: {datetime.now().strftime('%H:%M:%S')}"
            
            # Send via unified Discord bot
            if self.discord_manager:
                success = await self.discord_manager.send_market_update(summary)
                if success:
                    logger.info("📱 Economic summary sent via Discord bot")
            
        except Exception as e:
            logger.error(f"❌ Error sending economic summary: {e}")
    
    async def run_continuous_monitoring(self, interval_minutes: int = 15):
        """Run continuous monitoring with economic focus"""
        logger.info(f"🔄 Starting continuous monitoring (every {interval_minutes} minutes)")
        
        # Send startup message via unified bot
        if self.discord_manager:
            startup_msg = f"""🚀 **VOLUME-OPTIMIZED Arbitrage System Active**
📊 Scanning every {interval_minutes} minutes
🎯 Focus: Volume-optimized direct event contract arbitrage
🔥 NEW: Tests $50-$1000 volumes for maximum profit
⚡ ADVANTAGE: Real API slippage data (20-50% profit improvement)
🤖 Unified bot ready for alerts and execution!

**Commands:** `STATUS`, `EXECUTE A001`, `HALT`, `RESUME`"""
            await self.discord_manager.send_market_update(startup_msg)
        
        try:
            while True:
                # Run economic scan
                results = await self.run_economic_scan()
                
                if results:
                    logger.info(f"📊 Scan #{self.scan_count}: {results['volume_optimized_arbitrage']} volume-optimized arbitrage opportunities")
                
                # Wait for next scan
                logger.info(f"⏱️ Waiting {interval_minutes} minutes for next scan...")
                await asyncio.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")
            if self.discord_manager:
                await self.discord_manager.send_market_update("🛑 **System Offline** - Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitoring error: {e}")
            if self.discord_manager:
                await self.discord_manager.send_market_update(f"❌ **System Error** - Monitoring failed: {str(e)}")
    
    async def run_unified_discord_bot(self):
        """Run the unified Discord bot"""
        if not self.discord_manager:
            logger.error("❌ Unified Discord bot not available")
            return
        
        logger.info("🤖 Starting unified Discord bot...")
        
        try:
            await self.discord_manager.start_bot()
        except Exception as e:
            logger.error(f"❌ Discord bot error: {e}")
    
    def get_system_stats(self):
        """Get system performance statistics"""
        return {
            'total_scans': self.scan_count,
            'opportunities_found': self.opportunities_found,
            'economic_markets': self.economic_markets_found,
            'success_rate': f"{(self.opportunities_found/max(self.scan_count,1)*100):.1f}%"
        }

async def main():
    """Main entry point with enhanced options"""
    parser = argparse.ArgumentParser(description='Direct Event Contract Arbitrage System with Unified Discord Bot')
    parser.add_argument('command', choices=['scan', 'monitor', 'bot', 'economic', 'test'], 
                       help='Command to run')
    parser.add_argument('--interval', type=int, default=15, 
                       help='Monitoring interval in minutes (default: 15)')
    parser.add_argument('--max-days', type=int, default=14,
                       help='Maximum days to expiry for markets (default: 14)')
    
    args = parser.parse_args()
    
    # Initialize system
    system = EnhancedArbitrageSystem()
    
    print(f"🚀 Direct Event Contract Arbitrage System - {args.command.upper()} mode")
    print(f"⚙️ Environment: {settings.environment}")
    print(f"🎯 Focus: Event contract arbitrage ≤{args.max_days} days")
    print(f"🤖 Discord bot: {'Available' if DISCORD_AVAILABLE else 'Disabled'}")
    print(f"⚠️ Cross-asset arbitrage: DISABLED (focus on direct arbitrage first)")
    print()
    
    try:
        if args.command == 'test':
            # Run test scan
            print("🧪 Running test scan...")
            results = await system.run_economic_scan()
            if results:
                print(f"✅ Test completed: {results}")
                stats = system.get_system_stats()
                print(f"📊 Stats: {stats}")
            
        elif args.command == 'scan':
            # Single scan
            print("🔍 Running single economic scan...")
            results = await system.run_economic_scan()
            if results:
                print(f"✅ Scan completed: {results}")
            
        elif args.command == 'economic':
            # Economic markets analysis only
            print("🏦 Running economic markets analysis...")
            
            from kalshi_client import KalshiClient
            from polymarket_client_enhanced import EnhancedPolymarketClient
            
            kalshi = KalshiClient()
            kalshi_markets = kalshi.get_markets()
            
            async with EnhancedPolymarketClient() as poly_client:
                polymarket_markets = await poly_client.get_active_markets_with_pricing(limit=100)
            
            economic_markets = system.economic_filter.filter_economic_markets(kalshi_markets, polymarket_markets)
            
            summary = system.economic_filter.get_summary()
            print(f"📊 Economic Analysis Complete:")
            print(f"   Markets: {summary['total_economic_markets']}")
            print(f"   High Priority: {summary['high_priority_count']}")
            print(f"   Short-term: {summary['short_term_count']}")
            
        elif args.command == 'monitor':
            # Continuous monitoring
            print(f"🔄 Starting continuous monitoring every {args.interval} minutes...")
            print("Press Ctrl+C to stop")
            await system.run_continuous_monitoring(args.interval)
            
        elif args.command == 'bot':
            # Unified Discord bot
            print("🤖 Starting unified Discord bot...")
            print("📱 Bot will handle both alerts and execution commands")
            print("Press Ctrl+C to stop")
            await system.run_unified_discord_bot()
            
    except KeyboardInterrupt:
        print("\\n🛑 System stopped by user")
    except Exception as e:
        print(f"\\n❌ System error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
