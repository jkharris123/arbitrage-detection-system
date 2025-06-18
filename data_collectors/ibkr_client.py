#!/usr/bin/env python3
"""
IBKR TWS API Client for Event Contracts
Replaces the web scraping stub with real API integration
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
    from ibapi.common import TickerId, OrderId
    import ibapi.decoder
except ImportError:
    print("⚠️ IBKR API not installed. Run: pip install ibapi")

# Import your existing data structures
try:
    from main import MarketData, OrderBook, OrderBookLevel
except ImportError:
    print("⚠️ Could not import MarketData structures")

class TWSEventClient(EWrapper, EClient):
    """
    IBKR TWS API client specifically for Event/Forecast contracts
    Provides real-time market data and order execution
    """
    
    def __init__(self):
        EClient.__init__(self, self)
        
        # Connection settings for LIVE TRADING
        self.host = "127.0.0.1"  # localhost
        self.port = 7496         # TWS LIVE trading (7497 for paper, 4000 for IB Gateway live)
        self.client_id = 1       # Must be unique if multiple API connections
        
        # Data storage
        self.market_data = {}
        self.order_books = {}
        self.contracts = {}
        self.positions = {}
        
        # Threading
        self.api_thread = None
        self.connected = False
        
        # Request ID management
        self.next_req_id = 1000
        
        print("🔄 TWS Event Client initialized")
    
    def connect_to_tws(self) -> bool:
        """Connect to TWS application"""
        try:
            print(f"🔌 Connecting to TWS at {self.host}:{self.port}")
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
    
    def nextValidId(self, orderId: OrderId):
        """Receive next valid order ID"""
        super().nextValidId(orderId)
        self.next_req_id = orderId
        print(f"🔍 Next valid order ID: {orderId}")
    
    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        """Handle API errors"""
        if errorCode == 2104:  # Market data farm connection OK
            print("✅ Market data connection established")
        elif errorCode == 2106:  # HMDS data farm connection OK  
            print("✅ Historical data connection established")
        elif errorCode in [2158, 2159]:  # Market data warnings (can ignore)
            pass
        else:
            print(f"⚠️ TWS Error {errorCode}: {errorString} (Req ID: {reqId})")
    
    def create_event_contract(self, symbol: str, exchange: str = "NASDAQ") -> Contract:
        """
        Create contract for event/forecast trading based on IBKR documentation
        
        Args:
            symbol: Contract symbol (e.g., "USELX24", "CPI0324", "FED0324")
            exchange: Exchange (NASDAQ for most event contracts)
        """
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "CONTFUT"  # Contract futures for event contracts
        contract.exchange = exchange
        contract.currency = "USD"
        
        # Event contracts often need lastTradeDateOrContractMonth
        # Will be set when we get contract details
        
        return contract
    
    def search_event_contracts(self, search_term: str = "") -> List[Contract]:
        """
        Search for available event contracts using proper IBKR methods
        Based on IBKR event contract documentation
        """
        print(f"🔍 Searching for event contracts: {search_term or 'all'}")
        
        # Common event contract patterns from IBKR docs
        event_symbols = [
            "USELX24",    # US Election 2024
            "CPI",        # CPI data
            "FED",        # Fed meetings
            "NFP",        # Non-farm payrolls
            "GDP",        # GDP data
            "FOMC"        # FOMC meetings
        ]
        
        found_contracts = []
        
        for symbol in event_symbols:
            if not search_term or search_term.upper() in symbol.upper():
                try:
                    req_id = self.get_next_req_id()
                    
                    # Create contract for search
                    contract = Contract()
                    contract.symbol = symbol
                    contract.secType = "CONTFUT"
                    contract.exchange = "NASDAQ"
                    contract.currency = "USD"
                    
                    print(f"📊 Requesting details for {symbol}")
                    self.reqContractDetails(req_id, contract)
                    
                    # Small delay between requests
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"⚠️ Error searching {symbol}: {e}")
        
        # Wait for responses
        time.sleep(3)
        
        return list(self.contracts.values())
    
    def contractDetails(self, reqId: int, contractDetails):
        """Receive contract details"""
        contract = contractDetails.contract
        self.contracts[contract.symbol] = contract
        
        print(f"📊 Found contract: {contract.symbol} - {contractDetails.longName}")
    
    def request_market_data(self, contract: Contract) -> int:
        """Request real-time market data for a contract"""
        req_id = self.get_next_req_id()
        
        print(f"📊 Requesting market data for {contract.symbol}")
        
        # Request market data
        self.reqMktData(req_id, contract, "", False, False, [])
        
        # Request market depth (order book)
        depth_req_id = self.get_next_req_id()
        self.reqMktDepth(depth_req_id, contract, 10, False, [])
        
        return req_id
    
    def tickPrice(self, reqId: TickerId, tickType, price: float, attrib):
        """Receive real-time price updates"""
        # Map tick types to readable names
        tick_types = {
            1: "bid", 2: "ask", 4: "last", 6: "high", 7: "low", 9: "close"
        }
        
        if tickType in tick_types:
            tick_name = tick_types[tickType]
            if reqId not in self.market_data:
                self.market_data[reqId] = {}
            self.market_data[reqId][tick_name] = price
            
            print(f"💰 {reqId}: {tick_name} = ${price:.3f}")
    
    def tickSize(self, reqId: TickerId, tickType, size: int):
        """Receive real-time size updates"""
        size_types = {
            0: "bid_size", 3: "ask_size", 5: "last_size", 8: "volume"
        }
        
        if tickType in size_types:
            size_name = size_types[tickType]
            if reqId not in self.market_data:
                self.market_data[reqId] = {}
            self.market_data[reqId][size_name] = size
    
    def updateMktDepth(self, reqId: TickerId, position: int, operation: int, 
                      side: int, price: float, size: int):
        """Receive order book depth updates"""
        if reqId not in self.order_books:
            self.order_books[reqId] = {"bids": {}, "asks": {}}
        
        # side: 0 = ask, 1 = bid
        book_side = "bids" if side == 1 else "asks"
        
        if operation == 0:  # Insert
            self.order_books[reqId][book_side][position] = {"price": price, "size": size}
        elif operation == 1:  # Update
            if position in self.order_books[reqId][book_side]:
                self.order_books[reqId][book_side][position]["size"] = size
        elif operation == 2:  # Delete
            if position in self.order_books[reqId][book_side]:
                del self.order_books[reqId][book_side][position]
    
    def get_market_data(self) -> List[MarketData]:
        """
        Get current market data for all active event contracts
        Returns MarketData objects compatible with your existing system
        """
        if not self.connected:
            print("⚠️ Not connected to TWS")
            return []
        
        print("📊 Fetching IBKR event contract data...")
        
        # Search for common event contracts
        search_terms = ["USELX", "CPI", "FED", "SPX", "NDAQ"]  # Common patterns
        
        market_data_list = []
        
        for term in search_terms:
            contracts = self.search_event_contracts(term)
            
            for contract in contracts[:5]:  # Limit for testing
                req_id = self.request_market_data(contract)
                
                # Wait for data
                time.sleep(1)
                
                # Convert to MarketData format
                market_data = self._convert_to_market_data(contract, req_id)
                if market_data:
                    market_data_list.append(market_data)
        
        print(f"✅ Retrieved {len(market_data_list)} IBKR event contracts")
        return market_data_list
    
    def _convert_to_market_data(self, contract: Contract, req_id: int) -> Optional[MarketData]:
        """Convert TWS data to your MarketData format"""
        try:
            # Get price data
            prices = self.market_data.get(req_id, {})
            
            bid_price = prices.get("bid", 0.0)
            ask_price = prices.get("ask", 0.0)
            bid_size = prices.get("bid_size", 0)
            ask_size = prices.get("ask_size", 0)
            
            # Get order book
            book_data = self.order_books.get(req_id, {"bids": {}, "asks": {}})
            
            # Convert order book to your format
            bids = []
            asks = []
            
            # Sort and convert bids (highest first)
            for pos, data in sorted(book_data["bids"].items()):
                bids.append(OrderBookLevel(data["price"], data["size"]))
            
            # Sort and convert asks (lowest first)  
            for pos, data in sorted(book_data["asks"].items()):
                asks.append(OrderBookLevel(data["price"], data["size"]))
            
            # Create OrderBook
            order_book = OrderBook(
                bids=sorted(bids, key=lambda x: x.price, reverse=True),
                asks=sorted(asks, key=lambda x: x.price),
                timestamp=datetime.now()
            )
            
            # Create MarketData
            return MarketData(
                platform="IBKR",
                contract_name=f"{contract.symbol}",
                order_book=order_book,
                last_trade_price=prices.get("last")
            )
            
        except Exception as e:
            print(f"⚠️ Error converting market data: {e}")
            return None
    
    def place_event_order(self, contract: Contract, action: str, quantity: int, 
                         price: float = None, order_type: str = "LMT") -> int:
        """
        Place an order for event contract with proper event trading parameters
        
        Args:
            contract: Event contract
            action: "BUY" or "SELL"
            quantity: Number of contracts
            price: Limit price (required for event contracts)
            order_type: "LMT" (limit) or "MKT" (market) - LMT recommended for events
        """
        if not price and order_type == "LMT":
            raise ValueError("Limit price required for limit orders")
        
        order = Order()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = order_type
        
        # Event contracts typically require limit orders
        if order_type == "LMT":
            order.lmtPrice = price
        
        # Event contract specific settings
        order.timeInForce = "GTC"  # Good till cancelled
        order.outsideRth = False   # Regular trading hours only
        
        # Get order ID
        order_id = self.get_next_req_id()
        
        print(f"📝 Placing event order: {action} {quantity} {contract.symbol} @ ${price} ({order_type})")
        
        try:
            self.placeOrder(order_id, contract, order)
            return order_id
        except Exception as e:
            print(f"❌ Order placement failed: {e}")
            return -1
    
    def get_next_req_id(self) -> int:
        """Get next request ID"""
        req_id = self.next_req_id
        self.next_req_id += 1
        return req_id

def test_tws_client():
    """Test TWS API connection and event contract data"""
    try:
        print("🧪 Testing TWS Event Client...")
        
        client = TWSEventClient()
        
        # Connect to TWS
        if client.connect_to_tws():
            print("✅ TWS connection successful")
            
            # Test market data retrieval
            market_data = client.get_market_data()
            
            print(f"📊 Retrieved {len(market_data)} contracts")
            
            for data in market_data[:3]:
                print(f"   {data.contract_name}: ${data.bid_price:.3f} / ${data.ask_price:.3f}")
            
        else:
            print("❌ TWS connection failed")
            print("   Make sure TWS is running and API is enabled")
            print("   Go to TWS -> Configure -> API -> Enable ActiveX and Socket Clients")
        
        client.disconnect_from_tws()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_tws_client()