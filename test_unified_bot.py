#!/usr/bin/env python3
"""
Test Unified Discord Bot Setup
Tests the simplified unified bot approach
"""

import asyncio
import os
import sys
from datetime import datetime

# Add paths
sys.path.append('./config')

async def test_unified_bot_setup():
    """Test unified Discord bot setup"""
    
    print("🤖 UNIFIED DISCORD BOT TEST")
    print("=" * 40)
    print("Testing the simplified unified bot approach...")
    print("(One bot for both alerts AND execution commands)")
    print()
    
    try:
        # Test 1: Check what we need
        print("📋 What we need for unified bot:")
        print("   ✅ Discord bot token (DISCORD_BOT_TOKEN)")
        print("   ✅ Discord channel ID (DISCORD_CHANNEL_ID)")
        print("   ❌ No webhook needed anymore!")
        print()
        
        # Test 2: Check environment variables
        print("🔧 Test 1: Environment variables...")
        
        bot_token = os.getenv('DISCORD_BOT_TOKEN')
        channel_id = os.getenv('DISCORD_CHANNEL_ID') 
        webhook_url = os.getenv('DISCORD_WEBHOOK')  # We don't need this anymore
        
        if bot_token:
            print(f"   ✅ Bot token found: {bot_token[:20]}...")
        else:
            print("   ❌ Bot token missing (DISCORD_BOT_TOKEN)")
            
        if channel_id:
            print(f"   ✅ Channel ID found: {channel_id}")
        else:
            print("   ❌ Channel ID missing (DISCORD_CHANNEL_ID)")
            
        if webhook_url:
            print(f"   📝 Webhook found but not needed: {webhook_url[:30]}...")
        else:
            print("   📝 No webhook (not needed for unified bot)")
        
        # Test 3: Discord library
        print("\\n📦 Test 2: Discord library...")
        try:
            import discord
            print(f"   ✅ Discord.py available (version: {discord.__version__})")
            discord_available = True
        except ImportError as e:
            print(f"   ❌ Discord.py not installed: {e}")
            print("   💡 Install with: pip install discord.py")
            discord_available = False
        
        # Test 4: Import unified bot
        print("\\n🤖 Test 3: Unified bot import...")
        if discord_available:
            try:
                from unified_discord_bot import UnifiedArbitrageBot, UnifiedBotManager
                print("   ✅ Unified bot classes imported successfully")
                bot_classes_available = True
            except Exception as e:
                print(f"   ❌ Unified bot import error: {e}")
                bot_classes_available = False
        else:
            print("   ⚠️ Skipped - Discord not available")
            bot_classes_available = False
        
        # Test 5: Test bot initialization (without starting)
        print("\\n🚀 Test 4: Bot initialization test...")
        if bot_classes_available and bot_token:
            try:
                # Test creating bot manager (don't start it)
                manager = UnifiedBotManager()
                if manager.bot:
                    print("   ✅ Bot manager created successfully")
                    print("   ✅ Bot configuration ready")
                else:
                    print("   ⚠️ Bot manager created but bot not available")
            except Exception as e:
                print(f"   ❌ Bot initialization error: {e}")
        else:
            missing = []
            if not bot_classes_available:
                missing.append("bot classes")
            if not bot_token:
                missing.append("bot token")
            print(f"   ⚠️ Skipped - missing: {', '.join(missing)}")
        
        # Summary
        print("\\n" + "=" * 50)
        print("📊 UNIFIED BOT SETUP SUMMARY")
        print("=" * 50)
        
        required_items = [
            ("Discord.py installed", discord_available),
            ("Bot token configured", bool(bot_token)),
            ("Channel ID configured", bool(channel_id)),
            ("Bot classes available", bot_classes_available)
        ]
        
        ready_count = sum(1 for _, available in required_items if available)
        total_required = len(required_items)
        
        print(f"🎯 Setup Progress: {ready_count}/{total_required} components ready")
        print()
        
        for item, available in required_items:
            status = "✅" if available else "❌"
            print(f"   {status} {item}")
        
        if ready_count == total_required:
            print("\\n🎉 UNIFIED BOT READY!")
            print("✅ All components configured")
            print("\\n🚀 Next steps:")
            print("   1. Run: python3 launch_unified.py bot")
            print("   2. Bot will come online in Discord")
            print("   3. Type 'STATUS' in Discord to test")
            print("   4. Bot will send/receive all messages")
            print("\\n💡 Unified bot features:")
            print("   • Sends arbitrage alerts")
            print("   • Listens for 'EXECUTE A001' commands") 
            print("   • Handles 'STATUS', 'HALT', 'RESUME'")
            print("   • No webhook needed!")
            
        elif ready_count >= 2:
            print("\\n🔶 SETUP IN PROGRESS")
            print("Some components ready, finish setup for full functionality")
            
            if not bot_token:
                print("\\n📋 TO GET BOT TOKEN:")
                print("   1. https://discord.com/developers/applications")
                print("   2. Create Application → Bot → Copy Token")
                print("   3. Add to .env: DISCORD_BOT_TOKEN=your_token")
                
            if not channel_id:
                print("\\n📋 TO GET CHANNEL ID:")
                print("   1. Right-click Discord channel")
                print("   2. 'Copy Channel ID'")
                print("   3. Add to .env: DISCORD_CHANNEL_ID=your_id")
                
            if not discord_available:
                print("\\n📋 TO INSTALL DISCORD:")
                print("   pip install discord.py")
                
        else:
            print("\\n❌ SETUP INCOMPLETE")
            print("Follow Discord bot setup guide")
        
        print("\\n🎯 UNIFIED BOT ADVANTAGES:")
        print("   ✅ Single bot handles everything")
        print("   ✅ No webhook configuration needed")
        print("   ✅ Real-time command response")
        print("   ✅ Rich embeds for alerts")
        print("   ✅ Emergency controls built-in")
        
        return ready_count == total_required
        
    except Exception as e:
        print(f"\\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def demo_unified_bot_flow():
    """Demo how the unified bot would work"""
    
    print("\\n" + "=" * 50)
    print("🎭 UNIFIED BOT WORKFLOW DEMO")
    print("=" * 50)
    print("Here's how the unified bot works:")
    print()
    
    print("1️⃣ **Bot Startup:**")
    print("   🤖 Bot comes online in Discord")
    print("   📱 Sends startup message with commands")
    print()
    
    print("2️⃣ **Arbitrage Alert:**")
    print("   🔍 System finds $25 profit opportunity")
    print("   📢 Bot sends rich alert: 'A001 - $25 profit available'")
    print("   💬 'Type EXECUTE A001 to trade'")
    print()
    
    print("3️⃣ **User Execution:**")
    print("   📱 User types: 'EXECUTE A001' (from phone/computer)")
    print("   ⚡ Bot immediately responds: 'Executing A001...'")
    print("   ✅ Bot executes trade and confirms: 'Trade completed! $25 profit'")
    print()
    
    print("4️⃣ **Status & Control:**")
    print("   📊 User types: 'STATUS' → Bot shows current opportunities")
    print("   🛑 User types: 'HALT' → Bot stops all trading")
    print("   ▶️ User types: 'RESUME' → Bot resumes trading")
    print()
    
    print("🎯 **Key Benefits:**")
    print("   • One bot for everything (no webhook needed)")
    print("   • Real-time command response")
    print("   • Works from any device")
    print("   • Rich visual alerts")
    print("   • Built-in safety controls")

if __name__ == "__main__":
    try:
        result = asyncio.run(test_unified_bot_setup())
        asyncio.run(demo_unified_bot_flow())
        
        if result:
            print("\\n🎉 Ready to start unified Discord bot!")
        else:
            print("\\n🔧 Complete setup steps above first")
            
    except Exception as e:
        print(f"\\n💥 Test crashed: {e}")
