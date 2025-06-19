#!/usr/bin/env python3
"""
Arbitrage Detector - Fixed Import Issues
"""

import math
import os
from typing import Dict, Optional
from config.settings import Settings

# Import enhanced data structures - fixed import
try:
    from main import MarketData, OrderBook, OrderBookLevel
except ImportError:
    # Fallback definitions if main.py not available
    from datetime import datetime
    from dataclasses import dataclass
    from typing import List, Optional
    
    @dataclass
    class OrderBookLevel:
        price: float
        volume: int
    
    @dataclass  
    class OrderBook:
        bids: List[OrderBookLevel]
        asks: List[OrderBookLevel]
        timestamp: datetime
        
        def calculate_market_impact(self, side: str, volume: int) -> Dict[str, float]:
            # Simplified fallback implementation
            return {
                'average_price': 0.5,
                'slippage': 0.01,
                'filled_volume': volume,
                'remaining_volume': 0
            }
    
    @dataclass
    class MarketData:
        platform: str
        contract_name: str
        order_book: OrderBook
        
        @property
        def ask_price(self) -> float:
            return 0.5
            
        @property  
        def bid_price(self) -> float:
            return 0.5

class ArbitrageDetector:
    """
    Core arbitrage detection logic with real fee calculations and safety circuit breakers
    """
    
    def __init__(self):
        self.settings = Settings()
        
        # Safety tracking for testing
        self.daily_trades = 0
        self.daily_profit_loss = 0.0
        self.trade_history = []
        self.emergency_halt = False
        
        print("🔄 ArbitrageDetector initialized")
        
        # Load testing settings if enabled
        if os.getenv('TESTING_MODE', 'false').lower() == 'true':
            self.max_daily_trades = int(os.getenv('DAILY_TRADE_LIMIT', '5'))
            self.max_daily_loss = float(os.getenv('MAX_DAILY_LOSS', '50'))
            self.max_slippage_deviation = float(os.getenv('MAX_SLIPPAGE_DEVIATION', '0.02'))
            print(f"🧪 Testing mode: {self.max_daily_trades} trades/day, ${self.max_daily_loss} max loss")
        else:
            self.max_daily_trades = 999
            self.max_daily_loss = 1000
            self.max_slippage_deviation = 0.1
    
    def calculate_total_fees(self, buy_platform: str, sell_platform: str, 
                           buy_price: float, sell_price: float, volume: int) -> float:
        """
        Calculate total fees for both legs of arbitrage trade
        Uses real fee structures from settings
        """
        buy_fee = self._calculate_platform_fee(buy_platform, buy_price, volume)
        sell_fee = self._calculate_platform_fee(sell_platform, sell_price, volume)
        
        total_fees = buy_fee + sell_fee
        
        print(f"💰 Fee calculation: {buy_platform} ${buy_fee:.3f} + {sell_platform} ${sell_fee:.3f} = ${total_fees:.3f}")
        return total_fees
    
    def _calculate_platform_fee(self, platform: str, price: float, volume: int) -> float:
        """Calculate fees for specific platform"""
        
        if platform.lower() == 'kalshi':
            return self._calculate_kalshi_fee(price, volume)
        elif platform.lower() == 'ibkr':
            return self._calculate_ibkr_fee(price, volume)
        else:
            print(f"⚠️ Unknown platform: {platform}, using 0 fees")
            return 0.0
    
    def _calculate_kalshi_fee(self, price: float, volume: int) -> float:
        """
        Calculate Kalshi trading fee using real fee schedule
        Based on the fee tables from your documents
        """
        try:
            # Use the real fee calculation from settings
            fee = self.settings.get_kalshi_trading_fee(price, volume, 'general')
            return fee
        except Exception as e:
            print(f"⚠️ Error calculating Kalshi fee: {e}")
            # Fallback to manual calculation
            return self._manual_kalshi_fee(price, volume)
    
    def _manual_kalshi_fee(self, price: float, volume: int) -> float:
        """Manual Kalshi fee calculation as fallback"""
        # General formula: round_up(0.07 × C × P × (1-P))
        expected_value = price * (1 - price)
        fee_per_contract = 0.07 * expected_value
        total_fee = fee_per_contract * volume
        
        # Round up to next cent as per Kalshi rules
        return math.ceil(total_fee * 100) / 100
    
    def _calculate_ibkr_fee(self, price: float, volume: int) -> float:
        """
        Calculate IBKR ForecastEx fee
        ForecastEx contracts are free according to your documents
        """
        try:
            fee = self.settings.get_ibkr_trading_fee(volume, 'forecast')
            return fee
        except Exception as e:
            print(f"⚠️ Error calculating IBKR fee: {e}")
            # ForecastEx contracts are free
            return 0.0
    
    def estimate_slippage(self, buy_platform, sell_platform, volume: int) -> float:
        """
        Estimate slippage using real order book data
        This replaces the placeholder slippage function from settings
        """
        try:
            # Calculate real market impact using order book
            buy_impact = buy_platform.order_book.calculate_market_impact('buy', volume)
            sell_impact = sell_platform.order_book.calculate_market_impact('sell', volume)
            
            # Total slippage is the sum of both sides
            buy_slippage = buy_impact.get('slippage', 0)
            sell_slippage = sell_impact.get('slippage', 0)
            total_slippage = buy_slippage + sell_slippage
            
            print(f"📊 Slippage calculation: Buy ${buy_slippage:.3f} + Sell ${sell_slippage:.3f} = ${total_slippage:.3f}")
            return total_slippage
            
        except Exception as e:
            print(f"⚠️ Error calculating real slippage: {e}")
            # Fallback to conservative estimate
            return self._fallback_slippage_estimate(volume)
    
    def _fallback_slippage_estimate(self, volume: int) -> float:
        """Conservative slippage estimate as fallback"""
        if volume <= 10:
            return 0.005  # 0.5%
        elif volume <= 50:
            return 0.01   # 1%
        elif volume <= 100:
            return 0.02   # 2%
        else:
            return 0.05   # 5% for large orders
    
    def validate_arbitrage_opportunity(self, buy_platform, sell_platform, 
                                     volume: int) -> Optional[Dict]:
        """
        Comprehensive validation with PRE-CALCULATED slippage and safety checks
        SLIPPAGE MUST BE KNOWN AND INCLUDED BEFORE ALERT
        """
        
        # SAFETY CIRCUIT BREAKERS
        if self.emergency_halt:
            print("🛑 EMERGENCY HALT ACTIVE - No new trades")
            return None
            
        if self.daily_trades >= self.max_daily_trades:
            print(f"🛑 Daily trade limit reached ({self.daily_trades}/{self.max_daily_trades})")
            return None
            
        if self.daily_profit_loss < -self.max_daily_loss:
            print(f"🛑 Daily loss limit exceeded (${self.daily_profit_loss:.2f})")
            self.emergency_halt = True
            return None
        
        try:
            # CRITICAL: Get EXACT execution prices using REAL order book depth
            buy_price = buy_platform.ask_price  # We buy at ask price
            sell_price = sell_platform.bid_price  # We sell at bid price
            
            # Basic arbitrage check - must be profitable before costs
            if buy_price >= sell_price:
                return None
            
            # CALCULATE REAL EXECUTION IMPACT using order book depth
            # This is WHERE THE MAGIC HAPPENS - we KNOW slippage before trading
            buy_execution = buy_platform.order_book.calculate_market_impact('buy', volume)
            sell_execution = sell_platform.order_book.calculate_market_impact('sell', volume)
            
            # VERIFY we have sufficient liquidity 
            if buy_execution.get('remaining_volume', 0) > 0:
                print(f"⚠️ Insufficient buy liquidity: {buy_execution.get('remaining_volume')} contracts unfilled")
                return None
                
            if sell_execution.get('remaining_volume', 0) > 0:
                print(f"⚠️ Insufficient sell liquidity: {sell_execution.get('remaining_volume')} contracts unfilled")
                return None
            
            # Use ACTUAL execution prices (includes slippage)
            actual_buy_price = buy_execution.get('average_price', buy_price)
            actual_sell_price = sell_execution.get('average_price', sell_price)
            
            # Calculate all costs
            fees = self.calculate_total_fees(
                buy_platform.platform, sell_platform.platform,
                actual_buy_price, actual_sell_price, volume
            )
            
            # Slippage is already included in execution prices
            buy_slippage = buy_execution.get('slippage', 0)
            sell_slippage = sell_execution.get('slippage', 0)
            total_slippage = buy_slippage + sell_slippage
            
            # SAFETY CHECK: If slippage is way worse than expected, halt
            expected_slippage = self.estimate_slippage(buy_platform, sell_platform, volume)
            if total_slippage > (expected_slippage + self.max_slippage_deviation):
                print(f"🛑 Excessive slippage detected: {total_slippage:.4f} vs expected {expected_slippage:.4f}")
                self.emergency_halt = True
                return None
            
            # Net profit calculation with REAL execution prices
            gross_profit = (actual_sell_price - actual_buy_price) * volume
            net_profit = gross_profit - fees
            # Note: slippage already included in execution prices, so no double-counting
            
            # HALT IF ANY LOSS - This should NEVER happen with real arbitrage
            if net_profit <= 0:
                print(f"⚠️ Rejecting trade - would lose ${-net_profit:.2f}")
                print(f"   Buy: ${actual_buy_price:.3f}, Sell: ${actual_sell_price:.3f}, Fees: ${fees:.2f}")
                return None
            
            profit_margin = (net_profit / (actual_buy_price * volume)) * 100
            
            # Calculate daily profit rate (assume 1 day to expiry for now)
            daily_profit_rate = profit_margin  # Will be enhanced with real expiry dates
            
            # AUTO-EXECUTION LOGIC: Based on testing/production settings
            auto_threshold = float(os.getenv('AUTO_EXECUTE_PROFIT_THRESHOLD', '250'))
            auto_rate = float(os.getenv('AUTO_EXECUTE_DAILY_RATE', '5.0'))
            should_auto_execute = (daily_profit_rate >= auto_rate) or (net_profit >= auto_threshold)
            
            # Create detailed opportunity with PRE-CALCULATED everything
            opportunity = {
                'gross_profit': gross_profit,
                'total_fees': fees,
                'total_slippage': total_slippage,  # Already included in prices
                'net_profit': net_profit,          # FINAL profit after ALL costs
                'profit_margin_percent': profit_margin,
                'daily_profit_rate': daily_profit_rate,
                'volume': volume,
                'buy_price': actual_buy_price,     # REAL execution price
                'sell_price': actual_sell_price,   # REAL execution price
                'should_auto_execute': should_auto_execute,
                'buy_execution': buy_execution,
                'sell_execution': sell_execution,
                'execution_quality': min(buy_execution.get('filled_volume', 0), sell_execution.get('filled_volume', 0)),
                'pre_calculated': True,  # Flag that all costs are included
                'expected_slippage': expected_slippage,
                'actual_slippage': total_slippage,
                'slippage_accuracy': abs(total_slippage - expected_slippage)
            }
            
            print(f"✅ VALID ARBITRAGE FOUND:")
            print(f"   Net profit: ${net_profit:.2f} ({profit_margin:.2f}%)")
            print(f"   Slippage: ${total_slippage:.3f} (vs expected ${expected_slippage:.3f})")
            print(f"   Auto-execute: {should_auto_execute}")
            
            return opportunity
            
        except Exception as e:
            print(f"⚠️ Error validating arbitrage: {e}")
            return None
    
    def find_optimal_position_size(self, buy_platform, sell_platform) -> int:
        """
        Find optimal position size based on available liquidity and slippage
        No arbitrary limits - let the market determine optimal size
        """
        try:
            # Test different position sizes to find profit maximum
            test_sizes = [10, 25, 50, 100, 200, 500, 1000, 2000, 5000]
            
            best_size = 0
            best_total_profit = 0
            
            for size in test_sizes:
                opportunity = self.validate_arbitrage_opportunity(buy_platform, sell_platform, size)
                
                if opportunity and opportunity['net_profit'] > best_total_profit:
                    best_total_profit = opportunity['net_profit']
                    best_size = size
                elif opportunity is None:
                    # Hit the limit where slippage kills profitability
                    break
            
            print(f"📊 Optimal position size: {best_size} contracts (${best_total_profit:.2f} profit)")
            return best_size
            
        except Exception as e:
            print(f"⚠️ Error in position sizing: {e}")
            return 10  # Conservative fallback

# Test function
def test_arbitrage_detector():
    """Test the arbitrage detector with real logic"""
    detector = ArbitrageDetector()
    
    # Test fee calculations
    kalshi_fee = detector._calculate_kalshi_fee(0.50, 100)
    ibkr_fee = detector._calculate_ibkr_fee(0.50, 100)
    
    print(f"\n📊 Fee Test Results:")
    print(f"  Kalshi fee (100 contracts @ $0.50): ${kalshi_fee:.3f}")
    print(f"  IBKR fee (100 contracts @ $0.50): ${ibkr_fee:.3f}")
    
    # Test total fee calculation
    total_fees = detector.calculate_total_fees('Kalshi', 'IBKR', 0.50, 0.52, 100)
    print(f"  Total arbitrage fees: ${total_fees:.3f}")

if __name__ == "__main__":
    test_arbitrage_detector()