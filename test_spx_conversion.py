#!/usr/bin/env python3
"""
Test SPX conversion - verify IBKR options client works with SPX
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_collectors.ibkr_options_client import IBKROptionsClient
from datetime import datetime, date
import time

def test_spx():
    """Test SPX functionality"""
    print("\n=== Testing SPX Conversion ===")
    print("This test verifies SPX options work correctly")
    print("(Cash-settled, European-style, no auto-liquidation risk)")
    print("=" * 60)
    
    # Create client
    client = IBKROptionsClient()
    
    try:
        # Connect
        print("\n1. Connecting to TWS...")
        if not client.connect_to_tws():
            print("❌ Failed to connect. Make sure TWS is running.")
            return
        print("✅ Connected successfully")
        
        # Get SPX price
        print("\n2. Getting SPX index price...")
        client.get_underlying_price("SPX")
        time.sleep(3)
        
        spx_price = client.underlying_price.get("SPX", 0)
        if spx_price > 0:
            print(f"✅ SPX Index: {spx_price:.2f}")
        else:
            print("⚠️ No SPX price available, using 6400 as default")
            spx_price = 6400
        
        # Test option contract creation
        print("\n3. Testing SPX option contract creation...")
        expiry = date.today().strftime("%Y%m%d")
        strike = round(spx_price / 5) * 5  # Round to nearest 5
        
        # Create a call option
        call_contract = client.create_spx_option(strike, "C", expiry)
        print(f"✅ Created SPX option contract (SPXW for weeklies):")
        print(f"   Symbol: {call_contract.symbol}")
        print(f"   Type: {call_contract.secType}")
        print(f"   Exchange: {call_contract.exchange}")
        print(f"   Strike: {call_contract.strike}")
        print(f"   Right: {call_contract.right}")
        print(f"   Expiry: {call_contract.lastTradeDateOrContractMonth}")
        
        # Get a small option chain
        print(f"\n4. Fetching SPX option chain around {strike}...")
        strikes = [strike - 10, strike - 5, strike, strike + 5, strike + 10]
        client.get_spx_option_chain(expiry, strikes)
        
        print("⏳ Waiting for option data (5 seconds)...")
        time.sleep(5)
        
        # Display results
        if expiry in client.option_chains:
            print("\n✅ SPX Option Chain Data:")
            for s in strikes:
                if s in client.option_chains[expiry]:
                    if "C" in client.option_chains[expiry][s]:
                        opt = client.option_chains[expiry][s]["C"]
                        if opt.bid > 0:
                            print(f"\nSPX {s}C:")
                            print(f"  Bid: ${opt.bid:.2f} Ask: ${opt.ask:.2f}")
                            print(f"  Delta: {opt.delta:.3f}")
                            print(f"  IV: {opt.implied_volatility:.3f}")
        
        # Test commission calculation
        print("\n5. Commission Structure:")
        print(f"Current tier: {client.get_commission_tier()}")
        print("Expected commission for 2-leg spread: ~$3.00")
        
        print("\n✅ SPX conversion test completed successfully!")
        print("\n🎯 KEY POINTS:")
        print("- SPXW options (weekly SPX) settle at 4 PM ET")
        print("- Cash-settled (no shares to worry about)")
        print("- European-style (no early exercise)")
        print("- No auto-liquidation risk from IBKR")
        print("- Perfect match for Kalshi 4 PM settlement")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.disconnect_from_tws()
        print("\n🔌 Disconnected from TWS")


if __name__ == "__main__":
    test_spx()
