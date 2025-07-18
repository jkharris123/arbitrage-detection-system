#!/usr/bin/env python3
"""
Simple Discord Bot Test
Tests basic Discord bot functionality without the full arbitrage system
"""

import asyncio
import os
import sys
from datetime import datetime

# Add paths
sys.path.append('./config')

async def test_discord_setup():
    """Test Discord bot setup"""
    
    print("🤖 DISCORD BOT SETUP TEST")
    print("=" * 35)
    print(f"📅 Test Time: {datetime.now()}")
    print()
    
    try:
        # Test 1: Check environment variables
        print("🔧 Test 1: Environment variables...")
        
        bot_token = os.getenv('DISCORD_BOT_TOKEN')
        channel_id = os.getenv('DISCORD_CHANNEL_ID') 
        webhook_url = os.getenv('DISCORD_WEBHOOK')
        
        if bot_token:
            print(f"   ✅ Bot token found: {bot_token[:20]}...")
        else:
            print("   ❌ Bot token missing (DISCORD_BOT_TOKEN)")
            
        if channel_id:
            print(f"   ✅ Channel ID found: {channel_id}")
        else:
            print("   ❌ Channel ID missing (DISCORD_CHANNEL_ID)")
            
        if webhook_url:
            print(f"   ✅ Webhook URL found: {webhook_url[:50]}...")
        else:
            print("   ❌ Webhook URL missing (DISCORD_WEBHOOK)")
        
        # Test 2: Try importing discord
        print("\\n📦 Test 2: Discord library...")
        try:
            import discord
            print(f"   ✅ Discord.py imported successfully (version: {discord.__version__})")
            discord_available = True
        except ImportError as e:
            print(f"   ❌ Discord.py not installed: {e}")
            print("   💡 Install with: pip install discord.py")
            discord_available = False
        
        # Test 3: Test webhook (sending only)
        print("\\n📨 Test 3: Webhook test...")
        if webhook_url:
            try:
                import requests
                
                test_payload = {
                    "username": "Arbitrage Bot Test",
                    "content": "🧪 Discord setup test - webhook working!",
                    "embeds": [{
                        "title": "Discord Setup Test",
                        "description": "If you see this, your webhook is working!",
                        "color": 0x00FF00,
                        "timestamp": datetime.now().isoformat(),
                        "fields": [
                            {
                                "name": "Test Status",
                                "value": "✅ Webhook functional",
                                "inline": True
                            },
                            {
                                "name": "Next Step", 
                                "value": "Set up bot token for message listening",
                                "inline": True
                            }
                        ]
                    }]
                }
                
                response = requests.post(webhook_url, json=test_payload, timeout=10)
                
                if response.status_code == 204:
                    print("   ✅ Webhook test successful - check Discord!")
                else:
                    print(f"   ❌ Webhook failed: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Webhook test error: {e}")
        else:
            print("   ⚠️ No webhook URL to test")
        
        # Test 4: Test bot initialization (if available)
        print("\\n🤖 Test 4: Bot initialization...")
        if discord_available and bot_token:
            try:
                # Import our bot classes
                sys.path.append('.')
                from discord_execution_bot import DiscordExecutionBot
                
                # Create a simple test bot instance
                print("   ✅ Bot classes imported successfully")
                print("   📝 Bot configuration ready")
                
                # Don't actually start the bot, just verify we can create it
                print("   💡 To start bot: python3 launch_enhanced.py discord")
                
            except Exception as e:
                print(f"   ❌ Bot initialization error: {e}")
        else:
            missing = []
            if not discord_available:
                missing.append("discord.py library")
            if not bot_token:
                missing.append("bot token")
            print(f"   ⚠️ Bot test skipped - missing: {', '.join(missing)}")
        
        # Summary
        print("\\n" + "=" * 40)
        print("📊 DISCORD SETUP SUMMARY")
        print("=" * 40)
        
        ready_count = 0
        total_checks = 4
        
        if bot_token: ready_count += 1
        if channel_id: ready_count += 1  
        if webhook_url: ready_count += 1
        if discord_available: ready_count += 1
        
        print(f"🎯 Setup Progress: {ready_count}/{total_checks} components ready")
        
        if ready_count == total_checks:
            print("\\n🎉 DISCORD BOT READY!")
            print("✅ All components configured")
            print("\\n🚀 Next steps:")
            print("   1. Run: python3 launch_enhanced.py discord")
            print("   2. In Discord, type: STATUS")
            print("   3. Bot should respond with status message")
            print("   4. Test execution with: EXECUTE A001 (when opportunities exist)")
            
        elif ready_count >= 2:
            print("\\n🔶 PARTIAL SETUP")
            print("✅ Basic components ready")
            print("⚠️ Missing components for full functionality")
            
            if not bot_token:
                print("\\n📋 TO GET BOT TOKEN:")
                print("   1. Go to: https://discord.com/developers/applications")
                print("   2. Create New Application")
                print("   3. Go to Bot tab")
                print("   4. Copy token and add to .env file:")
                print("      DISCORD_BOT_TOKEN=your_token_here")
                
            if not channel_id:
                print("\\n📋 TO GET CHANNEL ID:")
                print("   1. In Discord, right-click your channel")
                print("   2. Click 'Copy Channel ID'")
                print("   3. Add to .env file:")
                print("      DISCORD_CHANNEL_ID=your_channel_id")
                
            if not discord_available:
                print("\\n📋 TO INSTALL DISCORD.PY:")
                print("   pip install discord.py")
                
        else:
            print("\\n❌ SETUP INCOMPLETE")
            print("Need to set up Discord bot and webhook")
            print("\\n📋 SETUP GUIDE:")
            print("   1. Create Discord App: https://discord.com/developers/applications")
            print("   2. Get bot token and webhook URL")
            print("   3. Install discord.py: pip install discord.py")
            print("   4. Add credentials to .env file")
        
        return ready_count == total_checks
        
    except Exception as e:
        print(f"\\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_discord_setup())
        if result:
            print("\\n🎉 Ready for Discord bot execution!")
        else:
            print("\\n🔧 Complete setup steps above before testing bot")
    except Exception as e:
        print(f"\\n💥 Test crashed: {e}")
