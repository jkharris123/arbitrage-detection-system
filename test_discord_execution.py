#!/usr/bin/env python3
"""
Discord Test - Send Mock Arbitrage Opportunity
Tests the complete Discord → Phone → Laptop execution flow
"""

import asyncio
import sys
import os
from datetime import datetime
from dataclasses import dataclass

# Add paths
sys.path.append('./alerts')
sys.path.append('./config')

@dataclass
class MockArbitrageOpportunity:
    """Mock opportunity for testing Discord execution flow"""
    opportunity_id: str = "TEST_DISCORD_001"
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
    timestamp: str = datetime.now().isoformat()

async def test_discord_execution_flow():
    """Test the complete Discord execution flow"""
    
    print("📱 TESTING DISCORD → PHONE → LAPTOP EXECUTION FLOW")
    print("=" * 60)
    
    try:
        from discord_alerter import DiscordArbitrageAlerter
        
        # Get Discord webhook from environment
        webhook_url = os.getenv('DISCORD_WEBHOOK')
        if not webhook_url:
            print("❌ No Discord webhook URL found in .env file")
            print("   Add DISCORD_WEBHOOK=your_webhook_url to .env")
            return
        
        # Create alerter
        alerter = DiscordArbitrageAlerter(webhook_url)
        
        # Create mock opportunity
        opportunity = MockArbitrageOpportunity()
        
        print("🎯 Mock Arbitrage Opportunity:")
        print(f"   Contract: {opportunity.kalshi_ticker}")
        print(f"   Profit: ${opportunity.guaranteed_profit:.2f} ({opportunity.profit_percentage:.1f}%)")
        print(f"   Strategy: Buy {opportunity.buy_platform} {opportunity.buy_side} @ ${opportunity.kalshi_execution_price:.3f}")
        print(f"             Sell {opportunity.sell_platform} {opportunity.sell_side} @ ${opportunity.polymarket_execution_price:.3f}")
        print(f"   ID: {opportunity.opportunity_id}")
        
        print("\n🚀 Sending Discord alert with execution URL...")
        
        # Send alert with execution URL (assuming web interface on localhost:8080)
        execution_base_url = "http://localhost:8080"  # Change this to your external IP for real testing
        success = await alerter.send_arbitrage_alert(opportunity, execution_base_url)
        
        if success:
            print("✅ Discord alert sent successfully!")
            print("\n📱 CHECK YOUR DISCORD CHANNEL NOW!")
            print("\n🔗 You should see:")
            print("   📊 Rich alert with profit analysis")
            print("   🚀 Blue 'EXECUTE FROM PHONE' link")
            print("   📱 Mobile-friendly execution instructions")
            
            print(f"\n🌐 Test execution flow:")
            print(f"   1. Click the execution link in Discord")
            print(f"   2. Should open: {execution_base_url}/execute/{opportunity.opportunity_id}")
            print(f"   3. Mobile-friendly page with big EXECUTE button")
            print(f"   4. Click EXECUTE → triggers trade on laptop")
            print(f"   5. Confirmation sent back to Discord")
            
            print(f"\n💡 Next steps:")
            print(f"   1. Start web interface: python3 web_interface.py")
            print(f"   2. Click the execution link from your phone")
            print(f"   3. Test the complete flow!")
            
        else:
            print("❌ Discord alert failed")
            print("   Check your webhook URL and internet connection")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure discord_alerter.py is available")
    except Exception as e:
        print(f"❌ Error: {e}")

async def send_system_status_test():
    """Send a simple system status test"""
    print("\n🧪 Testing basic Discord webhook...")
    
    try:
        from discord_alerter import DiscordArbitrageAlerter
        
        webhook_url = os.getenv('DISCORD_WEBHOOK')
        if not webhook_url:
            print("❌ No Discord webhook URL found")
            return
        
        alerter = DiscordArbitrageAlerter(webhook_url)
        
        success = await alerter.send_system_status(
            "ONLINE", 
            "🧪 **Testing Discord → Phone → Laptop Execution**\\n\\n📱 This is a test message to verify the webhook works.\\n🚀 Next: Testing full arbitrage alerts with execution URLs!"
        )
        
        if success:
            print("✅ Basic Discord test successful!")
        else:
            print("❌ Basic Discord test failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Choose test type:")
    print("1. Full arbitrage opportunity with execution URL")
    print("2. Basic webhook test")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_discord_execution_flow())
    elif choice == "2":
        asyncio.run(send_system_status_test())
    else:
        print("Invalid choice")
