#!/usr/bin/env python3
"""
MAIN ENHANCED ARBITRAGE DETECTION SYSTEM
Single entry point for all arbitrage detection and execution

This is the main file - runs the complete enhanced arbitrage system
with unified Discord bot integration.
"""

from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime

# Add paths
sys.path.append('./arbitrage')
sys.path.append('./data_collectors')
sys.path.append('./alerts')
sys.path.append('./config')

# Import the enhanced launch system
from launch_unified import EnhancedArbitrageSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for enhanced arbitrage system"""
    parser = argparse.ArgumentParser(description='Enhanced Arbitrage Detection System')
    parser.add_argument('--test', action='store_true', help='Run system test only')
    parser.add_argument('--discord', action='store_true', help='Run Discord bot only')
    parser.add_argument('--scan', action='store_true', help='Run single scan')
    parser.add_argument('--monitor', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=15, help='Monitoring interval (minutes)')
    
    args = parser.parse_args()
    
    print("🚀 ENHANCED ARBITRAGE DETECTION SYSTEM")
    print("=" * 50)
    print(f"📅 Started: {datetime.now()}")
    print(f"🎯 Goal: $1,000+ daily profit from risk-free arbitrage")
    print()
    
    # Initialize the enhanced system
    system = EnhancedArbitrageSystem()
    
    try:
        if args.test:
            # Run system test
            print("🧪 Running system test...")
            results = await system.run_economic_scan()
            if results:
                print(f"✅ Test completed: {results}")
                stats = system.get_system_stats()
                print(f"📊 Performance: {stats}")
            
        elif args.discord:
            # Run Discord bot only
            print("🤖 Starting unified Discord bot...")
            await system.run_unified_discord_bot()
            
        elif args.scan:
            # Single economic scan
            print("🔍 Running single economic arbitrage scan...")
            results = await system.run_economic_scan()
            if results:
                print(f"✅ Scan results: {results}")
            
        elif args.monitor:
            # Continuous monitoring
            print(f"🔄 Starting continuous monitoring (every {args.interval} minutes)...")
            await system.run_continuous_monitoring(args.interval)
            
        else:
            # Default: show help and run test
            print("📋 No command specified. Running quick test...")
            print("Available commands:")
            print("  --test      Run system test")
            print("  --discord   Run Discord bot")
            print("  --scan      Single arbitrage scan")
            print("  --monitor   Continuous monitoring")
            print()
            
            # Run quick test
            results = await system.run_economic_scan()
            if results:
                print(f"🎯 Quick test results: {results}")
            
    except KeyboardInterrupt:
        print("\\n🛑 System stopped by user")
    except Exception as e:
        print(f"\\n❌ System error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Enhanced Arbitrage System...")
    asyncio.run(main())
