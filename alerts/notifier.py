#!/usr/bin/env python3
"""
Alert Notifier with Discord Integration
Sends formatted arbitrage alerts to Discord
"""

import os
import requests
import json
from datetime import datetime, time
from typing import List, Dict, Optional

# Load .env from parent directory
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class AlertNotifier:
    """
    Send arbitrage alerts via Discord with smart scheduling
    """
    
    def __init__(self):
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK')
        
        # Alert scheduling settings
        self.sleep_start = datetime.strptime(os.getenv('ALERT_SLEEP_START', '23:00'), '%H:%M').time()
        self.sleep_end = datetime.strptime(os.getenv('ALERT_SLEEP_END', '07:00'), '%H:%M').time()
        self.weekend_alerts = os.getenv('WEEKEND_ALERTS', 'false').lower() == 'true'
        self.emergency_threshold = float(os.getenv('EMERGENCY_PROFIT_THRESHOLD', '100.0'))
        
        # Queued alerts for sleep mode
        self.queued_alerts = []
        
        print(f"🔔 AlertNotifier initialized")
        print(f"   Sleep mode: {self.sleep_start} - {self.sleep_end}")
        print(f"   Weekend alerts: {self.weekend_alerts}")
        print(f"   Emergency threshold: ${self.emergency_threshold}")
        
        if not self.discord_webhook:
            print("⚠️ No Discord webhook configured - alerts will be logged only")
    
    def should_send_alert(self, profit_amount: float = 0.0) -> bool:
        """
        Determine if alerts should be sent based on time and profit
        """
        now = datetime.now()
        current_time = now.time()
        
        # Emergency override for large profits
        if profit_amount >= self.emergency_threshold:
            return True
        
        # Check sleep hours
        if self._is_sleep_time(current_time):
            return False
        
        # Check weekends
        if not self.weekend_alerts and now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        return True
    
    def _is_sleep_time(self, current_time: time) -> bool:
        """Check if current time is in sleep hours"""
        if self.sleep_start <= self.sleep_end:
            # Normal case: 23:00 - 07:00 (same day)
            return self.sleep_start <= current_time <= self.sleep_end
        else:
            # Edge case: 23:00 - 07:00 (crosses midnight)
            return current_time >= self.sleep_start or current_time <= self.sleep_end
    
    def send_arbitrage_alerts(self, opportunities: List) -> None:
        """
        Send alerts for arbitrage opportunities
        Handles sleep mode and formatting
        """
        if not opportunities:
            return
        
        for opportunity in opportunities:
            profit_amount = getattr(opportunity, 'total_net_profit', 0.0)
            
            if self.should_send_alert(profit_amount):
                self._send_immediate_alert(opportunity)
            else:
                self._queue_alert(opportunity)
    
    def _send_immediate_alert(self, opportunity) -> None:
        """Send immediate alert to Discord"""
        try:
            # Calculate time metrics
            time_metrics = self._calculate_time_metrics(opportunity)
            
            # Format the alert message
            alert_data = self._format_discord_alert(opportunity, time_metrics)
            
            if self.discord_webhook:
                self._send_to_discord(alert_data)
            else:
                self._log_alert(alert_data)
                
        except Exception as e:
            print(f"❌ Error sending alert: {e}")
    
    def _calculate_time_metrics(self, opportunity) -> Dict:
        """Calculate daily, weekly, and annualized returns"""
        try:
            # Get expiration date (stub - will need real data)
            expiration_date = getattr(opportunity, 'expiration_date', 
                                    datetime.now().replace(month=12, day=31))  # Default to end of year
            
            now = datetime.now()
            days_to_expiry = max(1, (expiration_date - now).days)
            
            profit_margin = getattr(opportunity, 'profit_margin_percent', 0.0)
            total_profit = getattr(opportunity, 'total_net_profit', 0.0)
            
            # Calculate return rates
            daily_return = profit_margin / days_to_expiry
            weekly_return = daily_return * 7
            annualized_return = daily_return * 365
            daily_dollar_rate = total_profit / days_to_expiry
            
            return {
                'days_to_expiry': days_to_expiry,
                'daily_return_percent': daily_return,
                'weekly_return_percent': weekly_return,
                'annualized_return_percent': annualized_return,
                'daily_dollar_rate': daily_dollar_rate,
                'expiration_date': expiration_date
            }
            
        except Exception as e:
            print(f"⚠️ Error calculating time metrics: {e}")
            return {
                'days_to_expiry': 30,
                'daily_return_percent': 0.1,
                'weekly_return_percent': 0.7,
                'annualized_return_percent': 36.5,
                'daily_dollar_rate': 1.0,
                'expiration_date': datetime.now()
            }
    
    def _format_discord_alert(self, opportunity, time_metrics: Dict) -> Dict:
        """Format opportunity as Discord embed"""
        
        # Get opportunity data with fallbacks
        contract_name = getattr(opportunity, 'contract_name', 'Unknown Contract')
        total_profit = getattr(opportunity, 'total_net_profit', 0.0)
        profit_margin = getattr(opportunity, 'profit_margin_percent', 0.0)
        buy_platform = getattr(opportunity, 'buy_platform', 'Platform A')
        sell_platform = getattr(opportunity, 'sell_platform', 'Platform B')
        buy_price = getattr(opportunity, 'buy_price', 0.0)
        sell_price = getattr(opportunity, 'sell_price', 0.0)
        volume = getattr(opportunity, 'optimal_volume', getattr(opportunity, 'max_volume', 0))
        
        # Determine embed color based on profit
        if total_profit >= 100:
            color = 0x00ff00  # Green for high profit
        elif total_profit >= 50:
            color = 0xffff00  # Yellow for medium profit
        else:
            color = 0x00ffff  # Cyan for low profit
        
        # Build the embed
        embed = {
            "title": "💎 ARBITRAGE OPPORTUNITY",
            "description": f"**{contract_name}**",
            "color": color,
            "fields": [
                {
                    "name": "💰 Profit Analysis",
                    "value": f"**${total_profit:.2f}** ({profit_margin:.2f}%)\n"
                            f"Volume: {volume} contracts",
                    "inline": True
                },
                {
                    "name": "📊 Return Rates",
                    "value": f"Daily: **{time_metrics['daily_return_percent']:.2f}%**/day\n"
                            f"Weekly: {time_metrics['weekly_return_percent']:.1f}%/week\n"
                            f"Annual: {time_metrics['annualized_return_percent']:.0f}%/year",
                    "inline": True
                },
                {
                    "name": "🎯 Toward $1k/day Goal",
                    "value": f"**${time_metrics['daily_dollar_rate']:.2f}**/day\n"
                            f"Expires: {time_metrics['expiration_date'].strftime('%Y-%m-%d')}\n"
                            f"({time_metrics['days_to_expiry']} days)",
                    "inline": True
                },
                {
                    "name": "🔄 Trading Strategy",
                    "value": f"**Buy** {buy_platform} @ ${buy_price:.3f}\n"
                            f"**Sell** {sell_platform} @ ${sell_price:.3f}\n"
                            f"Net spread: ${sell_price - buy_price:.3f}",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Arbitrage Bot • {datetime.now().strftime('%H:%M:%S')}"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {"embeds": [embed]}
    
    def _send_to_discord(self, alert_data: Dict) -> bool:
        """Send formatted alert to Discord webhook"""
        try:
            response = requests.post(
                self.discord_webhook,
                json=alert_data,
                timeout=10
            )
            
            if response.status_code == 204:
                print("✅ Alert sent to Discord successfully")
                return True
            else:
                print(f"⚠️ Discord webhook returned status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send Discord alert: {e}")
            return False
    
    def _queue_alert(self, opportunity) -> None:
        """Queue alert for later delivery during sleep mode"""
        self.queued_alerts.append({
            'opportunity': opportunity,
            'timestamp': datetime.now()
        })
        print(f"😴 Alert queued (sleep mode): {getattr(opportunity, 'contract_name', 'Unknown')}")
    
    def send_morning_summary(self) -> None:
        """Send summary of queued alerts from overnight"""
        if not self.queued_alerts:
            return
        
        try:
            summary_embed = {
                "title": "🌅 OVERNIGHT ARBITRAGE SUMMARY",
                "description": f"**{len(self.queued_alerts)} opportunities** found while you were sleeping",
                "color": 0x87ceeb,  # Sky blue
                "fields": []
            }
            
            total_potential_profit = 0.0
            
            for i, alert in enumerate(self.queued_alerts[:5], 1):  # Show top 5
                opp = alert['opportunity']
                profit = getattr(opp, 'total_net_profit', 0.0)
                total_potential_profit += profit
                
                summary_embed["fields"].append({
                    "name": f"#{i} {getattr(opp, 'contract_name', 'Unknown')}",
                    "value": f"${profit:.2f} profit • {alert['timestamp'].strftime('%H:%M')}",
                    "inline": True
                })
            
            if len(self.queued_alerts) > 5:
                summary_embed["fields"].append({
                    "name": f"+ {len(self.queued_alerts) - 5} more opportunities",
                    "value": "Check logs for full details",
                    "inline": False
                })
            
            summary_embed["fields"].append({
                "name": "💰 Total Potential Profit",
                "value": f"**${total_potential_profit:.2f}**",
                "inline": False
            })
            
            if self.discord_webhook:
                self._send_to_discord({"embeds": [summary_embed]})
            
            # Clear queued alerts
            self.queued_alerts = []
            print(f"📬 Morning summary sent, cleared {len(self.queued_alerts)} queued alerts")
            
        except Exception as e:
            print(f"❌ Error sending morning summary: {e}")
    
    def _log_alert(self, alert_data: Dict) -> None:
        """Log alert to console when Discord is not configured"""
        try:
            embed = alert_data["embeds"][0]
            print(f"\n🔔 ARBITRAGE ALERT:")
            print(f"   {embed['title']}: {embed['description']}")
            
            for field in embed["fields"]:
                value_clean = field['value'].replace('**', '').replace('\n', ' | ')
                print(f"   {field['name']}: {value_clean}")
                
        except Exception as e:
            print(f"⚠️ Error logging alert: {e}")
    

    def send_bot_status(self, status: str, details: str = "") -> None:
        """Send bot status updates to Discord"""
        if not self.discord_webhook:
            print(f"🤖 Bot Status: {status} - {details}")
            return
        
        status_colors = {
            "started": 0x00ff00,    # Green
            "stopped": 0xff0000,    # Red
            "error": 0xff8c00,      # Orange
            "info": 0x87ceeb        # Sky blue
        }
        
        embed = {
            "title": "🤖 Arbitrage Bot Status",
            "description": status.title(),
            "color": status_colors.get(status.lower(), 0x87ceeb),
            "fields": [
                {
                    "name": "Details",
                    "value": details or "No additional details",
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._send_to_discord({"embeds": [embed]})
    
    def test_discord_connection(self) -> bool:
        """Test Discord webhook connection"""
        if not self.discord_webhook:
            print("❌ No Discord webhook configured")
            return False
        
        test_embed = {
            "title": "🧪 Test Alert",
            "description": "Discord connection test successful!",
            "color": 0x00ff00,
            "fields": [
                {
                    "name": "Status",
                    "value": "✅ Webhook working correctly",
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self._send_to_discord({"embeds": [test_embed]})

# Test function
def test_alert_notifier():
    """Test the alert notifier with dummy data"""
    notifier = AlertNotifier()
    
    # Test Discord connection
    print("Testing Discord connection...")
    notifier.test_discord_connection()
    
    # Test status message
    notifier.send_bot_status("started", "Arbitrage bot initialized and ready for trading")
    
    # Create dummy opportunity for testing
    class DummyOpportunity:
        def __init__(self):
            self.contract_name = "CPI-FEB25-ABOVE3"
            self.total_net_profit = 87.50
            self.profit_margin_percent = 3.2
            self.buy_platform = "Kalshi"
            self.sell_platform = "IBKR"
            self.buy_price = 0.485
            self.sell_price = 0.523
            self.optimal_volume = 200
            self.expiration_date = datetime(2025, 2, 15)
    
    # Test arbitrage alert
    dummy_opportunity = DummyOpportunity()
    notifier.send_arbitrage_alerts([dummy_opportunity])

if __name__ == "__main__":
    test_alert_notifier()