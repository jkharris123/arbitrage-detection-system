#!/usr/bin/env python3
"""
Simple launcher for the arbitrage bot
Run this to start the system with sensible defaults
"""

import sys
import os
import subprocess

def main():
    print("🚀 Arbitrage Bot Launcher")
    print("=" * 50)
    
    # Check for required environment variables
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ ERROR: OPENAI_API_KEY not set!")
        print("Please add to .env file:")
        print("OPENAI_API_KEY=sk-...")
        print("Get one from: https://platform.openai.com/api-keys")
        sys.exit(1)
    
    print("\nSelect mode:")
    print("1. Test Run - Alert Mode (Discord alerts)")
    print("2. Test Run - Auto Mode (automatic execution)")
    print("3. Live Monitor - Alert Mode (recommended)")
    print("4. Live Monitor - Auto Mode (fully automated)")
    print("5. View Documentation")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == '1':
        print("\n🧪 Running test cycle with Discord alerts...")
        subprocess.run([sys.executable, 'fully_automated_enhanced.py', 'test', '--mode', 'alert'])
    
    elif choice == '2':
        print("\n🧪 Running test cycle with auto execution...")
        subprocess.run([sys.executable, 'fully_automated_enhanced.py', 'test', '--mode', 'auto'])
    
    elif choice == '3':
        print("\n📱 Starting live monitoring with Discord alerts...")
        print("💡 You'll receive alerts and can execute with 'EXECUTE A001' commands")
        interval = input("Scan interval in minutes (default 15): ").strip() or '15'
        subprocess.run([sys.executable, 'fully_automated_enhanced.py', 'monitor', '--mode', 'alert', '--interval', interval])
    
    elif choice == '4':
        print("\n🤖 Starting fully automated monitoring...")
        print("⚠️  WARNING: This will auto-execute all profitable opportunities!")
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        if confirm == 'yes':
            interval = input("Scan interval in minutes (default 15): ").strip() or '15'
            subprocess.run([sys.executable, 'fully_automated_enhanced.py', 'monitor', '--mode', 'auto', '--interval', interval])
        else:
            print("Cancelled.")
    
    elif choice == '5':
        print("\n📖 Opening documentation...")
        if os.path.exists('QUICK_START.md'):
            with open('QUICK_START.md', 'r') as f:
                print(f.read())
        else:
            print("Documentation not found!")
    
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()
