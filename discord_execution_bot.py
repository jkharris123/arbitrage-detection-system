#!/usr/bin/env python3
"""
Discord Message-Based Execution System
Listens for "EXECUTE A001" messages and triggers trades
Enables mobile trading from anywhere via Discord
"""

try:
    import discord
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("⚠️ Discord not installed - message execution disabled")

import asyncio
import os
import sys
import logging
from datetime import datetime
import json

# Add paths
sys.path.append('./arbitrage')
sys.path.append('./data_collectors')
sys.path.append('./alerts')
sys.path.append('./config')

from discord_alerter import DiscordArbitrageAlerter
from detector_enhanced import EnhancedArbitrageDetector
from settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordExecutionBot(discord.Client if DISCORD_AVAILABLE else object):
    """Discord bot that listens for execution commands"""
    
    def __init__(self, arbitrage_detector, webhook_url):
        if not DISCORD_AVAILABLE:
            return
            
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        self.arbitrage_detector = arbitrage_detector
        self.alerter = DiscordArbitrageAlerter(webhook_url)
        self.pending_opportunities = {}  # Store opportunities by ID
        self.channel_id = None  # Will be set from config
        
    async def on_ready(self):
        """Bot is ready"""
        logger.info(f'🤖 Discord Execution Bot logged in as {self.user}')
        logger.info(f'📱 Listening for EXECUTE commands...')
        
        # Send startup notification
        await self.alerter.send_system_status(
            "ONLINE", 
            "🤖 Execution Bot Active - Reply 'EXECUTE ARB_XXX' to trade"
        )
    
    async def on_message(self, message):
        """Handle incoming messages"""
        # Ignore own messages
        if message.author == self.user:
            return
        
        # Only listen in configured channel (if set)
        if self.channel_id and message.channel.id != self.channel_id:
            return
        
        content = message.content.upper().strip()
        
        # Check for execution commands
        if content.startswith('EXECUTE A'):
            await self.handle_execution_command(message, content)
        
        elif content.startswith('STATUS'):
            await self.handle_status_command(message)
        
        elif content.startswith('HALT') or content.startswith('STOP'):
            await self.handle_halt_command(message)
    
    async def handle_execution_command(self, message, content):
        """Handle EXECUTE A001 commands"""
        try:
            # Extract opportunity ID
            parts = content.split()
            if len(parts) < 2:
                await message.reply("❌ Invalid format. Use: EXECUTE A001")
                return
            
            opp_id = parts[1]  # A001
            
            # Check if opportunity exists
            if opp_id not in self.pending_opportunities:
                await message.reply(f"❌ Opportunity {opp_id} not found or expired")
                return
            
            opportunity = self.pending_opportunities[opp_id]
            
            # Send confirmation
            await message.reply(f"🔄 Executing {opp_id}... Checking current prices...")
            
            # Execute the trade
            success, result_msg = await self.execute_arbitrage(opportunity)
            
            if success:
                await message.reply(f"✅ **TRADE EXECUTED!**\\n{result_msg}")
                
                # Remove from pending
                del self.pending_opportunities[opp_id]
                
                # Send detailed results
                await self.alerter.send_execution_result(opp_id, True, result_msg)
            else:
                await message.reply(f"❌ **EXECUTION FAILED**\\n{result_msg}")
                await self.alerter.send_execution_result(opp_id, False, result_msg)
        
        except Exception as e:
            logger.error(f"Error executing {content}: {e}")
            await message.reply(f"❌ Execution error: {str(e)}")
    
    async def handle_status_command(self, message):
        """Handle STATUS commands"""
        try:
            active_opps = len(self.pending_opportunities)
            
            status_msg = f"""📊 **ARBITRAGE BOT STATUS**
🤖 Bot: Online and listening
📱 Pending Opportunities: {active_opps}
⏰ Last Update: {datetime.now().strftime('%H:%M:%S')}
💰 Ready for execution commands

**Commands:**
• `EXECUTE A001` - Execute opportunity
• `STATUS` - Show this status
• `HALT` - Emergency stop"""
            
            await message.reply(status_msg)
            
        except Exception as e:
            await message.reply(f"❌ Status error: {str(e)}")
    
    async def handle_halt_command(self, message):
        """Handle emergency halt commands"""
        try:
            # Clear all pending opportunities
            self.pending_opportunities.clear()
            
            await message.reply("🛑 **EMERGENCY HALT ACTIVATED**\\nAll pending opportunities cleared.")
            await self.alerter.send_system_status("HALTED", "🛑 Emergency halt activated by user")
            
            logger.warning("🛑 Emergency halt activated")
            
        except Exception as e:
            await message.reply(f"❌ Halt error: {str(e)}")
    
    async def execute_arbitrage(self, opportunity):
        """
        Execute the actual arbitrage trade
        Returns (success: bool, message: str)
        """
        try:
            # In DEMO mode, simulate execution
            if settings.environment == "DEMO":
                await asyncio.sleep(2)  # Simulate execution delay
                
                result_msg = f"""**DEMO EXECUTION COMPLETED**
🎯 Strategy: {opportunity.strategy_type}
💰 Simulated Profit: ${opportunity.guaranteed_profit:.2f}
📊 Trade Size: ${opportunity.trade_size_usd:.0f}
⏱️ Execution Time: {datetime.now().strftime('%H:%M:%S')}

**Kalshi Trade:** {opportunity.buy_side} @ ${opportunity.kalshi_execution_price:.3f}
**Polymarket Trade:** {opportunity.sell_side} @ ${opportunity.polymarket_execution_price:.3f}

*Note: Demo mode - no real trades executed*"""
                
                return True, result_msg
            
            else:
                # TODO: Implement real trading logic
                # 1. Verify current prices haven't changed
                # 2. Execute Kalshi trade
                # 3. Execute Polymarket trade
                # 4. Confirm both trades
                # 5. Calculate actual profit
                
                return False, "Live trading not implemented yet"
        
        except Exception as e:
            return False, f"Execution error: {str(e)}"
    
    def store_opportunity(self, opportunity):
        """Store opportunity for potential execution"""
        self.pending_opportunities[opportunity.opportunity_id] = opportunity
        
        # Clean up old opportunities (older than 1 hour)
        cutoff_time = datetime.now().timestamp() - 3600
        expired_ids = [
            opp_id for opp_id, opp in self.pending_opportunities.items()
            if datetime.fromisoformat(opp.timestamp.replace('Z', '+00:00')).timestamp() < cutoff_time
        ]
        
        for opp_id in expired_ids:
            del self.pending_opportunities[opp_id]
        
        logger.info(f"📥 Stored opportunity {opportunity.opportunity_id} for execution")

class DiscordExecutionManager:
    """Manages Discord execution bot and integrates with arbitrage system"""
    
    def __init__(self):
        self.bot = None
        self.arbitrage_detector = EnhancedArbitrageDetector()
        
        # Get Discord configuration
        self.bot_token = os.getenv('DISCORD_BOT_TOKEN')
        self.webhook_url = os.getenv('DISCORD_WEBHOOK')
        self.channel_id = os.getenv('DISCORD_CHANNEL_ID')
        
        if not self.webhook_url:
            raise ValueError("DISCORD_WEBHOOK environment variable required")
    
    async def start_execution_bot(self):
        """Start the Discord execution bot"""
        if not DISCORD_AVAILABLE:
            logger.warning("⚠️ Discord not installed - execution bot disabled")
            return False
            
        if not self.bot_token:
            logger.warning("⚠️ No DISCORD_BOT_TOKEN - execution bot disabled")
            return False
        
        try:
            self.bot = DiscordExecutionBot(self.arbitrage_detector, self.webhook_url)
            
            if self.channel_id:
                self.bot.channel_id = int(self.channel_id)
            
            logger.info("🚀 Starting Discord execution bot...")
            await self.bot.start(self.bot_token)
            
        except Exception as e:
            logger.error(f"❌ Failed to start Discord bot: {e}")
            return False
    
    async def send_opportunity_alert(self, opportunity):
        """Send arbitrage opportunity alert with execution commands"""
        try:
            # Store opportunity for execution
            if self.bot:
                self.bot.store_opportunity(opportunity)
            
            # Send alert with execution button
            alerter = DiscordArbitrageAlerter(self.webhook_url)
            success = await alerter.send_arbitrage_alert(opportunity)
            
            if success:
                logger.info(f"📱 Sent alert for {opportunity.opportunity_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error sending opportunity alert: {e}")
            return False

# Test the execution system
async def test_execution_system():
    """Test the Discord execution system"""
    print("🧪 Testing Discord Execution System...")
    
    try:
        manager = DiscordExecutionManager()
        
        if manager.bot_token:
            print("✅ Bot token configured")
            print("🤖 Starting execution bot (Ctrl+C to stop)...")
            await manager.start_execution_bot()
        else:
            print("⚠️ No bot token - testing alert sending only...")
            
            # Create test opportunity
            from detector_enhanced import PreciseArbitrageOpportunity
            
            test_opp = PreciseArbitrageOpportunity(
                timestamp=datetime.now().isoformat(),
                opportunity_id="ARB_TEST_001",
                kalshi_ticker="INXD-25JUL18-6000",
                kalshi_question="Will SPX close above 6000 on July 18?",
                polymarket_condition_id="test_condition",
                polymarket_question="SPX closing above 6000 July 18",
                match_confidence=0.85,
                strategy_type="YES_ARBITRAGE",
                buy_platform="Kalshi",
                sell_platform="Polymarket",
                buy_side="YES",
                sell_side="NO",
                kalshi_execution_price=0.45,
                kalshi_slippage_percent=1.0,
                polymarket_execution_price=0.60,
                polymarket_slippage_percent=2.0,
                trade_size_usd=100.0,
                kalshi_total_cost=45.0,
                polymarket_total_cost=60.0,
                guaranteed_profit=15.0,
                profit_percentage=15.0,
                profit_per_hour=180.0,
                liquidity_score=80.0,
                execution_certainty=95.0,
                time_to_expiry_hours=48.0,
                is_profitable=True,
                ready_to_execute=True,
                recommendation="EXECUTE_IMMEDIATELY"
            )
            
            success = await manager.send_opportunity_alert(test_opp)
            
            if success:
                print("✅ Test alert sent successfully!")
                print("📱 Check Discord for alert with execution commands")
            else:
                print("❌ Failed to send test alert")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_execution_system())
    except KeyboardInterrupt:
        print("\\n🛑 Discord execution bot stopped")
    except Exception as e:
        print(f"\\n💥 Error: {e}")
