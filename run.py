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
    print("1. Test Run (single cycle)")
    print("2. Live Monitor - Fully Automated (recommended)")
    print("3. Check Verification Status")
    print("4. View Documentation")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        print("\n🧪 Running single test cycle...")
        subprocess.run([sys.executable, 'fully_automated_enhanced.py', 'test'])
    
    elif choice == '2':
        print("\n🤖 Starting fully automated monitoring...")
        print("✅ Auto-executes verified matches")
        print("📱 Alerts only for new matches needing verification")
        print("📊 Daily summaries at 6 PM EST")
        interval = input("\nScan interval in minutes (default 15): ").strip() or '15'
        days = input("Contract expiry window in days (default 14): ").strip() or '14'
        subprocess.run([sys.executable, 'fully_automated_enhanced.py', 'monitor', '--interval', interval, '--days', days])
    
    elif choice == '3':
        print("\n📊 Checking verification status...")
        # Verification status - check matching files directly
        print("📁 Checking for verified match files...")
        if os.path.exists('manual_matches.csv'):
            with open('manual_matches.csv', 'r') as f:
                lines = f.readlines()
                print(f"✅ Found {len(lines)-1} verified matches in manual_matches.csv")
        else:
            print("❌ No manual_matches.csv found")
    
    elif choice == '4':
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
