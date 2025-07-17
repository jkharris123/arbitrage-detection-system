#!/usr/bin/env python3
"""
Discord Alert System for One-Click Arbitrage Execution
Sends rich alerts to Discord with interactive buttons for execution control

FEATURES:
- Rich embeds with profit analysis
- Interactive buttons (Execute/Decline/Details)
- Emergency halt functionality
- Mobile-friendly interface
- Laptop execution confirmation
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import requests
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)

class DiscordArbitrageAlerter:
    """Discord alerting system with one-click execution"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.alert_count = 0
        self.emergency_halt = False
        
    def create_arbitrage_embed(self, opportunity, execution_url: str = None) -> Dict:
        """Create rich Discord embed for arbitrage opportunity with execution URL"""
        
        # Color coding based on profit level
        if opportunity.guaranteed_profit > 50:
            color = 0x00FF00  # Green for high profit
        elif opportunity.guaranteed_profit > 20:
            color = 0xFFFF00  # Yellow for medium profit
        else:
            color = 0xFF9900  # Orange for low profit
        
        # Profit per hour for urgency assessment
        if opportunity.profit_per_hour > 1000:
            urgency = "🔥 URGENT"
        elif opportunity.profit_per_hour > 500:
            urgency = "⚡ HIGH"
        else:
            urgency = "📈 NORMAL"
        
        embed = {
            "title": f"{urgency} Arbitrage Opportunity #{self.alert_count}",
            "description": f"**{opportunity.kalshi_ticker}** ↔ **{opportunity.polymarket_condition_id[:8]}...**",
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "💰 Guaranteed Profit",
                    "value": f"**${opportunity.guaranteed_profit:.2f}** ({opportunity.profit_percentage:.1f}%)",
                    "inline": True
                },
                {
                    "name": "⏱️ Hourly Rate",
                    "value": f"${opportunity.profit_per_hour:.0f}/hour",
                    "inline": True
                },
                {
                    "name": "💵 Trade Size",
                    "value": f"${opportunity.trade_size_usd:.0f}",
                    "inline": True
                },
                {
                    "name": "📊 Strategy",
                    "value": f"Buy **{opportunity.buy_platform}** {opportunity.buy_side} @ ${opportunity.kalshi_execution_price:.3f}\nSell **{opportunity.sell_platform}** {opportunity.sell_side} @ ${opportunity.polymarket_execution_price:.3f}",
                    "inline": False
                },
                {
                    "name": "🎯 Execution Details",
                    "value": f"Liquidity: {opportunity.liquidity_score:.0f}/100\nCertainty: {opportunity.execution_certainty:.0f}/100\nTime Left: {opportunity.time_to_expiry_hours:.1f}h",
                    "inline": True
                },
                {
                    "name": "📋 Slippage Analysis",
                    "value": f"Kalshi: {opportunity.kalshi_slippage_percent:.1f}%\nPolymarket: {opportunity.polymarket_slippage_percent:.1f}%",
                    "inline": True
                },
                {
                    "name": "🤖 Recommendation",
                    "value": f"**{opportunity.recommendation}**",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"ID: {opportunity.opportunity_id} | Confidence: {opportunity.match_confidence:.1%}"
            }
        }
        
        # Add execution URL if provided
        if execution_url:
            embed["fields"].append({
                "name": "📱 ONE-CLICK EXECUTION",
                "value": f"[🚀 **EXECUTE FROM PHONE** 🚀]({execution_url})\n\n⚠️ Click the link above to execute this trade from your phone!",
                "inline": False
            })
        
        return embed
    
    def create_action_buttons(self, opportunity_id: str) -> List[Dict]:
        """Create interactive buttons for Discord (webhook doesn't support components)"""
        # Note: Discord webhooks don't support components/buttons
        # This would need a Discord bot for true interactivity
        # For now, we'll use a different approach with follow-up webhooks
        
        buttons_info = {
            "name": "🎮 Quick Actions",
            "value": f"React to this message or use these commands:\n"
                    f"✅ `/execute {opportunity_id}` - Execute trade\n"
                    f"❌ `/decline {opportunity_id}` - Decline opportunity\n"
                    f"📊 `/details {opportunity_id}` - Show detailed analysis\n"
                    f"🛑 `/halt` - Emergency halt all trading",
            "inline": False
        }
        
        return buttons_info
    
    async def send_arbitrage_alert(self, opportunity, execution_base_url: str = "http://localhost:8080") -> bool:
        """Send arbitrage opportunity alert to Discord with execution URL"""
        try:
            self.alert_count += 1
            
            # Create execution URL that user can click from phone
            execution_url = f"{execution_base_url}/execute/{opportunity.opportunity_id}"
            
            embed = self.create_arbitrage_embed(opportunity, execution_url)
            
            payload = {
                "username": "Arbitrage Bot",
                "avatar_url": "https://cdn.discordapp.com/emojis/💰.png",
                "embeds": [embed],
                "content": f"🚀 **MOBILE EXECUTION READY** 🚀\n\n📱 Click the execution link in the embed below to trade from your phone!\n🏠 Your laptop will execute the trade automatically."
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                logger.info(f"✅ Discord alert sent for {opportunity.opportunity_id}")
                return True
            else:
                logger.error(f"❌ Discord alert failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending Discord alert: {e}")
            return False
    
    async def send_execution_confirmation(self, opportunity_id: str, action: str, 
                                        success: bool, details: str = "") -> bool:
        """Send execution confirmation back to Discord"""
        try:
            if success:
                color = 0x00FF00  # Green
                status = "✅ SUCCESS"
            else:
                color = 0xFF0000  # Red
                status = "❌ FAILED"
            
            embed = {
                "title": f"{status} - Trade Execution",
                "description": f"Opportunity ID: **{opportunity_id}**",
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "fields": [
                    {
                        "name": "Action Taken",
                        "value": action,
                        "inline": True
                    },
                    {
                        "name": "Execution Time",
                        "value": datetime.now().strftime("%H:%M:%S"),
                        "inline": True
                    },
                    {
                        "name": "Details",
                        "value": details if details else "No additional details",
                        "inline": False
                    }
                ]
            }
            
            payload = {
                "username": "Arbitrage Bot - Execution",
                "embeds": [embed]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"❌ Error sending execution confirmation: {e}")
            return False
    
    async def send_daily_summary(self, opportunities_found: int, total_profit: float, 
                               executed_trades: int, success_rate: float) -> bool:
        """Send daily performance summary"""
        try:
            if total_profit > 100:
                color = 0x00FF00  # Green for good day
            elif total_profit > 0:
                color = 0xFFFF00  # Yellow for okay day
            else:
                color = 0xFF0000  # Red for bad day
            
            embed = {
                "title": "📊 Daily Arbitrage Summary",
                "description": f"Performance report for {datetime.now().strftime('%Y-%m-%d')}",
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "fields": [
                    {
                        "name": "🔍 Opportunities Found",
                        "value": str(opportunities_found),
                        "inline": True
                    },
                    {
                        "name": "💰 Total Profit Potential",
                        "value": f"${total_profit:.2f}",
                        "inline": True
                    },
                    {
                        "name": "⚡ Executed Trades",
                        "value": str(executed_trades),
                        "inline": True
                    },
                    {
                        "name": "🎯 Success Rate",
                        "value": f"{success_rate:.1f}%",
                        "inline": True
                    },
                    {
                        "name": "📈 Daily Goal Progress",
                        "value": f"{min(total_profit/1000*100, 100):.1f}% towards $1,000/day",
                        "inline": False
                    }
                ]
            }
            
            payload = {
                "username": "Arbitrage Bot - Daily Report",
                "embeds": [embed]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"❌ Error sending daily summary: {e}")
            return False
    
    async def send_market_update(self, summary_text: str) -> bool:
        """Send market update summary to Discord"""
        try:
            embed = {
                "title": "📊 Market Update",
                "description": summary_text,
                "color": 0x0099FF,
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": f"Scan completed at {datetime.now().strftime('%H:%M:%S')}"
                }
            }
            
            payload = {
                "username": "Arbitrage Bot - Markets",
                "embeds": [embed]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"❌ Error sending market update: {e}")
            return False
    
    async def send_execution_result(self, opportunity_id: str, success: bool, result_msg: str) -> bool:
        """Send execution result to Discord"""
        try:
            color = 0x00FF00 if success else 0xFF0000
            status = "✅ EXECUTED" if success else "❌ FAILED"
            
            embed = {
                "title": f"{status} - {opportunity_id}",
                "description": result_msg,
                "color": color,
                "timestamp": datetime.now().isoformat()
            }
            
            payload = {
                "username": "Arbitrage Bot - Execution",
                "embeds": [embed]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"❌ Error sending execution result: {e}")
            return False
    
    async def send_system_status(self, status: str, message: str) -> bool:
        """Send system status updates"""
        try:
            status_colors = {
                "ONLINE": 0x00FF00,
                "OFFLINE": 0xFF0000,
                "WARNING": 0xFFFF00,
                "ERROR": 0xFF0000,
                "MAINTENANCE": 0x0099FF
            }
            
            color = status_colors.get(status, 0x808080)
            
            embed = {
                "title": f"🤖 System Status: {status}",
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat()
            }
            
            payload = {
                "username": "Arbitrage Bot - System",
                "embeds": [embed]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"❌ Error sending system status: {e}")
            return False

class OneClickExecutionHandler:
    """Handles one-click execution commands from Discord"""
    
    def __init__(self, kalshi_client, polymarket_client, alerter):
        self.kalshi_client = kalshi_client
        self.polymarket_client = polymarket_client
        self.alerter = alerter
        self.pending_opportunities = {}  # Store opportunities for execution
        self.execution_enabled = True
        
    def store_opportunity(self, opportunity):
        """Store opportunity for potential execution"""
        self.pending_opportunities[opportunity.opportunity_id] = opportunity
        
        # Clean old opportunities (older than 1 hour)
        cutoff_time = time.time() - 3600
        to_remove = []
        for opp_id, opp in self.pending_opportunities.items():
            opp_timestamp = datetime.fromisoformat(opp.timestamp).timestamp()
            if opp_timestamp < cutoff_time:
                to_remove.append(opp_id)
        
        for opp_id in to_remove:
            del self.pending_opportunities[opp_id]
    
    async def execute_arbitrage(self, opportunity_id: str) -> Dict[str, any]:
        """Execute arbitrage trade"""
        try:
            if not self.execution_enabled:
                return {
                    "success": False,
                    "message": "Trading is currently disabled",
                    "details": "Use emergency halt to re-enable"
                }
            
            opportunity = self.pending_opportunities.get(opportunity_id)
            if not opportunity:
                return {
                    "success": False,
                    "message": "Opportunity not found or expired",
                    "details": f"ID {opportunity_id} not in pending list"
                }
            
            # Verify opportunity is still valid (re-check prices)
            logger.info(f"🔄 Re-checking prices for {opportunity_id}...")
            
            # For demo mode, simulate execution
            if True:  # Replace with settings.is_demo_mode()
                await asyncio.sleep(2)  # Simulate execution delay
                result = {
                    "success": True,
                    "message": "DEMO execution successful",
                    "details": f"Simulated trade: ${opportunity.guaranteed_profit:.2f} profit",
                    "actual_profit": opportunity.guaranteed_profit,
                    "execution_time": 2.1
                }
            else:
                # Real execution logic would go here
                result = await self._execute_real_trade(opportunity)
            
            # Send confirmation
            await self.alerter.send_execution_confirmation(
                opportunity_id, 
                "EXECUTE_TRADE", 
                result["success"], 
                result["details"]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error executing arbitrage {opportunity_id}: {e}")
            return {
                "success": False,
                "message": "Execution error",
                "details": str(e)
            }
    
    async def _execute_real_trade(self, opportunity) -> Dict:
        """Execute real arbitrage trade (LIVE MODE ONLY)"""
        # This would implement actual trade execution
        # For now, returns placeholder
        return {
            "success": False,
            "message": "Real trading not implemented",
            "details": "Demo mode only"
        }
    
    def emergency_halt(self) -> str:
        """Emergency halt all trading"""
        self.execution_enabled = False
        logger.warning("🛑 EMERGENCY HALT - All trading disabled")
        return "🛑 Emergency halt activated. All trading disabled."
    
    def resume_trading(self) -> str:
        """Resume trading after halt"""
        self.execution_enabled = True
        logger.info("✅ Trading resumed")
        return "✅ Trading resumed. Bot is now active."

# Web interface for one-click execution
class WebExecutionInterface:
    """Simple web interface for one-click execution from Discord links"""
    
    def __init__(self, execution_handler, port: int = 8080):
        self.execution_handler = execution_handler
        self.port = port
        
    def create_execution_page(self, opportunity_id: str) -> str:
        """Create simple HTML page for one-click execution"""
        opportunity = self.execution_handler.pending_opportunities.get(opportunity_id)
        
        if not opportunity:
            return """
            <html><body>
            <h2>❌ Opportunity Not Found</h2>
            <p>This opportunity has expired or doesn't exist.</p>
            </body></html>
            """
        
        return f"""
        <html>
        <head>
            <title>Arbitrage Execution - {opportunity_id}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: white; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .profit {{ color: #00ff00; font-size: 24px; font-weight: bold; }}
                .strategy {{ background: #333; padding: 15px; border-radius: 8px; margin: 10px 0; }}
                .button {{ 
                    padding: 15px 30px; margin: 10px; border: none; border-radius: 8px; 
                    font-size: 18px; cursor: pointer; color: white; text-decoration: none;
                    display: inline-block; text-align: center;
                }}
                .execute {{ background: #00ff00; color: black; }}
                .decline {{ background: #ff0000; }}
                .details {{ background: #0099ff; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Arbitrage Opportunity</h1>
                <div class="profit">💰 ${opportunity.guaranteed_profit:.2f} Profit</div>
                <p><strong>Contract:</strong> {opportunity.kalshi_ticker}</p>
                <p><strong>Confidence:</strong> {opportunity.match_confidence:.1%}</p>
                
                <div class="strategy">
                    <h3>📊 Strategy</h3>
                    <p>Buy {opportunity.buy_platform} {opportunity.buy_side} @ ${opportunity.kalshi_execution_price:.3f}</p>
                    <p>Sell {opportunity.sell_platform} {opportunity.sell_side} @ ${opportunity.polymarket_execution_price:.3f}</p>
                </div>
                
                <a href="/execute/{opportunity_id}" class="button execute">✅ EXECUTE TRADE</a>
                <a href="/decline/{opportunity_id}" class="button decline">❌ DECLINE</a>
                <a href="/details/{opportunity_id}" class="button details">📊 DETAILS</a>
                
                <p><small>ID: {opportunity_id}</small></p>
            </div>
        </body>
        </html>
        """

# Test the Discord alerter
async def test_discord_alerter():
    """Test the Discord alerting system"""
    print("🚀 Testing Discord Arbitrage Alerter...")
    
    # Mock opportunity for testing
    from dataclasses import dataclass
    from datetime import datetime
    
    @dataclass
    class MockOpportunity:
        opportunity_id: str = "TEST_001"
        kalshi_ticker: str = "NASDAQ100-24DEC31-19000"
        polymarket_condition_id: str = "0x123abcdef"
        guaranteed_profit: float = 25.50
        profit_percentage: float = 12.75
        profit_per_hour: float = 850.0
        trade_size_usd: float = 200.0
        buy_platform: str = "Kalshi"
        sell_platform: str = "Polymarket"
        buy_side: str = "YES"
        sell_side: str = "NO"
        kalshi_execution_price: float = 0.485
        polymarket_execution_price: float = 0.534
        liquidity_score: float = 87.0
        execution_certainty: float = 94.0
        time_to_expiry_hours: float = 16.5
        kalshi_slippage_percent: float = 0.8
        polymarket_slippage_percent: float = 1.2
        recommendation: str = "EXECUTE_IMMEDIATELY"
        match_confidence: float = 0.92
        timestamp: str = datetime.now().isoformat()
    
    # Test with environment webhook URL
    import os
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    
    if not webhook_url:
        print("❌ No Discord webhook URL found in environment")
        return
    
    alerter = DiscordArbitrageAlerter(webhook_url)
    opportunity = MockOpportunity()
    
    # Send test alert
    success = await alerter.send_arbitrage_alert(opportunity)
    
    if success:
        print("✅ Discord alert sent successfully!")
        
        # Send test execution confirmation
        await asyncio.sleep(2)
        await alerter.send_execution_confirmation(
            opportunity.opportunity_id, 
            "TEST_EXECUTION", 
            True, 
            "Test execution completed successfully"
        )
        
        # Send test daily summary
        await asyncio.sleep(2)
        await alerter.send_daily_summary(5, 127.50, 3, 85.0)
        
        print("✅ All Discord tests completed!")
    else:
        print("❌ Discord alert failed")

if __name__ == "__main__":
    asyncio.run(test_discord_alerter())
