#!/usr/bin/env python3
"""
Simple Discord Alert Test
Just sends a mock arbitrage opportunity to test the alert format
"""

import asyncio
import requests
import os
from datetime import datetime
from dataclasses import dataclass

@dataclass
class MockOpportunity:
    """Mock arbitrage opportunity for testing"""
    opportunity_id: str = "ARB_TEST_001"
    kalshi_ticker: str = "NASDAQ100-24DEC31-19000"
    polymarket_condition_id: str = "0x1234567890abcdef"
    guaranteed_profit: float = 47.85
    profit_percentage: float = 23.9
    profit_per_hour: float = 1850.0
    trade_size_usd: float = 200.0
    buy_platform: str = "Kalshi"
    sell_platform: str = "Polymarket"
    buy_side: str = "YES"
    sell_side: str = "NO"
    kalshi_execution_price: float = 0.425
    polymarket_execution_price: float = 0.665
    liquidity_score: float = 92.0
    execution_certainty: float = 97.0
    time_to_expiry_hours: float = 8.5
    kalshi_slippage_percent: float = 0.6
    polymarket_slippage_percent: float = 0.9
    recommendation: str = "EXECUTE_IMMEDIATELY"
    match_confidence: float = 0.96

def send_simple_discord_alert(opportunity):
    """Send simple Discord alert with message-based execution"""
    
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        print("❌ No DISCORD_WEBHOOK found in .env")
        return False
    
    # Create Discord embed
    embed = {
        "title": "🎯 Arbitrage Opportunity Found!",
        "description": f"**{opportunity.kalshi_ticker}** ↔ **{opportunity.polymarket_condition_id[:8]}...**",
        "color": 0x00FF00,  # Green
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
                "name": "🎯 Risk Analysis",
                "value": f"Liquidity: {opportunity.liquidity_score:.0f}/100\nCertainty: {opportunity.execution_certainty:.0f}/100\nTime Left: {opportunity.time_to_expiry_hours:.1f}h",
                "inline": True
            },
            {
                "name": "📋 Slippage",
                "value": f"Kalshi: {opportunity.kalshi_slippage_percent:.1f}%\nPolymarket: {opportunity.polymarket_slippage_percent:.1f}%",
                "inline": True
            },
            {
                "name": "📱 MOBILE EXECUTION",
                "value": f"**Reply in this channel:**\n`EXECUTE {opportunity.opportunity_id}`\n\n🚀 Execute from any device!",
                "inline": False
            }
        ],
        "footer": {
            "text": f"ID: {opportunity.opportunity_id} | Confidence: {opportunity.match_confidence:.1%}"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Main message content
    content = f"""🚨 **NEW ARBITRAGE OPPORTUNITY** 🚨

📱 **MOBILE EXECUTION READY**
Reply with: `EXECUTE {opportunity.opportunity_id}`

🏠 Your laptop will execute the trade automatically!"""

    payload = {
        "username": "Arbitrage Bot",
        "content": content,
        "embeds": [embed]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 204:
            print("✅ Discord alert sent successfully!")
            return True
        else:
            print(f"❌ Discord failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending to Discord: {e}")
        return False

def send_system_status():
    """Send simple system status"""
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        print("❌ No DISCORD_WEBHOOK found in .env")
        return False
    
    payload = {
        "username": "Arbitrage Bot",
        "content": "🧪 **Testing Discord Integration**\n\n✅ Webhook connection working!\n📱 Ready for arbitrage alerts with mobile execution."
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 204
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("📱 SIMPLE DISCORD ALERT TEST")
    print("=" * 40)
    
    choice = input("Choose test:\n1. System status\n2. Full arbitrage alert\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\n🧪 Sending system status...")
        success = send_system_status()
        if success:
            print("✅ System status sent to Discord!")
        
    elif choice == "2":
        print("\n🎯 Sending mock arbitrage opportunity...")
        opportunity = MockOpportunity()
        success = send_simple_discord_alert(opportunity)
        
        if success:
            print(f"\n✅ Mock arbitrage alert sent!")
            print(f"\n📱 CHECK YOUR DISCORD CHANNEL!")
            print(f"\n🧪 You should see:")
            print(f"   💰 Profit: ${opportunity.guaranteed_profit:.2f} ({opportunity.profit_percentage:.1f}%)")
            print(f"   📊 Strategy details")
            print(f"   📱 Instructions to reply: EXECUTE {opportunity.opportunity_id}")
            print(f"\n🚀 Next steps:")
            print(f"   1. Check Discord for the alert")
            print(f"   2. Reply in Discord: EXECUTE {opportunity.opportunity_id}")
            print(f"   3. We'll build the listener to catch your reply!")
        
    else:
        print("Invalid choice")
