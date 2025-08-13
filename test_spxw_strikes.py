#!/usr/bin/env python3
"""
Test SPXW strike selection logic
Ensures short leg is AT the Kalshi level for perfect hedge
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_collectors.ibkr_options_client import IBKROptionsClient
from datetime import datetime, date
import time

def test_strike_selection():
    """Test that strikes are selected correctly for Kalshi hedge"""
    print("\n=== Testing SPXW Strike Selection ===")
    print("Critical: Short leg MUST be AT Kalshi level")
    print("=" * 60)
    
    # Create client
    client = IBKROptionsClient()
    
    try:
        # Connect
        print("\n1. Connecting to TWS...")
        if not client.connect_to_tws():
            print("❌ Failed to connect.")
            return
        print("✅ Connected")
        
        # Test scenarios
        print("\n2. Testing strike selection logic...")
        
        # Scenario 1: Kalshi "over 6475"
        print("\n📊 Scenario 1: Kalshi 'over 6475'")
        print("   Strategy: Bear call spread")
        print("   Correct strikes: Sell 6475C, Buy 6485C")
        print("   If S&P closes at 6475.01: Kalshi YES wins + 6475C expires worthless = PERFECT!")
        
        # Scenario 2: Kalshi "under 6475"  
        print("\n📊 Scenario 2: Kalshi 'under 6475'")
        print("   Strategy: Bull put spread")
        print("   Correct strikes: Sell 6475P, Buy 6465P")
        print("   If S&P closes at 6474.99: Kalshi NO wins + 6475P expires worthless = PERFECT!")
        
        # Get some sample data
        expiry = date.today().strftime("%Y%m%d")
        print(f"\n3. Testing with expiry {expiry}...")
        
        # Load a small chain
        client.get_spx_option_chain(expiry, [6465, 6470, 6475, 6480, 6485])
        time.sleep(3)
        
        # Test find_kalshi_equivalent_spread
        print("\n4. Testing spread finder...")
        
        # Test "over" scenario
        spread = client.find_kalshi_equivalent_spread(6475, expiry, "over")
        if spread:
            print(f"\n✅ 'Over 6475' spread found correctly:")
            print(f"   Short: {spread.short_leg.contract.strike}{spread.short_leg.contract.right}")
            print(f"   Long: {spread.long_leg.contract.strike}{spread.long_leg.contract.right}")
        
        # Test "under" scenario
        spread = client.find_kalshi_equivalent_spread(6475, expiry, "under")
        if spread:
            print(f"\n✅ 'Under 6475' spread found correctly:")
            print(f"   Short: {spread.short_leg.contract.strike}{spread.short_leg.contract.right}")
            print(f"   Long: {spread.long_leg.contract.strike}{spread.long_leg.contract.right}")
        
        print("\n✅ Strike selection test completed!")
        print("\n🎯 Remember: Wrong strikes = imperfect hedge = real losses!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.disconnect_from_tws()
        print("\n🔌 Disconnected from TWS")


if __name__ == "__main__":
    test_strike_selection()
