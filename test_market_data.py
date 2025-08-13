#!/usr/bin/env python3
"""
Test market data subscriptions and permissions
"""
import time
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

class MarketDataTest(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data_received = False
        
    def error(self, reqId, errorCode, errorString):
        print(f"Error {errorCode}: {errorString}")
        
    def tickPrice(self, reqId, tickType, price, attrib):
        self.data_received = True
        print(f"✅ Received price data: ${price}")
        
    def nextValidId(self, orderId):
        # Test with SPY stock first (simpler than options)
        contract = Contract()
        contract.symbol = "SPY"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        
        print("Testing SPY stock data...")
        self.reqMktData(1, contract, "", False, False, [])

def test_market_data():
    app = MarketDataTest()
    app.connect("127.0.0.1", 7496, 999)
    
    # Start the socket in a thread
    import threading
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    # Wait for data
    time.sleep(5)
    
    if app.data_received:
        print("\n✅ Market data working!")
    else:
        print("\n❌ No market data received")
        print("\nTo fix in TWS:")
        print("1. Go to: Account -> Trade Configuration -> Market Data")
        print("2. Check 'Enable market data for API clients'")
        print("3. Go to: Global Configuration -> API -> Settings")
        print("4. Ensure 'Download open orders on connection' is checked")
        print("5. Restart TWS after changes")
    
    app.disconnect()

if __name__ == "__main__":
    test_market_data()
