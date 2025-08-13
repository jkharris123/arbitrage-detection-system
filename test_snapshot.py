#!/usr/bin/env python3
"""
Test snapshot data (works after hours)
"""
import time
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

class SnapshotTest(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        
    def error(self, reqId, errorCode, errorString):
        if errorCode not in [2104, 2106, 2158]:  # Ignore connection messages
            print(f"Error {errorCode}: {errorString}")
            
    def tickPrice(self, reqId, tickType, price, attrib):
        tick_names = {1: "Bid", 2: "Ask", 4: "Last", 6: "High", 7: "Low", 9: "Close"}
        if tickType in tick_names:
            print(f"✅ {tick_names[tickType]}: ${price:.2f}")
            
    def tickSnapshotEnd(self, reqId):
        print("✅ Snapshot complete")
        self.disconnect()
        
    def nextValidId(self, orderId):
        # Request snapshot data for SPY
        contract = Contract()
        contract.symbol = "SPY"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        
        print("Requesting SPY snapshot data...")
        # Last parameter True = snapshot
        self.reqMktData(1, contract, "", True, False, [])

def test_snapshot():
    print("🔍 Testing Snapshot Data (works after hours)")
    print("=" * 50)
    
    app = SnapshotTest()
    app.connect("127.0.0.1", 7496, 998)
    
    # Run the client
    app.run()

if __name__ == "__main__":
    test_snapshot()
