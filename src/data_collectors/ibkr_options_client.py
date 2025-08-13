#!/usr/bin/env python3
"""
IBKR TWS API Client for SPX Options (SPXW weeklies)
Designed for cross-asset arbitrage with Kalshi prediction markets

SPXW = Weekly SPX options with PM settlement (4:00 PM close)
- Cash-settled (no shares to worry about)
- European-style (no early exercise)
- No auto-liquidation risk from IBKR
- Perfect match for Kalshi which also settles at 4 PM

Note: IBKR automatically routes weekly expiries to SPXW
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math

# IBKR API imports
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order
    from ibapi.ticktype import TickTypeEnum
    from ibapi.execution import Execution
    from ibapi.commission_report import CommissionReport
except ImportError:
    print("⚠️ IBKR API not installed. Run: pip install ibapi")

@dataclass
class OptionData:
    """Store option contract data with Greeks"""
    contract: Contract
    bid: float = 0.0
    ask: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    last: float = 0.0
    volume: int = 0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    implied_volatility: float = 0.0
    underlying_price: float = 0.0
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.ask if self.ask > 0 else 0.0
    
    @property
    def spread(self) -> float:
        """Calculate bid-ask spread"""
        return self.ask - self.bid if self.ask > 0 and self.bid > 0 else 0.0
    
    def probability_itm(self) -> float:
        """Calculate probability of finishing in-the-money using delta as approximation"""
        # For calls, delta approximates probability of ITM
        # For puts, 1 - abs(delta) approximates probability of ITM
        if self.contract.right == "C":
            return abs(self.delta)
        else:
            return 1 - abs(self.delta)

@dataclass
class SpreadData:
    """Store vertical spread data"""
    long_leg: OptionData
    short_leg: OptionData
    
    @property
    def net_debit(self) -> float:
        """Calculate net debit for the spread"""
        return self.long_leg.ask - self.short_leg.bid
    
    @property
    def net_credit(self) -> float:
        """Calculate net credit for the spread"""
        return self.short_leg.bid - self.long_leg.ask
    
    @property
    def max_profit(self) -> float:
        """Calculate maximum profit"""
        strike_width = abs(self.short_leg.contract.strike - self.long_leg.contract.strike)
        if self.net_credit > 0:  # Credit spread
            return self.net_credit
        else:  # Debit spread
            return strike_width - self.net_debit
    
    @property
    def max_loss(self) -> float:
        """Calculate maximum loss"""
        strike_width = abs(self.short_leg.contract.strike - self.long_leg.contract.strike)
        if self.net_credit > 0:  # Credit spread
            return strike_width - self.net_credit
        else:  # Debit spread
            return self.net_debit
    
    def probability_of_profit(self) -> float:
        """Estimate probability of profit based on Greeks"""
        # Simplified calculation using delta
        if self.net_credit > 0:  # Credit spread
            # For credit spreads, we profit if short leg expires OTM
            return 1 - self.short_leg.probability_itm()
        else:  # Debit spread
            # For debit spreads, we profit if long leg expires ITM
            return self.long_leg.probability_itm()

class IBKROptionsClient(EWrapper, EClient):
    """
    IBKR TWS API client for SPX options trading - Cross-asset arbitrage focus
    Uses SPX (cash-settled, European-style) to avoid auto-liquidation risk
    """
    
    def __init__(self):
        EClient.__init__(self, self)
        
        # Connection settings
        self.host = "127.0.0.1"
        self.port = 7496         # TWS live trading port (7497 for paper)
        self.client_id = 3       # Different ID to avoid conflicts
        
        # Data storage
        self.option_chains = {}  # {expiry: {strike: {right: OptionData}}}
        self.underlying_price = {}  # {symbol: price}
        self.req_id_to_option = {}  # Map request IDs to options
        self.commissions = {}  # {execId: commission_amount}
        
        # Commission tracking
        self.monthly_volume = 0
        self.monthly_commissions = 0.0
        
        # Threading
        self.api_thread = None
        self.connected = False
        self.data_ready = threading.Event()
        
        # Request ID management
        self.next_req_id = 2000
        
        print("🎯 IBKR Options Client initialized for cross-asset arbitrage")
    
    def connect_to_tws(self) -> bool:
        """Connect to TWS (Interactive Brokers Trader Workstation)"""
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
                
                # Request market data type (live quotes for production)
                self.reqMarketDataType(1)  # 1 = Live, 3 = Delayed
                
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
        # Ignore common non-critical errors
        if errorCode in [2104, 2106, 2107, 2108, 2158, 2159]:
            return
        elif errorCode == 200:  # No security definition found
            print(f"⚠️ No contract found for request {reqId}")
        else:
            print(f"⚠️ TWS Error {errorCode}: {errorString} (Req ID: {reqId})")
    
    def create_spx_option(self, strike: float, right: str, expiry: str) -> Contract:
        """
        Create SPXW option contract (weekly SPX with PM settlement)
        SPXW settles at 4 PM ET, matching Kalshi exactly
        
        Args:
            strike: Strike price (e.g., 6400.0)
            right: "C" for Call, "P" for Put
            expiry: Format "YYYYMMDD"
        """
        contract = Contract()
        # Use SPX symbol - IBKR automatically routes to SPXW for weeklies
        contract.symbol = "SPX"
        contract.secType = "OPT"
        contract.exchange = "SMART"  # Let IBKR smart route to best exchange
        contract.currency = "USD"
        contract.lastTradeDateOrContractMonth = expiry
        contract.strike = strike
        contract.right = right
        contract.multiplier = "100"
        # Note: SPXW (PM settlement) is automatically selected for weekly expiries
        # Only monthly expiries get AM settlement SPX
        
        return contract
    
    # Keep old method for compatibility but use SPXW
    
    def get_spx_option_chain(self, expiry: str, strikes: List[float] = None) -> bool:
        """
        Get SPXW (weekly SPX) option chain for specific expiry
        SPXW = PM settlement (4:00 PM), perfect for Kalshi arbitrage
        
        Args:
            expiry: Format "YYYYMMDD"
            strikes: List of strikes to get (None = all liquid strikes)
        """
        print(f"📊 Fetching SPXW option chain for {expiry}")
        print(f"   (Weekly SPX with 4 PM settlement)")
        
        # First get underlying SPX price
        self.get_underlying_price("SPX")
        time.sleep(1)
        
        current_spx = self.underlying_price.get("SPX", 6400.0)
        
        # If no strikes specified, get ATM +/- 100 points
        # SPX strikes: 5-point increments near ATM, 10-point further out
        if strikes is None:
            center = round(current_spx / 5) * 5  # Round to nearest 5
            strikes = []
            # Near ATM: 5-point increments (+/- 50 points)
            for i in range(-10, 11):
                strikes.append(center + i*5)
            # Further out: 10-point increments
            for i in [-7, -6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7]:
                strikes.append(center + i*10 + (50 if i > 0 else -50))
        
        # Initialize storage for this expiry
        if expiry not in self.option_chains:
            self.option_chains[expiry] = {}
        
        # Request data for each strike and type
        for strike in strikes:
            if strike not in self.option_chains[expiry]:
                self.option_chains[expiry][strike] = {}
            
            for right in ["C", "P"]:
                try:
                    contract = self.create_spx_option(strike, right, expiry)
                    option_data = OptionData(contract=contract)
                    
                    # Store in chain
                    self.option_chains[expiry][strike][right] = option_data
                    
                    # Request market data
                    req_id = self.get_next_req_id()
                    self.req_id_to_option[req_id] = option_data
                    
                    # Request market data and Greeks
                    self.reqMktData(req_id, contract, "", False, False, [])
                    
                    # Small delay to avoid overwhelming API
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"⚠️ Error requesting {strike} {right}: {e}")
        
        print(f"✅ Requested data for {len(strikes)} strikes")
        return True
    
    # Removed get_spy_option_chain - use get_spx_option_chain directly
    
    def get_underlying_price(self, symbol: str = "SPX"):
        """Get current price of underlying (SPX is an index)"""
        contract = Contract()
        contract.symbol = symbol
        if symbol == "SPX":
            contract.secType = "IND"  # Index for SPX
            contract.exchange = "CBOE"
        else:
            contract.secType = "STK"  # Stock for SPY
            contract.exchange = "SMART"
        contract.currency = "USD"
        
        req_id = self.get_next_req_id()
        self.req_id_to_option[req_id] = symbol  # Special marker for underlying
        
        self.reqMktData(req_id, contract, "", False, False, [])
        
    def tickPrice(self, reqId, tickType, price: float, attrib):
        """Receive real-time price updates"""
        if reqId not in self.req_id_to_option:
            return
        
        data = self.req_id_to_option[reqId]
        
        # Check if this is underlying price
        if isinstance(data, str):
            if tickType == TickTypeEnum.LAST:
                self.underlying_price[data] = price
                print(f"📈 {data} price: ${price:.2f}")
            return
        
        # Option price updates
        if tickType == TickTypeEnum.BID:
            data.bid = price
        elif tickType == TickTypeEnum.ASK:
            data.ask = price
        elif tickType == TickTypeEnum.LAST:
            data.last = price
    
    def tickSize(self, reqId, tickType, size: int):
        """Receive real-time size updates"""
        if reqId not in self.req_id_to_option:
            return
            
        data = self.req_id_to_option[reqId]
        
        if isinstance(data, str):  # Underlying
            return
        
        if tickType == TickTypeEnum.BID_SIZE:
            data.bid_size = size
        elif tickType == TickTypeEnum.ASK_SIZE:
            data.ask_size = size
        elif tickType == TickTypeEnum.VOLUME:
            data.volume = size
    
    def tickOptionComputation(self, reqId, tickType, tickAttrib, impliedVol, 
                            delta, optPrice, pvDividend, gamma, vega, theta, undPrice):
        """Receive option Greeks"""
        if reqId not in self.req_id_to_option:
            return
            
        data = self.req_id_to_option[reqId]
        
        if isinstance(data, str):  # Underlying
            return
        
        # Update Greeks
        if tickType in [TickTypeEnum.BID_OPTION_COMPUTATION, 
                       TickTypeEnum.ASK_OPTION_COMPUTATION,
                       TickTypeEnum.LAST_OPTION_COMPUTATION]:
            if delta is not None and delta != -2.0:  # -2 means not computed
                data.delta = delta
            if gamma is not None and gamma != -2.0:
                data.gamma = gamma
            if theta is not None and theta != -2.0:
                data.theta = theta
            if vega is not None and vega != -2.0:
                data.vega = vega
            if impliedVol is not None and impliedVol != -2.0:
                data.implied_volatility = impliedVol
            if undPrice is not None and undPrice != -1.0:
                data.underlying_price = undPrice
    
    def find_kalshi_equivalent_spread(self, s_p_level: float, expiry: str, 
                                    kalshi_side: str) -> Optional[SpreadData]:
        """
        Find SPXW option spread equivalent to Kalshi S&P contract
        
        CRITICAL: Short leg must be AT the Kalshi strike level!
        - For "over X": Sell X call, Buy (X+10) call (bear call spread)
        - For "under X": Sell X put, Buy (X-10) put (bull put spread)
        
        Args:
            s_p_level: S&P level from Kalshi (e.g., 6475)
            expiry: Option expiry date "YYYYMMDD"
            kalshi_side: "over" or "under"
        """
        # SPX uses same levels as S&P 500 (no conversion needed)
        spx_level = s_p_level
        
        if expiry not in self.option_chains:
            print(f"⚠️ No option chain loaded for {expiry}")
            return None
        
        # Determine spread type and strikes based on Kalshi side
        if kalshi_side == "under":
            # Bull put spread: Sell strike AT level, Buy 10 points below
            short_strike = spx_level
            long_strike = spx_level - 10
            right = "P"
            spread_type = "Bull Put Spread"
        else:  # "over"
            # Bear call spread: Sell strike AT level, Buy 10 points above
            short_strike = spx_level
            long_strike = spx_level + 10
            right = "C"
            spread_type = "Bear Call Spread"
        
        # Verify strikes exist in chain
        if (short_strike not in self.option_chains[expiry] or 
            long_strike not in self.option_chains[expiry]):
            print(f"⚠️ Required strikes {short_strike}/{long_strike} not available")
            return None
        
        # Get option data
        short_option = self.option_chains[expiry][short_strike].get(right)
        long_option = self.option_chains[expiry][long_strike].get(right)
        
        if not short_option or not long_option:
            return None
        
        print(f"✅ Found {spread_type}: Sell {short_strike}{right}, Buy {long_strike}{right}")
        
        # Create spread data
        spread = SpreadData(long_leg=long_option, short_leg=short_option)
        
        return spread
    
    def calculate_kalshi_arbitrage(self, kalshi_price: float, kalshi_side: str,
                                 s_p_level: float, expiry: str) -> Dict:
        """
        Calculate arbitrage opportunity between Kalshi and options
        
        Args:
            kalshi_price: Price of Kalshi contract (0-1)
            kalshi_side: "over" or "under"
            s_p_level: S&P level threshold
            expiry: Options expiry "YYYYMMDD"
        """
        # Find equivalent spread based on Kalshi position
        spread = self.find_kalshi_equivalent_spread(s_p_level, expiry, kalshi_side)
        
        if not spread:
            return {"error": "Could not find matching option spread"}
        
        # Calculate probabilities
        kalshi_prob = kalshi_price
        options_prob = spread.probability_of_profit()
        prob_diff = abs(kalshi_prob - options_prob)
        
        # Calculate costs
        # SPX has $100 multiplier, so 1 SPX contract = $100 per point move
        kalshi_contracts = 100  # 100 Kalshi contracts = $100 payout
        spx_contracts = 1      # 1 SPX spread to match the $100 exposure
        
        kalshi_cost = kalshi_price * kalshi_contracts
        kalshi_fee = self._estimate_kalshi_fee(kalshi_price, kalshi_contracts)
        
        # Options cost (1 SPX spread = $100 per point)
        options_credit = spread.net_credit * 100  # SPX multiplier
        options_commission = 3.0  # ~$3 for 2-leg spread
        
        # Total investment
        total_cost = kalshi_cost + kalshi_fee - options_credit + options_commission
        
        # Guaranteed payout (if positions offset correctly)
        guaranteed_payout = 100.0  # $100 for 100 Kalshi contracts
        
        # Net profit
        net_profit = guaranteed_payout - total_cost
        
        return {
            "kalshi_side": kalshi_side,
            "kalshi_price": kalshi_price,
            "kalshi_probability": kalshi_prob * 100,
            "options_spread": f"{spread.short_leg.contract.strike}/{spread.long_leg.contract.strike}",
            "options_probability": options_prob * 100,
            "probability_difference": prob_diff * 100,
            "kalshi_cost": kalshi_cost,
            "kalshi_fee": kalshi_fee,
            "options_credit": options_credit,
            "options_commission": options_commission,
            "total_investment": total_cost,
            "guaranteed_payout": guaranteed_payout,
            "net_profit": net_profit,
            "profitable": net_profit > 0,
            "spread_data": spread
        }
    
    def _estimate_kalshi_fee(self, price: float, contracts: int) -> float:
        """Estimate Kalshi fees"""
        # Kalshi fee formula: round_up(0.07 * C * P * (1-P))
        fee_raw = 0.07 * contracts * price * (1 - price)
        return max(0.01, round(fee_raw * 100) / 100)  # Round up to nearest cent
    
    def place_option_spread(self, spread: SpreadData, quantity: int, 
                          limit_credit: float = None) -> List[int]:
        """
        Place a vertical spread order
        
        Args:
            spread: SpreadData with long and short legs
            quantity: Number of spreads
            limit_credit: Minimum credit to receive (None = market)
        """
        orders = []
        
        # Create orders for both legs
        # Short leg
        short_order = Order()
        short_order.action = "SELL"
        short_order.totalQuantity = quantity
        short_order.orderType = "LMT" if limit_credit else "MKT"
        if limit_credit:
            short_order.lmtPrice = spread.short_leg.bid  # Sell at bid
        
        # Long leg
        long_order = Order()
        long_order.action = "BUY"
        long_order.totalQuantity = quantity
        long_order.orderType = "LMT" if limit_credit else "MKT"
        if limit_credit:
            long_order.lmtPrice = spread.long_leg.ask  # Buy at ask
        
        # Place orders
        order_ids = []
        
        try:
            # Place short leg
            short_id = self.get_next_req_id()
            self.placeOrder(short_id, spread.short_leg.contract, short_order)
            order_ids.append(short_id)
            print(f"📝 Placed short leg: SELL {quantity} {spread.short_leg.contract.strike}{spread.short_leg.contract.right}")
            
            # Place long leg
            long_id = self.get_next_req_id()
            self.placeOrder(long_id, spread.long_leg.contract, long_order)
            order_ids.append(long_id)
            print(f"📝 Placed long leg: BUY {quantity} {spread.long_leg.contract.strike}{spread.long_leg.contract.right}")
            
            return order_ids
            
        except Exception as e:
            print(f"❌ Error placing spread: {e}")
            return []
    
    def commissionReport(self, commissionReport: CommissionReport):
        """Receive commission reports"""
        self.commissions[commissionReport.execId] = commissionReport.commission
        self.monthly_commissions += commissionReport.commission
        print(f"💰 Commission: ${commissionReport.commission:.2f} for execution {commissionReport.execId}")
    
    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        """Receive execution details"""
        print(f"✅ Execution: {execution.side} {execution.shares} {contract.symbol} @ ${execution.price}")
        self.monthly_volume += execution.shares
    
    def get_commission_tier(self) -> str:
        """Get current commission tier based on monthly volume"""
        if self.monthly_volume >= 100_001:
            return "Tier 4: $0.15/contract"
        elif self.monthly_volume >= 50_001:
            return "Tier 3: $0.25/contract"
        elif self.monthly_volume >= 10_001:
            return "Tier 2: $0.50/contract"
        else:
            return "Tier 1: $0.65/contract"
    
    def get_next_req_id(self) -> int:
        """Get next request ID"""
        req_id = self.next_req_id
        self.next_req_id += 1
        return req_id


def test_options_client():
    """Test the IBKR options client for cross-asset arbitrage"""
    print("🚀 Testing IBKR Options Client for Cross-Asset Arbitrage")
    print("=" * 60)
    
    client = IBKROptionsClient()
    
    try:
        # Connect to TWS
        if not client.connect_to_tws():
            print("❌ Failed to connect to TWS")
            return
        
        # Get today's date for 0DTE options
        from datetime import date
        today = date.today()
        expiry = today.strftime("%Y%m%d")
        
        print(f"\n📅 Testing with {expiry} expiry (0DTE)")
        
        # Get option chain around current SPX level
        print("\n📊 Fetching SPX option chain...")
        client.get_spx_option_chain(expiry)
        
        # Wait for data
        print("⏳ Waiting for market data...")
        time.sleep(5)
        
        # Display some data
        if expiry in client.option_chains:
            print(f"\n✅ Retrieved option chain with {len(client.option_chains[expiry])} strikes")
            
            # Show a few strikes
            strikes = sorted(client.option_chains[expiry].keys())[:5]
            for strike in strikes:
                if "C" in client.option_chains[expiry][strike]:
                    call = client.option_chains[expiry][strike]["C"]
                    print(f"\nSPX {strike}C: Bid ${call.bid:.2f} Ask ${call.ask:.2f}")
                    print(f"   Delta: {call.delta:.3f} | IV: {call.implied_volatility:.3f}")
        
        # Test arbitrage calculation
        print("\n🎯 Testing Kalshi Arbitrage Calculation...")
        print("Example: Kalshi S&P under 6400 @ $0.64")
        
        arb_result = client.calculate_kalshi_arbitrage(
            kalshi_price=0.64,
            kalshi_side="under",
            s_p_level=6400,
            expiry=expiry
        )
        
        if "error" not in arb_result:
            print(f"\n💰 ARBITRAGE ANALYSIS:")
            print(f"   Kalshi: {arb_result['kalshi_side']} @ {arb_result['kalshi_probability']:.1f}%")
            print(f"   Options: {arb_result['options_spread']} spread @ {arb_result['options_probability']:.1f}%")
            print(f"   Probability Difference: {arb_result['probability_difference']:.1f}%")
            print(f"   Net Profit: ${arb_result['net_profit']:.2f}")
            print(f"   Profitable: {'YES' if arb_result['profitable'] else 'NO'}")
        
        # Check commission tier
        print(f"\n📊 Commission Tier: {client.get_commission_tier()}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.disconnect_from_tws()
        print("\n✅ Test complete")


if __name__ == "__main__":
    test_options_client()
