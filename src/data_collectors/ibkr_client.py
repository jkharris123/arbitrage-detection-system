#!/usr/bin/env python3
"""
FIXED IBKR TWS API Client - Using Correct ForecastEx Contract Symbols
Based on official IBKR documentation
"""

import time
import threading
from datetime import datetime
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

# IBKR API imports
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order
    import ibapi.decoder
except ImportError:
    print("⚠️ IBKR API not installed. Run: pip install ibapi")

class TWSEventClient(EWrapper, EClient):
    """
    FIXED IBKR TWS API client with correct ForecastEx contract symbols
    """
    
    def __init__(self):
        EClient.__init__(self, self)
        
        # Connection settings
        self.host = "127.0.0.1"
        self.port = 7496         # Live trading port
        self.client_id = 2       # Use different ID to avoid conflicts
        
        # Data storage
        self.market_data = {}
        self.contracts = {}
        self.positions = {}
        
        # Threading
        self.api_thread = None
        self.connected = False
        
        # Request ID management
        self.next_req_id = 1000
        
        print("🔄 FIXED TWS Event Client initialized")
    
    def connect_to_tws(self) -> bool:
        """Connect to TWS application"""
        try:
            print(f"🔌 Connecting to TWS at {self.host}:{self.port} (client_id: {self.client_id})")
            self.connect(self.host, self.port, self.client_id)
            
            # Start API thread
            self.api_thread = threading.Thread(target=self.run, daemon=True)
            self.api_thread.start()
            
            # Wait for connection
            time.sleep(2)
            
            if self.isConnected():
                print("✅ Connected to TWS successfully")
                self.connected = True
                return True
            else:
                print("❌ Failed to connect to TWS")
                return False
                
        except Exception as e:
            print(f"❌ TWS connection error: {e}")
            return False
    
    def disconnect_from_tws(self):
        """Disconnect from TWS"""
        if self.connected:
            self.disconnect()
            self.connected = False
            print("🔌 Disconnected from TWS")
    
    def nextValidId(self, orderId):
        """Receive next valid order ID"""
        super().nextValidId(orderId)
        self.next_req_id = orderId
        print(f"🔍 Next valid order ID: {orderId}")
    
    def error(self, reqId, errorCode: int, errorString: str):
        """Handle API errors"""
        if errorCode == 2104:  # Market data farm connection OK
            print("✅ Market data connection established")
        elif errorCode == 2106:  # HMDS data farm connection OK  
            print("✅ Historical data connection established")
        elif errorCode in [2158, 2159]:  # Market data warnings (can ignore)
            pass
        else:
            print(f"⚠️ TWS Error {errorCode}: {errorString} (Req ID: {reqId})")
    
    def create_forecastex_contract(self, symbol: str, strike: float, right: str, 
                                  expiry_date: str) -> Contract:
        """
        Create ForecastEx contract using CORRECT symbols from IBKR docs
        
        Args:
            symbol: Product symbol (e.g., "FF", "GCE", "EUR", "NQ")
            strike: Strike price/threshold 
            right: "C" for Yes (Call), "P" for No (Put)
            expiry_date: Format "YYYYMMDD"
        """
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"          # Options for ForecastEx
        contract.exchange = "FORECASTX"   # Correct exchange (no final E)
        contract.currency = "USD"
        contract.lastTradeDateOrContractMonth = expiry_date
        contract.right = right            # "C" = Yes, "P" = No
        contract.strike = strike
        
        return contract
    
    def search_forecastex_contracts(self) -> List[Contract]:
        """
        Search for ForecastEx contracts using KNOWN working symbols only
        We'll manually provide the contract info instead of discovery
        """
        print("🔍 Searching for ForecastEx event contracts...")
        
        # START SMALL: Use only KNOWN working symbols from your test
        # We can expand this list manually as we find more
        known_working_contracts = [
            # Global Carbon Emissions - CONFIRMED WORKING
            {"symbol": "GCE", "strike": 40500, "expiry": "20251231"},
            
            # Fed Funds - From IBKR docs (should work)
            {"symbol": "FF", "strike": 3.125, "expiry": "20241217"},
            {"symbol": "FF", "strike": 4.875, "expiry": "20241217"},
            {"symbol": "FF", "strike": 5.125, "expiry": "20241217"},
            {"symbol": "FF", "strike": 5.375, "expiry": "20241217"},
            
            # Test a few more from IBKR examples
            {"symbol": "EUR", "strike": 1.11, "expiry": "20241228"},
            {"symbol": "NQ", "strike": 19800, "expiry": "20241220"},
        ]
        
        print(f"📊 Testing {len(known_working_contracts)} known contracts...")
        
        for contract_info in known_working_contracts:
            try:
                # Test both YES and NO contracts
                for right, right_name in [("C", "Yes"), ("P", "No")]:
                    req_id = self.get_next_req_id()
                    
                    contract = self.create_forecastex_contract(
                        symbol=contract_info["symbol"],
                        strike=contract_info["strike"],
                        right=right,
                        expiry_date=contract_info["expiry"]
                    )
                    
                    print(f"📊 Testing: {contract_info['symbol']} {right_name} {contract_info['strike']}")
                    self.reqContractDetails(req_id, contract)
                    
                    time.sleep(0.5)  # Reasonable delay
                    
            except Exception as e:
                print(f"⚠️ Error testing {contract_info['symbol']}: {e}")
        
        # Wait for responses
        time.sleep(5)
        
        print(f"📊 Found {len(self.contracts)} valid contracts")
        
        # TODO: Add more contracts manually as we discover them
        print("💡 TO EXPAND: Add more contract details manually to known_working_contracts list")
        
        return list(self.contracts.values())
    
    def contractDetails(self, reqId: int, contractDetails):
        """Receive contract details"""
        contract = contractDetails.contract
        contract_key = f"{contract.symbol}_{contract.right}_{contract.strike}_{contract.lastTradeDateOrContractMonth}"
        self.contracts[contract_key] = contract
        
        right_name = "Yes" if contract.right == "C" else "No"
        print(f"✅ Found contract: {contract.symbol} {right_name} {contract.strike} - {contractDetails.longName}")
    
    def request_market_data(self, contract) -> int:
        """Request real-time market data for a contract"""
        req_id = self.get_next_req_id()
        
        right_name = "Yes" if contract.right == "C" else "No"
        print(f"📊 Requesting market data for {contract.symbol} {right_name} {contract.strike}")
        
        # Request Level I market data (bid/ask/last)
        # ForecastEx only supports Level I according to docs
        self.reqMktData(req_id, contract, "", False, False, [])
        
        return req_id
    
    def tickPrice(self, reqId, tickType, price: float, attrib):
        """Receive real-time price updates"""
        tick_types = {
            1: "bid", 2: "ask", 4: "last", 6: "high", 7: "low", 9: "close"
        }
        
        if tickType in tick_types:
            tick_name = tick_types[tickType]
            if reqId not in self.market_data:
                self.market_data[reqId] = {}
            self.market_data[reqId][tick_name] = price
            
            print(f"💰 {reqId}: {tick_name} = ${price:.3f}")
    
    def tickSize(self, reqId, tickType, size: int):
        """Receive real-time size updates"""
        size_types = {
            0: "bid_size", 3: "ask_size", 5: "last_size", 8: "volume"
        }
        
        if tickType in size_types:
            size_name = size_types[tickType]
            if reqId not in self.market_data:
                self.market_data[reqId] = {}
            self.market_data[reqId][size_name] = size
            
            print(f"📊 {reqId}: {size_name} = {size}")
    
    def place_forecastex_order(self, contract, quantity: int, 
                              limit_price: float, time_in_force: str = "DAY") -> int:
        """
        Place order for ForecastEx contract
        NOTE: Must use limit orders at ASK price for instant fill (no market orders)
        
        Args:
            contract: ForecastEx contract object
            quantity: Number of contracts (whole numbers only)
            limit_price: Limit price (use ASK price for instant fill)
            time_in_force: "DAY", "GTC", or "IOC"
        """
        order = Order()
        order.action = "BUY"                    # ForecastEx only allows BUY
        order.totalQuantity = quantity
        order.orderType = "LMT"                 # Only limit orders allowed
        order.lmtPrice = limit_price
        order.tif = time_in_force
        
        # ForecastEx specific settings
        order.outsideRth = False                # Regular hours only
        
        # Get order ID
        order_id = self.get_next_req_id()
        
        right_name = "Yes" if contract.right == "C" else "No"
        print(f"📝 Placing ForecastEx order:")
        print(f"   {order.action} {quantity} {contract.symbol} {right_name} @ ${limit_price} ({time_in_force})")
        print(f"   💡 Using limit price at ASK for instant fill (no market orders available)")
        
        try:
            self.placeOrder(order_id, contract, order)
            print(f"✅ Order submitted with ID: {order_id}")
            return order_id
        except Exception as e:
            print(f"❌ Order placement failed: {e}")
            return -1
    
    def get_market_data_for_arbitrage(self) -> List[Dict]:
        """
        Get market data for ALL available contracts (for cross-platform arbitrage)
        This just collects data - arbitrage detection happens in main system
        """
        print("📊 Collecting ForecastEx market data for cross-platform arbitrage...")
        
        # Get available contracts using FIXED symbols
        contracts = self.search_forecastex_contracts()
        
        if not contracts:
            print("❌ No contracts found - check symbols or TWS connection")
            return []
        
        market_data_list = []
        
        for contract in contracts:
            # Request market data
            req_id = self.request_market_data(contract)
            
            # Wait for data
            time.sleep(1.5)  # Increased wait time
            
            # Get market data
            data = self.market_data.get(req_id, {})
            
            if data.get('bid') and data.get('ask'):
                right_name = "Yes" if contract.right == "C" else "No"
                
                market_data_list.append({
                    'platform': 'IBKR',
                    'symbol': contract.symbol,
                    'right': right_name,
                    'strike': contract.strike,
                    'expiry': contract.lastTradeDateOrContractMonth,
                    'bid': data.get('bid', 0),
                    'ask': data.get('ask', 0),
                    'bid_size': data.get('bid_size', 0),
                    'ask_size': data.get('ask_size', 0),
                    'contract': contract,
                    'req_id': req_id,
                    'contract_name': f"{contract.symbol} {right_name} {contract.strike}",
                    # For arbitrage matching with Kalshi
                    'standardized_name': f"{contract.symbol}_{right_name}_{contract.strike}"
                })
            else:
                print(f"⚠️ No market data for {contract.symbol} {contract.right} {contract.strike}")
        
        print(f"✅ Retrieved {len(market_data_list)} ForecastEx contracts with market data")
        return market_data_list
    
    def test_all_contracts(self) -> bool:
        """
        Test getting market data for all available contracts
        This shows what's available for arbitrage with Kalshi
        """
        print(f"🧪 TESTING ALL FORECASTEX CONTRACTS")
        print("=" * 60)
        
        try:
            # Get all market data
            market_data = self.get_market_data_for_arbitrage()
            
            if not market_data:
                print("❌ No contracts with market data found")
                return False
            
            print(f"\n📊 AVAILABLE FOR CROSS-PLATFORM ARBITRAGE:")
            print(f"Found {len(market_data)} contracts with market data\n")
            
            for data in market_data:
                print(f"✅ {data['symbol']} {data['right']} {data['strike']} @ {data['expiry']}")
                print(f"   Bid: ${data['bid']:.3f} ({data['bid_size']}) | Ask: ${data['ask']:.3f} ({data['ask_size']})")
                print(f"   Spread: ${data['ask'] - data['bid']:.3f} ({((data['ask'] - data['bid']) / data['ask'] * 100):.1f}%)")
                print()
            
            print(f"🎯 READY FOR ARBITRAGE DETECTION:")
            print(f"   ✅ {len(market_data)} contracts ready")
            print(f"   ✅ Can execute limit orders at ask price")
            print(f"   ✅ Level I data sufficient for arbitrage")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    def get_next_req_id(self) -> int:
        """Get next request ID"""
        req_id = self.next_req_id
        self.next_req_id += 1
        return req_id

def test_fixed_tws_client():
    """Test the FIXED TWS client with correct contract symbols"""
    try:
        print("🚀 Testing FIXED TWS Event Client with correct symbols...")
        
        client = TWSEventClient()
        
        # Connect to TWS
        if client.connect_to_tws():
            print("✅ TWS connection successful")
            
            # Test all available contracts
            success = client.test_all_contracts()
            
            if success:
                print("\n🎉 SUCCESS: Ready for cross-platform arbitrage!")
                print("   Next step: Compare with Kalshi data")
            else:
                print("\n❌ ISSUE: No contracts available for arbitrage")
        else:
            print("❌ TWS connection failed")
        
        client.disconnect_from_tws()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_tws_client()