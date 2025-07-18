#!/usr/bin/env python3
"""
Unified Discord Bot for Arbitrage System
Sends alerts AND listens for execution commands
Replaces both webhook and separate bot functionality
"""

try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("⚠️ Discord not installed - bot disabled")

import asyncio
import os
import sys
import logging
import json
from datetime import datetime
from typing import Dict, Optional, List

# Add paths
sys.path.append('./arbitrage')
sys.path.append('./data_collectors')
sys.path.append('./alerts')
sys.path.append('./config')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedArbitrageBot(commands.Bot if DISCORD_AVAILABLE else object):
    """
    Unified Discord bot that both sends alerts and listens for commands
    Replaces webhook + separate bot with single integrated solution
    """
    
    def __init__(self):
        if not DISCORD_AVAILABLE:
            return
        
        # Set up bot with message intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',  # For slash commands if needed
            intents=intents,
            description='Arbitrage Trading Bot'
        )
        
        # Configuration
        self.target_channel_id = None
        self.arbitrage_detector = None
        self.pending_opportunities = {}  # Store opportunities by ID
        self.alert_count = 0
        self.execution_enabled = True
        
        # Import here to avoid circular imports
        try:
            from detector_enhanced import EnhancedArbitrageDetector
            self.arbitrage_detector = EnhancedArbitrageDetector()
        except Exception as e:
            logger.warning(f"Could not initialize arbitrage detector: {e}")
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("🤖 Unified Arbitrage Bot starting up...")
        
        # Get target channel ID from environment
        channel_id = os.getenv('DISCORD_CHANNEL_ID')
        if channel_id:
            self.target_channel_id = int(channel_id)
            logger.info(f"📱 Target channel ID: {self.target_channel_id}")
    
    async def on_ready(self):
        """Called when bot is fully logged in and ready"""
        logger.info(f'🚀 Unified Arbitrage Bot logged in as {self.user}')
        logger.info(f'📊 Connected to {len(self.guilds)} servers')
        
        # Send startup message to target channel
        if self.target_channel_id:
            channel = self.get_channel(self.target_channel_id)
            if channel:
                embed = discord.Embed(
                    title="🤖 Arbitrage Bot Online",
                    description="Unified bot ready for alerts and execution!",
                    color=0x00FF00,
                    timestamp=datetime.now()
                )
                embed.add_field(
                    name="Features",
                    value="✅ Send arbitrage alerts\n✅ Listen for execution commands\n✅ Emergency controls",
                    inline=False
                )
                embed.add_field(
                    name="Commands",
                    value="`EXECUTE A001` - Execute opportunity\n`STATUS` - Show bot status\n`HALT` - Emergency stop",
                    inline=False
                )
                
                try:
                    await channel.send(embed=embed)
                    logger.info("📱 Startup message sent")
                except Exception as e:
                    logger.error(f"Failed to send startup message: {e}")
    
    async def on_message(self, message):
        """Handle incoming messages"""
        # Don't respond to own messages
        if message.author == self.user:
            return
        
        # Only listen in target channel (if specified)
        if self.target_channel_id and message.channel.id != self.target_channel_id:
            return
        
        content = message.content.upper().strip()
        
        # Handle execution commands
        if content.startswith('EXECUTE A'):
            await self.handle_execution_command(message, content)
        
        elif content == 'STATUS':
            await self.handle_status_command(message)
        
        elif content in ['HALT', 'STOP', 'EMERGENCY']:
            await self.handle_halt_command(message)
        
        elif content in ['RESUME', 'START']:
            await self.handle_resume_command(message)
        
        # Also process commands (for slash commands if we add them)
        await self.process_commands(message)
    
    async def handle_execution_command(self, message, content):
        """Handle EXECUTE A001 commands"""
        try:
            parts = content.split()
            if len(parts) < 2:
                await message.reply("❌ Invalid format. Use: `EXECUTE A001`")
                return
            
            opp_id = parts[1]  # A001
            
            if not self.execution_enabled:
                await message.reply("🛑 Execution disabled. Use `RESUME` to re-enable.")
                return
            
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
                # Send success message
                embed = discord.Embed(
                    title="✅ Trade Executed Successfully!",
                    description=result_msg,
                    color=0x00FF00,
                    timestamp=datetime.now()
                )
                await message.reply(embed=embed)
                
                # Remove from pending
                del self.pending_opportunities[opp_id]
                
            else:
                # Send failure message
                embed = discord.Embed(
                    title="❌ Trade Execution Failed",
                    description=result_msg,
                    color=0xFF0000,
                    timestamp=datetime.now()
                )
                await message.reply(embed=embed)
        
        except Exception as e:
            logger.error(f"Error executing {content}: {e}")
            await message.reply(f"❌ Execution error: {str(e)}")
    
    async def handle_status_command(self, message):
        """Handle STATUS command"""
        try:
            active_opps = len(self.pending_opportunities)
            
            embed = discord.Embed(
                title="📊 Arbitrage Bot Status",
                color=0x0099FF,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🤖 Bot Status",
                value="🟢 Online and listening" if self.execution_enabled else "🔴 Execution disabled",
                inline=True
            )
            
            embed.add_field(
                name="📱 Pending Opportunities",
                value=str(active_opps),
                inline=True
            )
            
            embed.add_field(
                name="📊 Total Alerts Sent",
                value=str(self.alert_count),
                inline=True
            )
            
            if active_opps > 0:
                opp_list = "\n".join([f"• {opp_id}" for opp_id in list(self.pending_opportunities.keys())[:5]])
                if active_opps > 5:
                    opp_list += f"\n... and {active_opps - 5} more"
                embed.add_field(
                    name="🎯 Active Opportunities",
                    value=opp_list,
                    inline=False
                )
            
            embed.add_field(
                name="💡 Commands",
                value="`EXECUTE A001` - Execute opportunity\n`STATUS` - Show this status\n`HALT` - Emergency stop\n`RESUME` - Resume trading",
                inline=False
            )
            
            await message.reply(embed=embed)
            
        except Exception as e:
            await message.reply(f"❌ Status error: {str(e)}")
    
    async def handle_halt_command(self, message):
        """Handle emergency halt"""
        try:
            self.execution_enabled = False
            self.pending_opportunities.clear()
            
            embed = discord.Embed(
                title="🛑 Emergency Halt Activated",
                description="All pending opportunities cleared.\nExecution disabled until resumed.",
                color=0xFF0000,
                timestamp=datetime.now()
            )
            
            await message.reply(embed=embed)
            logger.warning("🛑 Emergency halt activated")
            
        except Exception as e:
            await message.reply(f"❌ Halt error: {str(e)}")
    
    async def handle_resume_command(self, message):
        """Handle resume trading"""
        try:
            self.execution_enabled = True
            
            embed = discord.Embed(
                title="✅ Trading Resumed",
                description="Bot is now active and ready for execution commands.",
                color=0x00FF00,
                timestamp=datetime.now()
            )
            
            await message.reply(embed=embed)
            logger.info("✅ Trading resumed")
            
        except Exception as e:
            await message.reply(f"❌ Resume error: {str(e)}")
    
    async def execute_arbitrage(self, opportunity):
        """Execute arbitrage trade"""
        try:
            from settings import settings
            
            if settings.environment == "DEMO":
                # Simulate execution
                await asyncio.sleep(2)
                
                result_msg = f"""**DEMO EXECUTION COMPLETED**
🎯 Strategy: {opportunity.strategy_type}
💰 Simulated Profit: ${opportunity.guaranteed_profit:.2f}
📊 Trade Size: ${opportunity.trade_size_usd:.0f}
⏱️ Execution Time: {datetime.now().strftime('%H:%M:%S')}

**Trades:**
• {opportunity.buy_platform} {opportunity.buy_side} @ ${opportunity.kalshi_execution_price:.3f}
• {opportunity.sell_platform} {opportunity.sell_side} @ ${opportunity.polymarket_execution_price:.3f}

*Demo mode - no real trades executed*"""
                
                return True, result_msg
            else:
                # Real execution would go here
                return False, "Live trading not implemented yet"
        
        except Exception as e:
            return False, f"Execution error: {str(e)}"
    
    async def send_arbitrage_alert(self, opportunity):
        """Send arbitrage opportunity alert"""
        if not self.target_channel_id:
            logger.warning("No target channel configured")
            return False
        
        channel = self.get_channel(self.target_channel_id)
        if not channel:
            logger.error(f"Could not find channel {self.target_channel_id}")
            return False
        
        try:
            self.alert_count += 1
            
            # Store opportunity for execution
            self.pending_opportunities[opportunity.opportunity_id] = opportunity
            
            # Clean up old opportunities (older than 1 hour)
            cutoff_time = datetime.now().timestamp() - 3600
            expired_ids = []
            for opp_id, opp in self.pending_opportunities.items():
                try:
                    opp_timestamp = datetime.fromisoformat(opp.timestamp.replace('Z', '+00:00')).timestamp()
                    if opp_timestamp < cutoff_time:
                        expired_ids.append(opp_id)
                except:
                    pass
            
            for opp_id in expired_ids:
                del self.pending_opportunities[opp_id]
            
            # Create alert embed
            embed = await self.create_arbitrage_embed(opportunity)
            
            # Send alert
            await channel.send(
                content=f"🚨 **ARBITRAGE OPPORTUNITY** 🚨\n💰 ${opportunity.guaranteed_profit:.2f} profit available!\n📱 Type `EXECUTE {opportunity.opportunity_id}` to trade",
                embed=embed
            )
            
            logger.info(f"📱 Alert sent for {opportunity.opportunity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
    async def create_arbitrage_embed(self, opportunity):
        """Create rich embed for arbitrage opportunity"""
        
        # Color coding based on profit level
        if opportunity.guaranteed_profit > 50:
            color = 0x00FF00  # Green for high profit
        elif opportunity.guaranteed_profit > 20:
            color = 0xFFFF00  # Yellow for medium profit
        else:
            color = 0xFF9900  # Orange for low profit
        
        # Urgency assessment
        if opportunity.profit_per_hour > 1000:
            urgency = "🔥 URGENT"
        elif opportunity.profit_per_hour > 500:
            urgency = "⚡ HIGH"
        else:
            urgency = "📈 NORMAL"
        
        embed = discord.Embed(
            title=f"{urgency} - {opportunity.opportunity_id}",
            description=f"**{opportunity.kalshi_ticker}** ↔ **{opportunity.polymarket_condition_id[:8]}...**",
            color=color,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="💰 Guaranteed Profit",
            value=f"**${opportunity.guaranteed_profit:.2f}** ({opportunity.profit_percentage:.1f}%)",
            inline=True
        )
        
        embed.add_field(
            name="⏱️ Hourly Rate",
            value=f"${opportunity.profit_per_hour:.0f}/hour",
            inline=True
        )
        
        embed.add_field(
            name="💵 Trade Size",
            value=f"${opportunity.trade_size_usd:.0f}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Strategy",
            value=f"Buy **{opportunity.buy_platform}** {opportunity.buy_side} @ ${opportunity.kalshi_execution_price:.3f}\nSell **{opportunity.sell_platform}** {opportunity.sell_side} @ ${opportunity.polymarket_execution_price:.3f}",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Risk Analysis",
            value=f"Liquidity: {opportunity.liquidity_score:.0f}/100\nCertainty: {opportunity.execution_certainty:.0f}%\nTime Left: {opportunity.time_to_expiry_hours:.1f}h",
            inline=True
        )
        
        embed.add_field(
            name="📋 Slippage",
            value=f"Kalshi: {opportunity.kalshi_slippage_percent:.1f}%\nPolymarket: {opportunity.polymarket_slippage_percent:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="🚀 Quick Execute",
            value=f"**Type:** `EXECUTE {opportunity.opportunity_id}`",
            inline=False
        )
        
        embed.set_footer(text=f"Confidence: {opportunity.match_confidence:.1%} | {opportunity.recommendation}")
        
        return embed
    
    async def send_market_update(self, summary_text: str):
        """Send market update summary"""
        if not self.target_channel_id:
            return False
        
        channel = self.get_channel(self.target_channel_id)
        if not channel:
            return False
        
        try:
            embed = discord.Embed(
                title="📊 Market Update",
                description=summary_text,
                color=0x0099FF,
                timestamp=datetime.now()
            )
            
            embed.set_footer(text=f"Scan completed at {datetime.now().strftime('%H:%M:%S')}")
            
            await channel.send(embed=embed)
            return True
            
        except Exception as e:
            logger.error(f"Error sending market update: {e}")
            return False

class UnifiedBotManager:
    """Manager for the unified Discord bot"""
    
    def __init__(self):
        self.bot = None
        self.bot_token = os.getenv('DISCORD_BOT_TOKEN')
        
        if not self.bot_token:
            logger.warning("⚠️ No DISCORD_BOT_TOKEN - bot disabled")
            return
        
        if DISCORD_AVAILABLE:
            self.bot = UnifiedArbitrageBot()
        else:
            logger.warning("⚠️ Discord not available - bot disabled")
    
    async def start_bot(self):
        """Start the unified bot"""
        if not self.bot or not self.bot_token:
            logger.error("❌ Bot not available - check token and Discord installation")
            return False
        
        try:
            logger.info("🚀 Starting unified Discord bot...")
            await self.bot.start(self.bot_token)
        except Exception as e:
            logger.error(f"❌ Bot failed to start: {e}")
            return False
    
    async def send_opportunity_alert(self, opportunity):
        """Send arbitrage opportunity alert"""
        if self.bot:
            return await self.bot.send_arbitrage_alert(opportunity)
        return False
    
    async def send_market_update(self, summary_text: str):
        """Send market update"""
        if self.bot:
            return await self.bot.send_market_update(summary_text)
        return False

# Test the unified bot
async def test_unified_bot():
    """Test the unified Discord bot"""
    print("🤖 Testing Unified Discord Bot...")
    
    if not DISCORD_AVAILABLE:
        print("❌ Discord not installed")
        return False
    
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        print("❌ No bot token configured")
        return False
    
    print("✅ Bot configuration ready")
    print("🚀 Starting bot (Ctrl+C to stop)...")
    print("📱 Bot will send startup message to your Discord channel")
    print("💡 Try typing 'STATUS' in Discord to test")
    
    try:
        manager = UnifiedBotManager()
        await manager.start_bot()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(test_unified_bot())
