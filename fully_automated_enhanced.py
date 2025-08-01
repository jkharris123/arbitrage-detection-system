#!/usr/bin/env python3
"""
Fully Automated Arbitrage System with Enhanced OpenAI Matching
Complete pipeline: Fetch markets → OpenAI (GPT-4o-mini) individual contract matching → Arbitrage detection → Discord alerts/execution
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import csv

# Add paths
sys.path.append('./src/data_collectors')
sys.path.append('./src/detectors')
sys.path.append('./src/bots')
sys.path.append('./src/matchers')

from openai_enhanced_matcher import EnhancedOpenAIMatchingSystem as EnhancedClaudeMatchingSystem
from claude_matched_detector import ClaudeMatchedArbitrageDetector
from discord_bot import UnifiedBotManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FullyAutomatedArbitrageSystem:
    """Complete automated arbitrage system with enhanced OpenAI matching"""
    
    def __init__(self, mode: str = 'alert'):
        """
        Initialize system
        
        Args:
            mode: 'alert' for Discord alerts only, 'auto' for full automation
        """
        self.mode = mode
        self.matching_system = EnhancedClaudeMatchingSystem()
        self.discord_manager = UnifiedBotManager() if os.getenv('DISCORD_BOT_TOKEN') else None
        
        # Configuration
        self.min_profit = 10.0  # Minimum $10 profit to act on
        self.max_days_to_expiry = 14
        self.min_confidence = 0.8  # Minimum match confidence
        
        # Live testing tracking
        self.live_test_file = f"output/live_test_{mode}_{datetime.now().strftime('%Y%m%d')}.csv"
        self.init_live_test_file()
        
        # Stats
        self.cycles_run = 0
        self.total_opportunities = 0
        self.total_alerts_sent = 0
        self.total_auto_executions = 0
        
    def init_live_test_file(self):
        """Initialize CSV file for live testing results"""
        os.makedirs('output', exist_ok=True)
        
        with open(self.live_test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'opportunity_id', 'kalshi_ticker', 'polymarket_condition_id',
                'guaranteed_profit', 'profit_percentage', 'optimal_volume', 'time_to_expiry_hours',
                'action', 'execution_decision', 'execution_timestamp', 'notes'
            ])
    
    def log_live_test_opportunity(self, opportunity, action: str, decision: str = 'pending'):
        """Log opportunity to live test file"""
        with open(self.live_test_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                opportunity.opportunity_id,
                opportunity.kalshi_ticker,
                opportunity.polymarket_condition_id,
                opportunity.guaranteed_profit,
                opportunity.profit_percentage,
                opportunity.optimal_volume,
                opportunity.time_to_expiry_hours,
                action,
                decision,
                datetime.now().isoformat() if decision != 'pending' else '',
                f"Mode: {self.mode}"
            ])
    
    async def run_automated_cycle(self) -> Dict:
        """Run a complete automated arbitrage cycle"""
        self.cycles_run += 1
        cycle_start = datetime.now()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 Starting Automated Cycle #{self.cycles_run} (Mode: {self.mode.upper()})")
        logger.info(f"{'='*60}")
        
        try:
            # Step 1: Run enhanced OpenAI matching for individual contracts
            logger.info("\n📊 Step 1: Enhanced OpenAI (GPT-4o-mini) Matching")
            logger.info("🎯 Matching individual contracts with specific thresholds...")
            
            match_stats = await self.matching_system.run_enhanced_matching()
            
            logger.info(f"✅ Matching complete: {match_stats['total_matches']} matches found")
            logger.info(f"   High confidence: {match_stats['high_confidence']}")
            logger.info(f"   Exact matches: {match_stats['exact_matches']}")
            logger.info(f"   Threshold matches: {match_stats['threshold_matches']}")
            
            # Step 2: Run arbitrage detection on matched contracts
            logger.info("\n💰 Step 2: Arbitrage Detection")
            logger.info("🔍 Scanning matched contracts for profit opportunities...")
            
            detector = ClaudeMatchedArbitrageDetector('manual_matches.csv')
            opportunities = await detector.scan_matched_contracts(max_orderbook_calls=200)
            
            self.total_opportunities += len(opportunities)
            
            # Filter for profitable opportunities
            profitable_opps = [
                opp for opp in opportunities 
                if opp.guaranteed_profit >= self.min_profit
                and opp.match_confidence >= self.min_confidence
            ]
            
            logger.info(f"✅ Found {len(profitable_opps)} profitable opportunities (>${self.min_profit})")
            
            # Step 3: Process opportunities based on mode
            if profitable_opps:
                logger.info(f"\n🎯 Step 3: Processing Opportunities (Mode: {self.mode.upper()})")
                
                if self.mode == 'alert':
                    await self.process_alert_mode(profitable_opps)
                else:  # auto mode
                    await self.process_auto_mode(profitable_opps)
            else:
                logger.info("\n📊 No profitable opportunities found this cycle")
            
            # Calculate cycle statistics
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            
            stats = {
                'cycle_number': self.cycles_run,
                'cycle_time': cycle_time,
                'matches_found': match_stats['total_matches'],
                'opportunities_found': len(opportunities),
                'profitable_opportunities': len(profitable_opps),
                'total_profit_potential': sum(opp.guaranteed_profit for opp in profitable_opps),
                'mode': self.mode,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send summary to Discord
            if self.discord_manager and self.discord_manager.bot:
                summary = f"""Cycle #{self.cycles_run} Complete
⏱️ Duration: {cycle_time:.1f}s
🔗 Matches: {match_stats['total_matches']}
💰 Opportunities: {len(profitable_opps)}
💵 Profit potential: ${stats['total_profit_potential']:.2f}
📊 Mode: {self.mode.upper()}"""
                
                await self.discord_manager.send_market_update(summary)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error in automated cycle: {e}")
            import traceback
            traceback.print_exc()
            return {
                'cycle_number': self.cycles_run,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def process_alert_mode(self, opportunities: List):
        """Process opportunities in alert mode (Discord alerts, wait for response)"""
        logger.info(f"📱 Sending {len(opportunities)} alerts to Discord...")
        
        for opp in opportunities:
            # Log to live test file
            self.log_live_test_opportunity(opp, 'alert_sent')
            
            # Send Discord alert
            if self.discord_manager and self.discord_manager.bot:
                success = await self.discord_manager.send_opportunity_alert(opp)
                if success:
                    self.total_alerts_sent += 1
                    logger.info(f"✅ Alert sent for {opp.opportunity_id}")
                else:
                    logger.error(f"❌ Failed to send alert for {opp.opportunity_id}")
            
            # Log top opportunities
            logger.info(f"\n💰 {opp.opportunity_id}:")
            logger.info(f"   Kalshi: {opp.kalshi_ticker}")
            logger.info(f"   Polymarket: {opp.polymarket_condition_id[:16]}...")
            logger.info(f"   Profit: ${opp.guaranteed_profit:.2f} ({opp.profit_percentage:.1f}%)")
            logger.info(f"   Volume: {opp.optimal_volume} contracts")
            logger.info(f"   Strategy: Buy {opp.buy_platform} {opp.buy_side}")
    
    async def process_auto_mode(self, opportunities: List):
        """Process opportunities in auto mode (automatic execution)"""
        logger.info(f"🤖 Auto-executing {len(opportunities)} opportunities...")
        
        for opp in opportunities:
            # Log to live test file
            self.log_live_test_opportunity(opp, 'auto_execute', 'executed')
            
            # In live testing, we just log the execution
            self.total_auto_executions += 1
            
            logger.info(f"\n✅ AUTO-EXECUTED {opp.opportunity_id}:")
            logger.info(f"   Kalshi: {opp.kalshi_ticker}")
            logger.info(f"   Polymarket: {opp.polymarket_condition_id[:16]}...")
            logger.info(f"   Profit: ${opp.guaranteed_profit:.2f}")
            logger.info(f"   Volume: {opp.optimal_volume} contracts")
            
            # TODO: Add actual execution logic here when ready
            # For now, just tracking what would be executed
    
    async def run_continuous_monitoring(self, interval_minutes: int = 15):
        """Run continuous monitoring with automated matching"""
        logger.info(f"🚀 Starting Fully Automated Arbitrage System")
        logger.info(f"⏰ Scanning every {interval_minutes} minutes")
        logger.info(f"🎯 Mode: {self.mode.upper()}")
        logger.info(f"💰 Minimum profit threshold: ${self.min_profit}")
        logger.info(f"🤖 Enhanced OpenAI (GPT-4o-mini) matching: ENABLED")
        
        # Check for required API keys
        if not os.getenv('OPENAI_API_KEY'):
            logger.error("❌ OPENAI_API_KEY not found! Please set it in .env")
            logger.error("Get one from: https://platform.openai.com/api-keys")
            return
        
        # Start Discord bot if in alert mode
        if self.mode == 'alert' and self.discord_manager:
            logger.info("🤖 Starting Discord bot...")
            asyncio.create_task(self.discord_manager.start_bot())
            await asyncio.sleep(5)  # Give bot time to connect
        
        while True:
            try:
                # Run cycle
                stats = await self.run_automated_cycle()
                
                # Log summary
                logger.info(f"\n📈 Cycle Summary:")
                logger.info(f"   Duration: {stats.get('cycle_time', 0):.1f}s")
                logger.info(f"   Matches: {stats.get('matches_found', 0)}")
                logger.info(f"   Opportunities: {stats.get('profitable_opportunities', 0)}")
                logger.info(f"   Profit potential: ${stats.get('total_profit_potential', 0):.2f}")
                
                # System stats
                logger.info(f"\n📊 System Statistics:")
                logger.info(f"   Total cycles: {self.cycles_run}")
                logger.info(f"   Total opportunities: {self.total_opportunities}")
                logger.info(f"   Alerts sent: {self.total_alerts_sent}")
                logger.info(f"   Auto executions: {self.total_auto_executions}")
                logger.info(f"   Live test file: {self.live_test_file}")
                
                # Wait for next cycle
                logger.info(f"\n⏱️ Waiting {interval_minutes} minutes for next cycle...")
                await asyncio.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping automated system...")
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                logger.info(f"⏱️ Retrying in {interval_minutes} minutes...")
                await asyncio.sleep(interval_minutes * 60)

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fully Automated Arbitrage System')
    parser.add_argument('command', choices=['test', 'monitor'],
                       help='Command to run')
    parser.add_argument('--mode', choices=['alert', 'auto'], default='alert',
                       help='Execution mode: alert (Discord alerts) or auto (automatic execution)')
    parser.add_argument('--interval', type=int, default=15,
                       help='Monitoring interval in minutes (default: 15)')
    
    args = parser.parse_args()
    
    system = FullyAutomatedArbitrageSystem(mode=args.mode)
    
    if args.command == 'test':
        print(f"🧪 Running single test cycle in {args.mode} mode...")
        stats = await system.run_automated_cycle()
        print(f"\n✅ Test complete!")
        print(f"Results: {stats}")
        
    elif args.command == 'monitor':
        print(f"🔄 Starting continuous monitoring in {args.mode} mode...")
        await system.run_continuous_monitoring(args.interval)

if __name__ == "__main__":
    # Example usage:
    # python fully_automated_enhanced.py test --mode alert    # Test with Discord alerts
    # python fully_automated_enhanced.py test --mode auto     # Test with auto execution
    # python fully_automated_enhanced.py monitor --mode alert # Live with Discord alerts
    # python fully_automated_enhanced.py monitor --mode auto  # Live with auto execution
    
    asyncio.run(main())
