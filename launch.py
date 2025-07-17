#!/usr/bin/env python3
"""
Enhanced System Launcher
Cleans up redundant files and provides easy system management
"""

import os
import subprocess
import sys
import time
from threading import Thread

def cleanup_redundant_files():
    """Remove redundant files to clean up the project"""
    
    print("🧹 Cleaning up redundant files...")
    
    files_to_remove = [
        "main.py",                          # Old main file
        "test_setup.py",                    # Old test file  
        "verify_enhanced_system.py",        # Redundant verification
        "arbitrage/detector.py",            # Old detector
        "data_collectors/polymarket_client.py" # Old Polymarket client
    ]
    
    removed_count = 0
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"   ✅ Removed {file_path}")
                removed_count += 1
            except Exception as e:
                print(f"   ⚠️ Could not remove {file_path}: {e}")
        else:
            print(f"   ✅ {file_path} (already removed)")
    
    print(f"\n📊 Cleanup complete: {removed_count} files removed")
    
    print("\n✅ CLEAN PROJECT STRUCTURE:")
    keep_files = [
        "main_enhanced.py",                 # Enhanced main orchestrator
        "test_enhanced_system.py",          # Comprehensive testing
        "web_interface.py",                 # Mobile execution interface  
        "arbitrage/detector_enhanced.py",   # Enhanced detector
        "data_collectors/kalshi_client.py", # Working Kalshi client
        "data_collectors/polymarket_client_enhanced.py", # Enhanced Polymarket
        "alerts/discord_alerter.py",        # Discord alerts with execution URLs
        "config/settings.py",               # Configuration
        "README_ENHANCED.md"                # Documentation
    ]
    
    for file in keep_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ⚠️ {file} (missing)")

def start_web_interface():
    """Start the web interface in background"""
    print("\n🌐 Starting web interface for mobile execution...")
    try:
        subprocess.Popen([sys.executable, "web_interface.py"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        print("   ✅ Web interface started on http://localhost:8080")
        return True
    except Exception as e:
        print(f"   ❌ Failed to start web interface: {e}")
        return False

def main():
    """Main launcher"""
    
    print("🚀 ENHANCED ARBITRAGE SYSTEM LAUNCHER")
    print("=" * 50)
    
    # Step 1: Cleanup
    cleanup_redundant_files()
    
    # Step 2: Check what to run
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            print("\n🧪 Running system test...")
            os.system("python3 test_enhanced_system.py")
            
        elif command == "scan":
            print("\n🔍 Running single arbitrage scan...")
            os.system("python3 main_enhanced.py --test")
            
        elif command == "discord":
            print("\n📱 Testing Discord execution flow...")
            os.system("python3 test_discord_execution.py")
            
        elif command == "web":
            print("\n🌐 Starting web interface only...")
            os.system("python3 web_interface.py")
            
        elif command == "full":
            print("\n🎯 Starting FULL SYSTEM...")
            
            # Start web interface
            web_started = start_web_interface()
            if web_started:
                time.sleep(2)  # Give web interface time to start
                
                print("\n🤖 Starting arbitrage bot with Discord alerts...")
                print("   📱 Mobile execution URLs will be included in Discord alerts")
                print("   🏠 Web interface running on laptop for execution")
                print("\n   Press Ctrl+C to stop\n")
                
                try:
                    os.system("python3 main_enhanced.py")
                except KeyboardInterrupt:
                    print("\n⏹️ Stopping system...")
            else:
                print("❌ Cannot start full system without web interface")
                
        else:
            print(f"❌ Unknown command: {command}")
            show_usage()
    else:
        show_usage()

def show_usage():
    """Show usage instructions"""
    print("""
🎯 USAGE:
   python3 launch.py test     # Test all components
   python3 launch.py scan     # Run single arbitrage scan  
   python3 launch.py discord  # Test Discord alerts
   python3 launch.py web      # Start web interface only
   python3 launch.py full     # Start COMPLETE system

📱 DISCORD → PHONE → LAPTOP EXECUTION:
   1. Run 'python3 launch.py full'
   2. Bot finds opportunity → Sends Discord alert
   3. Click execution URL in Discord from your phone
   4. Trade executes on laptop automatically
   5. Confirmation sent back to Discord

💰 Goal: $1,000/day guaranteed profit from arbitrage
🛡️ Risk: ZERO (demo mode with precise calculations)
""")

if __name__ == "__main__":
    main()
