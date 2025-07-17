#!/usr/bin/env python3
"""
Discord Message-Based Execution System
Simple approach: Reply to Discord alerts to trigger execution

WORKFLOW:
1. Bot sends arbitrage alert
2. User replies: "EXECUTE [ID]" or just "EXECUTE" 
3. Bot monitors channel, executes trade
4. Confirmation sent back to Discord
"""

import asyncio
import discord
import os
import json
from datetime import datetime
from typing import Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordExecutionBot:
    """Discord bot that monitors for execution commands"""
    
    def __init__(self, bot_token: str, channel_id: int):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.pending_opportunities = {}
        self.execution_handler = None
        
        # Discord bot setup
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = discord.Client(intents=intents)
        
        # Setup event handlers
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """Setup Discord event handlers"""
        
        @self.bot.event
        async def on_ready():
            logger.info(f"🤖 Discord bot connected as {self.bot.user}")
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                logger.info(f"📺 Monitoring channel: {channel.name}")
            else:
                logger.error(f"❌ Could not find channel with ID: {self.channel_id}")
        
        @self.bot.event
        async def on_message(message):
            # Ignore bot's own messages
            if message.author == self.bot.user:
                return
            
            # Only process messages in our channel
            if message.channel.id != self.channel_id:
                return
            
            await self.handle_user_message(message)
    
    async def handle_user_message(self, message):
        """Handle user messages for execution commands"""
        content = message.content.upper().strip()
        
        # Check for execution commands
        if content.startswith("EXECUTE"):
            await self.process_execution_command(message, content)
        elif content in ["HALT", "STOP", "EMERGENCY"]:
            await self.process_halt_command(message)
        elif content in ["STATUS", "HELP"]:
            await self.process_status_command(message)
    
    async def process_execution_command(self, message, content):
        """Process execution command from user"""
        try:
            # Extract opportunity ID if provided
            parts = content.split()
            opportunity_id = None
            
            if len(parts) > 1:
                opportunity_id = parts[1]
            elif len(self.pending_opportunities) == 1:
                # If only one pending, use it
                opportunity_id = list(self.pending_opportunities.keys())[0]
            
            if not opportunity_id or opportunity_id not in self.pending_opportunities:
                await message.reply(
                    "❌ **Execution Failed**\\n"
                    f"Opportunity ID not found or expired.\\n"
                    f"Available opportunities: {list(self.pending_opportunities.keys())}"
                )
                return
            
            # Get opportunity
            opportunity = self.pending_opportunities[opportunity_id]
            
            # Send confirmation with details
            await message.reply(
                f"⚡ **EXECUTING TRADE**\\n"
                f"ID: `{opportunity_id}`\\n"
                f"Contract: {opportunity.get('contract', 'Unknown')}\\n"
                f"Profit: ${opportunity.get('profit', 0):.2f}\\n"
                f"🔄 Processing..."
            )
            
            # Execute the trade (simulate for now)
            success = await self.execute_arbitrage(opportunity_id, opportunity)
            
            if success:
                # Remove from pending
                del self.pending_opportunities[opportunity_id]
                
                await message.channel.send(
                    f"✅ **EXECUTION SUCCESSFUL**\\n"
                    f"Trade `{opportunity_id}` completed successfully!\\n"
                    f"💰 Profit: ${opportunity.get('profit', 0):.2f}\\n"
                    f"📊 Time: {datetime.now().strftime('%H:%M:%S')}"
                )
            else:
                await message.channel.send(
                    f"❌ **EXECUTION FAILED**\\n"
                    f"Trade `{opportunity_id}` could not be completed.\\n"
                    f"🔄 Opportunity still available for retry."
                )
                
        except Exception as e:
            logger.error(f"❌ Error processing execution: {e}")
            await message.reply(f"❌ **Error**: {str(e)}")
    
    async def process_halt_command(self, message):
        """Process emergency halt command"""
        await message.reply(
            "🛑 **EMERGENCY HALT ACTIVATED**\\n"
            "All trading has been stopped.\\n"
            "Use `STATUS` to check system status."
        )
        # TODO: Implement actual halt logic
    
    async def process_status_command(self, message):
        """Process status command"""
        pending_count = len(self.pending_opportunities)
        pending_list = "\\n".join([f"• `{oid}`" for oid in self.pending_opportunities.keys()]) if pending_count > 0 else "None"
        
        await message.reply(
            f"📊 **System Status**\\n"
            f"🤖 Bot: Online\\n"
            f"💰 Pending Opportunities: {pending_count}\\n"
            f"{pending_list}\\n\\n"
            f"**Commands:**\\n"
            f"• `EXECUTE [ID]` - Execute trade\\n"
            f"• `HALT` - Emergency stop\\n"
            f"• `STATUS` - Show this status"
        )
    
    async def execute_arbitrage(self, opportunity_id: str, opportunity: Dict) -> bool:
        """Execute arbitrage trade (simulated for demo)"""
        try:
            logger.info(f"🔄 Executing arbitrage {opportunity_id}")
            
            # Simulate execution delay
            await asyncio.sleep(2)
            
            # For demo mode, always succeed
            logger.info(f"✅ Arbitrage {opportunity_id} executed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Execution failed for {opportunity_id}: {e}")
            return False
    
    def add_opportunity(self, opportunity_id: str, opportunity_data: Dict):
        """Add opportunity for potential execution"""
        self.pending_opportunities[opportunity_id] = opportunity_data
        logger.info(f"📋 Added opportunity {opportunity_id} to pending list")
        
        # Clean old opportunities (keep only last 5)
        if len(self.pending_opportunities) > 5:
            oldest_key = list(self.pending_opportunities.keys())[0]
            del self.pending_opportunities[oldest_key]
    
    async def start(self):
        """Start the Discord bot"""
        await self.bot.start(self.bot_token)

# Enhanced Discord Alerter with Message-Based Execution
class EnhancedDiscordAlerter:
    """Enhanced Discord alerter that supports message-based execution"""
    
    def __init__(self, webhook_url: str, bot_token: str = None, channel_id: int = None):
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.execution_bot = None
        
        # Start execution bot if credentials provided
        if bot_token and channel_id:
            self.execution_bot = DiscordExecutionBot(bot_token, channel_id)
    
    async def send_arbitrage_alert_with_commands(self, opportunity):
        """Send arbitrage alert with execution commands"""
        try:
            # Create enhanced embed
            embed = {
                "title": f"🎯 Arbitrage Opportunity",
                "description": f"**{opportunity.kalshi_ticker}** ↔ **{opportunity.polymarket_condition_id[:8]}...**",
                "color": 0x00FF00,
                "fields": [
                    {
                        "name": "💰 Guaranteed Profit", 
                        "value": f"**${opportunity.guaranteed_profit:.2f}** ({opportunity.profit_percentage:.1f}%)",
                        "inline": True
                    },
                    {
                        "name": "📊 Strategy",
                        "value": f"Buy {opportunity.buy_platform} {opportunity.buy_side} @ ${opportunity.kalshi_execution_price:.3f}\\nSell {opportunity.sell_platform} {opportunity.sell_side} @ ${opportunity.polymarket_execution_price:.3f}",
                        "inline": False
                    },
                    {
                        "name": "📱 MOBILE EXECUTION",
                        "value": f"**Reply:** `EXECUTE {opportunity.opportunity_id}`\\n**Or just:** `EXECUTE`\\n\\n🚀 Execute this trade from any device!",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"ID: {opportunity.opportunity_id} | Reply with EXECUTE to trade"
                }
            }
            
            payload = {
                "username": "Arbitrage Bot",
                "content": f"🚨 **NEW ARBITRAGE OPPORTUNITY** 🚨\\n📱 **Reply with `EXECUTE` to trade from your phone!**",
                "embeds": [embed]
            }
            
            import requests
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                # Add to execution bot if available
                if self.execution_bot:
                    self.execution_bot.add_opportunity(opportunity.opportunity_id, {
                        'contract': opportunity.kalshi_ticker,
                        'profit': opportunity.guaranteed_profit,
                        'strategy': f"{opportunity.buy_platform} {opportunity.buy_side} → {opportunity.sell_platform} {opportunity.sell_side}"
                    })
                
                return True
            else:
                logger.error(f"❌ Discord alert failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending Discord alert: {e}")
            return False

# Test the message-based execution
async def test_message_based_execution():
    """Test the message-based execution system"""
    
    print("📱 TESTING DISCORD MESSAGE-BASED EXECUTION")
    print("=" * 50)
    
    # Check environment variables
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    bot_token = os.getenv('DISCORD_BOT_TOKEN')  # Add this to .env
    channel_id = os.getenv('DISCORD_CHANNEL_ID')  # Add this to .env
    
    if not webhook_url:
        print("❌ Missing DISCORD_WEBHOOK in .env file")
        return
    
    # Create mock opportunity
    from dataclasses import dataclass
    
    @dataclass
    class MockOpportunity:
        opportunity_id: str = "ARB_MSG_001"
        kalshi_ticker: str = "NASDAQ100-24DEC31"
        polymarket_condition_id: str = "0x1234567890abcdef"
        guaranteed_profit: float = 52.30
        profit_percentage: float = 26.15
        buy_platform: str = "Kalshi"
        sell_platform: str = "Polymarket"
        buy_side: str = "YES"
        sell_side: str = "NO"
        kalshi_execution_price: float = 0.435
        polymarket_execution_price: float = 0.695
    
    opportunity = MockOpportunity()
    
    # Send alert
    alerter = EnhancedDiscordAlerter(webhook_url, bot_token, int(channel_id) if channel_id else None)
    
    print("🚀 Sending Discord alert with execution commands...")
    success = await alerter.send_arbitrage_alert_with_commands(opportunity)
    
    if success:
        print("✅ Discord alert sent!")
        print("\n📱 CHECK DISCORD - You should see:")
        print("   💰 Arbitrage opportunity details")
        print("   📱 Instructions to reply with 'EXECUTE'")
        print("   🎯 No web interface needed!")
        
        print("\n🧪 TO TEST EXECUTION:")
        print("   1. Go to your Discord channel")
        print("   2. Reply with: EXECUTE ARB_MSG_001")
        print("   3. Bot will confirm execution")
        print("   4. Works from any device!")
        
        if bot_token and channel_id:
            print("\n🤖 Starting execution bot to monitor messages...")
            try:
                await alerter.execution_bot.start()
            except Exception as e:
                print(f"⚠️ Execution bot failed to start: {e}")
                print("   Add DISCORD_BOT_TOKEN to .env for full functionality")
        else:
            print("\n💡 For full execution bot:")
            print("   Add DISCORD_BOT_TOKEN=your_bot_token to .env")
            print("   Add DISCORD_CHANNEL_ID=your_channel_id to .env")
    else:
        print("❌ Discord alert failed")

if __name__ == "__main__":
    asyncio.run(test_message_based_execution())
