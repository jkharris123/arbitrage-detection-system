#!/usr/bin/env python3
"""
Smart Arbitrage Detection Bot
Considers fees, slippage, and liquidity for guaranteed profit opportunities
Built for expansion into market making and cross-platform strategies
"""

import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config.settings import Settings
from data_collectors.kalshi_client import KalshiClient
from data_collectors.ibkr_client import IBKRClient
from arbitrage.detector import ArbitrageDetector
from alerts.notifier import AlertNotifier

@dataclass
class OrderBookLevel:
    """Single level in the order book"""
    price: float
    volume: int
    num_orders: Optional[int] = None  # Number of orders at this level (if available)

@dataclass
class OrderBook:
    """Complete order book with all bid/ask levels"""
    bids: List[OrderBookLevel]  # Sorted highest to lowest price
    asks: List[OrderBookLevel]  # Sorted lowest to highest price
    timestamp: datetime
    
    def get_best_bid(self) -> Optional[OrderBookLevel]:
        """Get best (highest) bid"""
        return self.bids[0] if self.bids else None
    
    def get_best_ask(self) -> Optional[OrderBookLevel]:
        """Get best (lowest) ask"""
        return self.asks[0] if self.asks else None
    
    def get_bid_ask_spread(self) -> Optional[float]:
        """Calculate bid-ask spread"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        return None
    
    def get_spread_percentage(self) -> Optional[float]:
        """Calculate spread as percentage of mid price"""
        spread = self.get_bid_ask_spread()
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if spread and best_bid and best_ask:
            mid_price = (best_bid.price + best_ask.price) / 2
            return (spread / mid_price) * 100
        return None
    
    def calculate_market_impact(self, side: str, volume: int) -> Dict[str, float]:
        """
        Calculate market impact for a given order size
        Returns: {
            'average_price': weighted average execution price,
            'slippage': difference from best price,
            'remaining_volume': volume that couldn't be filled
        }
        """
        if side.lower() == 'buy':
            levels = self.asks  # Buying hits ask side
            best_price = self.get_best_ask().price if self.get_best_ask() else 0
        else:
            levels = self.bids  # Selling hits bid side
            best_price = self.get_best_bid().price if self.get_best_bid() else 0
        
        if not levels or not best_price:
            return {'average_price': 0, 'slippage': float('inf'), 'remaining_volume': volume}
        
        total_cost = 0
        filled_volume = 0
        remaining_volume = volume
        
        for level in levels:
            if remaining_volume <= 0:
                break
                
            volume_at_level = min(remaining_volume, level.volume)
            total_cost += volume_at_level * level.price
            filled_volume += volume_at_level
            remaining_volume -= volume_at_level
        
        if filled_volume > 0:
            average_price = total_cost / filled_volume
            slippage = abs(average_price - best_price)
            slippage_percent = (slippage / best_price) * 100
        else:
            average_price = 0
            slippage = float('inf')
            slippage_percent = float('inf')
        
        return {
            'average_price': average_price,
            'slippage': slippage,
            'slippage_percent': slippage_percent,
            'filled_volume': filled_volume,
            'remaining_volume': remaining_volume
        }
    
    def get_total_volume(self, side: str, max_levels: int = 10) -> int:
        """Get total volume available on one side up to max_levels"""
        levels = self.bids if side.lower() == 'bid' else self.asks
        return sum(level.volume for level in levels[:max_levels])
    
    def get_volume_at_price_range(self, min_price: float, max_price: float, side: str) -> int:
        """Get total volume available in a price range"""
        levels = self.bids if side.lower() == 'bid' else self.asks
        return sum(
            level.volume for level in levels 
            if min_price <= level.price <= max_price
        )

@dataclass
class MarketData:
    """Enhanced market data with full order book depth"""
    platform: str
    contract_name: str
    order_book: OrderBook
    last_trade_price: Optional[float] = None
    last_trade_volume: Optional[int] = None
    last_trade_timestamp: Optional[datetime] = None
    daily_volume: Optional[int] = None
    open_interest: Optional[int] = None
    
    # Convenience properties for backward compatibility
    @property
    def bid_price(self) -> float:
        """Best bid price"""
        best_bid = self.order_book.get_best_bid()
        return best_bid.price if best_bid else 0.0
    
    @property
    def ask_price(self) -> float:
        """Best ask price"""
        best_ask = self.order_book.get_best_ask()
        return best_ask.price if best_ask else 0.0
    
    @property
    def bid_volume(self) -> int:
        """Best bid volume"""
        best_bid = self.order_book.get_best_bid()
        return best_bid.volume if best_bid else 0
    
    @property
    def ask_volume(self) -> int:
        """Best ask volume"""
        best_ask = self.order_book.get_best_ask()
        return best_ask.volume if best_ask else 0
    
    @property
    def timestamp(self) -> datetime:
        """Order book timestamp"""
        return self.order_book.timestamp
    
    def calculate_execution_cost(self, side: str, volume: int) -> Dict[str, float]:
        """Calculate the cost of executing an order of given size"""
        return self.order_book.calculate_market_impact(side, volume)
    
    def get_liquidity_score(self) -> float:
        """
        Calculate liquidity score (0-100) based on:
        - Total volume in top 5 levels
        - Spread tightness
        - Order book depth
        """
        score = 50  # Base score
        
        """PLACEHOLDER"""
        # PLACEHOLDER - Volume component (40 points max)
        total_bid_volume = self.order_book.get_total_volume('bid', 5)
        total_ask_volume = self.order_book.get_total_volume('ask', 5)
        avg_volume = (total_bid_volume + total_ask_volume) / 2
        
        if avg_volume >= 1000:
            score += 40
        elif avg_volume >= 500:
            score += 30
        elif avg_volume >= 100:
            score += 20
        elif avg_volume >= 50:
            score += 10
        
        """PLACEHOLDER"""
        # PLACEHOLDER - Spread component (10 points max)
        spread_pct = self.order_book.get_spread_percentage()
        if spread_pct:
            if spread_pct <= 1.0:
                score += 10
            elif spread_pct <= 2.0:
                score += 7
            elif spread_pct <= 5.0:
                score += 5
            elif spread_pct <= 10.0:
                score += 2
        
        return min(score, 100)
    
    def to_summary_dict(self) -> Dict:
        """Convert to dictionary for logging/alerts"""
        return {
            'platform': self.platform,
            'contract': self.contract_name,
            'bid': self.bid_price,
            'ask': self.ask_price,
            'bid_vol': self.bid_volume,
            'ask_vol': self.ask_volume,
            'spread': self.order_book.get_bid_ask_spread(),
            'spread_pct': self.order_book.get_spread_percentage(),
            'liquidity_score': self.get_liquidity_score(),
            'total_bid_vol_5': self.order_book.get_total_volume('bid', 5),
            'total_ask_vol_5': self.order_book.get_total_volume('ask', 5),
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class ArbitrageOpportunity:
    """Enhanced arbitrage opportunity with detailed execution analysis"""
    buy_platform: str
    sell_platform: str
    buy_market_data: MarketData
    sell_market_data: MarketData
    optimal_volume: int
    buy_execution_cost: Dict[str, float]  # From calculate_market_impact
    sell_execution_cost: Dict[str, float]
    gross_profit_per_contract: float
    total_fees: float
    net_profit_per_contract: float
    total_net_profit: float
    profit_margin_percent: float
    contract_name: str
    confidence_score: float
    liquidity_score: float
    execution_risk_score: float
    timestamp: datetime
    
    def to_alert_dict(self) -> Dict:
        """Convert to dictionary for alerts"""
        return {
            'contract': self.contract_name,
            'strategy': f"Buy {self.buy_platform} @ ${self.buy_execution_cost['average_price']:.3f}, Sell {self.sell_platform} @ ${self.sell_execution_cost['average_price']:.3f}",
            'volume': self.optimal_volume,
            'net_profit_per_contract': f"${self.net_profit_per_contract:.3f}",
            'total_profit': f"${self.total_net_profit:.2f}",
            'profit_margin': f"{self.profit_margin_percent:.2f}%",
            'buy_slippage': f"{self.buy_execution_cost['slippage_percent']:.2f}%",
            'sell_slippage': f"{self.sell_execution_cost['slippage_percent']:.2f}%",
            'confidence': f"{self.confidence_score:.0f}/100",
            'liquidity': f"{self.liquidity_score:.0f}/100",
            'timestamp': self.timestamp.isoformat()
        }

class ArbitrageBot:
    """
    Smart arbitrage bot that only alerts on guaranteed profitable opportunities
    Accounts for all transaction costs, slippage, and liquidity constraints
    """
    
    def __init__(self):
        self.settings = Settings()
        self.kalshi_client = KalshiClient()
        self.ibkr_client = IBKRClient()
        self.arbitrage_detector = ArbitrageDetector()
        self.notifier = AlertNotifier()
        
        self.setup_logging()
        self.running = False
        self.iteration_count = 0
        
        # Performance tracking
        self.opportunities_found = 0
        self.total_potential_profit = 0.0
        self.start_time = datetime.now()
        
    def setup_logging(self):
        """Configure comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/arbitrage_bot_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def collect_market_data(self) -> Dict[str, List[MarketData]]:
        """
        Collect real-time market data from all platforms
        Returns data grouped by contract for comparison
        """
        self.logger.info("🔄 Collecting market data from all platforms...")
        
        try:
            # Collect from Kalshi
            kalshi_data = self.kalshi_client.get_market_data()
            
            # Collect from IBKR ForecastTrader  
            ibkr_data = self.ibkr_client.get_market_data()
            
            # Group by contract for comparison
            grouped_data = self._group_data_by_contract(kalshi_data, ibkr_data)
            
            self.logger.info(f"📊 Collected data for {len(grouped_data)} contracts")
            return grouped_data
            
        except Exception as e:
            self.logger.error(f"❌ Error collecting market data: {e}")
            return {}
    
    def _group_data_by_contract(self, kalshi_data: List[MarketData], 
                               ibkr_data: List[MarketData]) -> Dict[str, List[MarketData]]:
        """Group market data by contract for cross-platform comparison"""
        grouped = {}
        
        # Add Kalshi data
        for data in kalshi_data:
            contract_key = self._normalize_contract_name(data.contract_name)
            if contract_key not in grouped:
                grouped[contract_key] = []
            grouped[contract_key].append(data)
            
        # Add IBKR data
        for data in ibkr_data:
            contract_key = self._normalize_contract_name(data.contract_name)
            if contract_key not in grouped:
                grouped[contract_key] = []
            grouped[contract_key].append(data)
            
        # Only return contracts available on both platforms
        return {k: v for k, v in grouped.items() if len(v) >= 2}
    
    def _normalize_contract_name(self, name: str) -> str:
        """Normalize contract names for cross-platform matching"""
        # Implementation will depend on actual contract naming conventions
        return name.lower().replace(" ", "_").replace("-", "_")
    
    def find_arbitrage_opportunities(self, market_data: Dict[str, List[MarketData]]) -> List[ArbitrageOpportunity]:
        """
        Find profitable arbitrage opportunities after all costs
        Only returns opportunities with guaranteed positive net profit
        """
        opportunities = []
        
        for contract_name, platforms_data in market_data.items():
            if len(platforms_data) < 2:
                continue
                
            self.logger.debug(f"🔍 Analyzing arbitrage for {contract_name}")
            
            # Check all platform pairs
            for i in range(len(platforms_data)):
                for j in range(i + 1, len(platforms_data)):
                    platform_a = platforms_data[i]
                    platform_b = platforms_data[j]
                    
                    # Check both directions (A->B and B->A)
                    opp_ab = self._calculate_arbitrage_opportunity(platform_a, platform_b, contract_name)
                    opp_ba = self._calculate_arbitrage_opportunity(platform_b, platform_a, contract_name)
                    
                    if opp_ab and opp_ab.net_profit_per_contract > 0:
                        opportunities.append(opp_ab)
                        
                    if opp_ba and opp_ba.net_profit_per_contract > 0:
                        opportunities.append(opp_ba)
        
        # Sort by profit potential
        opportunities.sort(key=lambda x: x.total_net_profit, reverse=True)
        
        if opportunities:
            self.logger.info(f"💰 Found {len(opportunities)} profitable arbitrage opportunities")
        
        return opportunities
    
    def _calculate_arbitrage_opportunity(self, buy_platform: MarketData, 
                                       sell_platform: MarketData, 
                                       contract_name: str) -> Optional[ArbitrageOpportunity]:
        """
        Calculate complete arbitrage opportunity with all costs
        Returns None if not profitable after all fees and slippage
        """
        # Basic arbitrage check: buy low, sell high
        if buy_platform.ask_price >= sell_platform.bid_price:
            return None
            
        # Calculate maximum tradeable volume
        max_volume = min(buy_platform.ask_volume, sell_platform.bid_volume)
        if max_volume == 0:
            return None
            
        # Gross profit per contract
        gross_profit = sell_platform.bid_price - buy_platform.ask_price
        
        # Calculate all transaction costs
        total_fees = self.arbitrage_detector.calculate_total_fees(
            buy_platform.platform, sell_platform.platform,
            buy_platform.ask_price, sell_platform.bid_price, max_volume
        )
        
        # Estimate slippage impact
        estimated_slippage = self.arbitrage_detector.estimate_slippage(
            buy_platform, sell_platform, max_volume
        )
        
        # Net profit calculation
        net_profit_per_contract = gross_profit - total_fees - estimated_slippage
        
        # Only proceed if profitable
        if net_profit_per_contract <= 0:
            return None
            
        # Check minimum profit threshold
        profit_margin = (net_profit_per_contract / buy_platform.ask_price) * 100
        if profit_margin < self.settings.min_profit_margin_percent:
            return None
            
        total_net_profit = net_profit_per_contract * max_volume
        
        # Calculate confidence score (based on volume, spread tightness, etc.)
        confidence_score = self._calculate_confidence_score(
            buy_platform, sell_platform, max_volume, profit_margin
        )
        
        return ArbitrageOpportunity(
            buy_platform=buy_platform.platform,
            sell_platform=sell_platform.platform,
            buy_price=buy_platform.ask_price,
            sell_price=sell_platform.bid_price,
            max_volume=max_volume,
            gross_profit_per_contract=gross_profit,
            total_fees=total_fees,
            estimated_slippage=estimated_slippage,
            net_profit_per_contract=net_profit_per_contract,
            total_net_profit=total_net_profit,
            profit_margin_percent=profit_margin,
            contract_name=contract_name,
            confidence_score=confidence_score,
            timestamp=datetime.now()
        )
    
    def _calculate_confidence_score(self, buy_platform: MarketData, 
                                   sell_platform: MarketData, 
                                   volume: int, profit_margin: float) -> float:
        """Calculate confidence score for arbitrage opportunity (0-100)"""
        score = 50  # Base score
        
        # Higher volume = higher confidence
        if volume >= 100:
            score += 20
        elif volume >= 50:
            score += 10
        
        # Higher profit margin = higher confidence
        if profit_margin >= 5.0:
            score += 20
        elif profit_margin >= 2.0:
            score += 10
        
        # Tighter spreads = higher confidence
        buy_spread = (buy_platform.ask_price - buy_platform.bid_price) / buy_platform.ask_price
        sell_spread = (sell_platform.ask_price - sell_platform.bid_price) / sell_platform.bid_price
        
        if buy_spread < 0.05 and sell_spread < 0.05:  # Tight spreads
            score += 10
        
        return min(score, 100)
    
    def send_alerts(self, opportunities: List[ArbitrageOpportunity]):
        """Send alerts for profitable opportunities"""
        if not opportunities:
            return
            
        self.logger.info(f"🚨 Sending alerts for {len(opportunities)} opportunities")
        
        # Update statistics
        self.opportunities_found += len(opportunities)
        self.total_potential_profit += sum(opp.total_net_profit for opp in opportunities)
        
        # Send notifications
        self.notifier.send_arbitrage_alerts(opportunities)
        
        # Log top opportunities
        for i, opp in enumerate(opportunities[:3], 1):
            self.logger.info(
                f"#{i} 💎 {opp.contract_name}: "
                f"Buy {opp.buy_platform} @${opp.buy_price:.3f}, "
                f"Sell {opp.sell_platform} @${opp.sell_price:.3f}, "
                f"Net: ${opp.net_profit_per_contract:.3f}/contract "
                f"({opp.profit_margin_percent:.2f}%), "
                f"Volume: {opp.max_volume}, "
                f"Total: ${opp.total_net_profit:.2f}"
            )
    
    def run_single_scan(self):
        """Run a single arbitrage scan cycle"""
        self.iteration_count += 1
        scan_start = time.time()
        
        self.logger.info(f"🔄 Starting scan #{self.iteration_count}")
        
        try:
            # Collect market data
            market_data = self.collect_market_data()
            
            if not market_data:
                self.logger.warning("⚠️ No market data collected")
                return
            
            # Find arbitrage opportunities
            opportunities = self.find_arbitrage_opportunities(market_data)
            
            # Send alerts for profitable opportunities
            self.send_alerts(opportunities)
            
            scan_time = time.time() - scan_start
            self.logger.info(f"✅ Scan #{self.iteration_count} completed in {scan_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"❌ Error in scan #{self.iteration_count}: {e}")
    
    def run_continuous(self):
        """Run continuous arbitrage monitoring"""
        self.logger.info("🚀 Starting Arbitrage Bot - Continuous Mode")
        self.logger.info(f"⚙️ Min profit margin: {self.settings.min_profit_margin_percent}%")
        self.logger.info(f"⏱️ Scan interval: {self.settings.scan_interval_seconds}s")
        
        self.running = True
        
        try:
            while self.running:
                self.run_single_scan()
                
                # Performance summary every 10 scans
                if self.iteration_count % 10 == 0:
                    self._log_performance_summary()
                
                self.logger.info(f"😴 Waiting {self.settings.scan_interval_seconds}s until next scan...")
                time.sleep(self.settings.scan_interval_seconds)
                
        except KeyboardInterrupt:
            self.logger.info("⏹️ Stopping bot (Ctrl+C pressed)")
        except Exception as e:
            self.logger.error(f"💥 Unexpected error: {e}")
        finally:
            self.stop()
    
    def _log_performance_summary(self):
        """Log performance statistics"""
        runtime = datetime.now() - self.start_time
        self.logger.info(
            f"📈 Performance Summary: "
            f"{self.iteration_count} scans, "
            f"{self.opportunities_found} opportunities found, "
            f"${self.total_potential_profit:.2f} total potential profit, "
            f"Runtime: {runtime}"
        )
    
    def stop(self):
        """Stop the arbitrage bot"""
        self.running = False
        self.logger.info("🛑 Arbitrage Bot stopped")
        self._log_performance_summary()

def main():
    """Main entry point"""
    bot = ArbitrageBot()
    
    # Run single scan for testing
    if "--test" in __import__('sys').argv:
        bot.run_single_scan()
    else:
        # Run continuous monitoring
        bot.run_continuous()

if __name__ == "__main__":
    main()