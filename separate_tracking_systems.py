#!/usr/bin/env python3
"""
Separate Tracking Systems for Traditional Arbitrage vs TradFi Arbitrage

Traditional Arbitrage: Kalshi ↔ Polymarket direct price differences
TradFi Arbitrage: Prediction markets ↔ Traditional derivatives (options, futures)
"""

import asyncio
import logging
import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TraditionalArbitrageOpportunity:
    """Traditional arbitrage between Kalshi and Polymarket"""
    timestamp: str
    opportunity_id: str  # Format: A001, A002, etc.
    
    # Contract details
    kalshi_ticker: str
    kalshi_question: str
    polymarket_condition_id: str
    polymarket_question: str
    match_confidence: float
    
    # Strategy
    strategy_type: str  # "YES_ARBITRAGE" or "NO_ARBITRAGE"
    buy_platform: str
    sell_platform: str
    buy_side: str
    sell_side: str
    
    # Pricing
    kalshi_price: float
    polymarket_price: float
    spread: float
    
    # Financial analysis
    trade_size_usd: float
    kalshi_cost: float
    polymarket_cost: float
    guaranteed_profit: float
    profit_percentage: float
    
    # Risk factors
    time_to_expiry_hours: float
    liquidity_score: float
    execution_certainty: float
    
    # Status
    status: str  # "ACTIVE", "EXECUTED", "EXPIRED", "DECLINED"
    recommendation: str

@dataclass
class TradFiArbitrageOpportunity:
    """TradFi arbitrage between prediction markets and derivatives"""
    timestamp: str
    opportunity_id: str  # Format: T001, T002, etc.
    
    # Prediction market side
    prediction_platform: str  # "Kalshi" or "Polymarket"
    prediction_ticker: str
    prediction_question: str
    prediction_price: float
    prediction_implied_probability: float
    
    # Traditional derivatives side
    underlying_symbol: str  # "SPX", "NDX", etc.
    derivative_type: str  # "OPTIONS", "FUTURES", "BONDS"
    derivative_description: str  # "SPX Dec 6000 Calls"
    derivative_price: float
    implied_probability: float  # From derivative pricing
    
    # Options-specific data (if applicable)
    strike_price: Optional[float] = None
    expiry_date: Optional[str] = None
    option_type: Optional[str] = None  # "CALL" or "PUT"
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    implied_volatility: Optional[float] = None
    
    # Strategy analysis
    strategy_type: str  # "DELTA_HEDGE", "GAMMA_SCALP", "VOLATILITY_ARB"
    probability_divergence: float  # Difference in implied probabilities
    edge_estimate: float  # Estimated edge in probability terms
    
    # Position sizing
    recommended_position_size: float
    max_loss: float
    expected_profit: float
    profit_probability: float
    
    # Risk management
    time_decay_risk: float  # Theta exposure
    market_risk: float  # Delta exposure
    volatility_risk: float  # Vega exposure
    complexity_score: int  # 1-5 (1=simple, 5=complex)
    
    # Status
    status: str  # "ANALYZED", "PENDING", "EXECUTED", "MONITORING"
    recommendation: str

class ArbitrageTrackingSystem:
    """Separate tracking for Traditional vs TradFi arbitrage"""
    
    def __init__(self):
        # Setup directories
        os.makedirs('./output/traditional_arbitrage', exist_ok=True)
        os.makedirs('./output/tradfi_arbitrage', exist_ok=True)
        
        # Initialize counters
        self.traditional_counter = 0
        self.tradfi_counter = 0
        
        # Initialize CSV files
        self.setup_csv_files()
        
        # Storage
        self.traditional_opportunities = []
        self.tradfi_opportunities = []
    
    def setup_csv_files(self):
        """Setup separate CSV files for each arbitrage type"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Traditional arbitrage CSV
        self.traditional_csv = f'./output/traditional_arbitrage/traditional_arb_{timestamp}.csv'
        with open(self.traditional_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(TraditionalArbitrageOpportunity.__annotations__.keys()))
            writer.writeheader()
        
        # TradFi arbitrage CSV
        self.tradfi_csv = f'./output/tradfi_arbitrage/tradfi_arb_{timestamp}.csv'
        with open(self.tradfi_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(TradFiArbitrageOpportunity.__annotations__.keys()))
            writer.writeheader()
    
    def generate_traditional_id(self) -> str:
        """Generate alphanumeric ID for traditional arbitrage (A001, A002, etc.)"""
        self.traditional_counter += 1
        return f"A{self.traditional_counter:03d}"
    
    def generate_tradfi_id(self) -> str:
        """Generate alphanumeric ID for TradFi arbitrage (T001, T002, etc.)"""
        self.tradfi_counter += 1
        return f"T{self.tradfi_counter:03d}"
    
    def store_traditional_opportunity(self, opportunity: TraditionalArbitrageOpportunity):
        """Store traditional arbitrage opportunity"""
        self.traditional_opportunities.append(opportunity)
        
        # Save to CSV
        with open(self.traditional_csv, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(TraditionalArbitrageOpportunity.__annotations__.keys()))
            writer.writerow(asdict(opportunity))
        
        logger.info(f"📊 Stored traditional arbitrage: {opportunity.opportunity_id} - ${opportunity.guaranteed_profit:.2f}")
    
    def store_tradfi_opportunity(self, opportunity: TradFiArbitrageOpportunity):
        """Store TradFi arbitrage opportunity"""
        self.tradfi_opportunities.append(opportunity)
        
        # Save to CSV
        with open(self.tradfi_csv, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(TradFiArbitrageOpportunity.__annotations__.keys()))
            writer.writerow(asdict(opportunity))
        
        logger.info(f"💼 Stored TradFi arbitrage: {opportunity.opportunity_id} - {opportunity.strategy_type}")
    def get_active_traditional_opportunities(self) -> List[TraditionalArbitrageOpportunity]:
        """Get active traditional arbitrage opportunities"""
        return [opp for opp in self.traditional_opportunities if opp.status == "ACTIVE"]
    
    def get_active_tradfi_opportunities(self) -> List[TradFiArbitrageOpportunity]:
        """Get active TradFi arbitrage opportunities"""
        return [opp for opp in self.tradfi_opportunities if opp.status in ["ANALYZED", "PENDING"]]
    
    def update_opportunity_status(self, opportunity_id: str, new_status: str):
        """Update opportunity status"""
        # Check traditional opportunities
        for opp in self.traditional_opportunities:
            if opp.opportunity_id == opportunity_id:
                opp.status = new_status
                logger.info(f"📊 Updated {opportunity_id} status: {new_status}")
                return True
        
        # Check TradFi opportunities
        for opp in self.tradfi_opportunities:
            if opp.opportunity_id == opportunity_id:
                opp.status = new_status
                logger.info(f"💼 Updated {opportunity_id} status: {new_status}")
                return True
        
        return False
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary for both arbitrage types"""
        traditional_active = len(self.get_active_traditional_opportunities())
        tradfi_active = len(self.get_active_tradfi_opportunities())
        
        traditional_profit = sum(opp.guaranteed_profit for opp in self.traditional_opportunities 
                               if opp.status == "EXECUTED")
        
        tradfi_profit = sum(opp.expected_profit for opp in self.tradfi_opportunities 
                          if opp.status == "EXECUTED")
        
        return {
            'traditional': {
                'total_opportunities': len(self.traditional_opportunities),
                'active_opportunities': traditional_active,
                'total_profit': traditional_profit,
                'avg_profit': traditional_profit / max(len(self.traditional_opportunities), 1)
            },
            'tradfi': {
                'total_opportunities': len(self.tradfi_opportunities),
                'active_opportunities': tradfi_active,
                'total_profit': tradfi_profit,
                'avg_profit': tradfi_profit / max(len(self.tradfi_opportunities), 1)
            },
            'combined_profit': traditional_profit + tradfi_profit
        }

class TradFiAnalysisEngine:
    """Analysis engine for TradFi arbitrage opportunities"""
    
    def __init__(self):
        # Import IBKR client for derivatives data
        try:
            import sys
            sys.path.append('./data_collectors')
            from ibkr_client import IBKRClient
            self.ibkr_client = IBKRClient()
            self.ibkr_available = True
            logger.info("✅ IBKR client initialized for TradFi analysis")
        except Exception as e:
            logger.warning(f"⚠️ IBKR client not available: {e}")
            self.ibkr_available = False
    
    def analyze_index_arbitrage(self, prediction_market, current_index_level: float) -> Optional[TradFiArbitrageOpportunity]:
        """
        Analyze arbitrage between index prediction and index derivatives
        
        Example: Kalshi "SPX above 6000" vs SPX 6000 Call options
        """
        try:
            # Extract strike level from prediction question
            import re
            question = prediction_market.get('question', '')
            
            # Look for price levels in question
            price_match = re.search(r'(\\d{4,5})', question.lower())
            if not price_match:
                return None
            
            strike_level = int(price_match.group(1))
            
            # Determine if it's "above" or "below"
            is_above = "above" in question.lower() or "over" in question.lower()
            
            # Get prediction market pricing
            prediction_price = prediction_market.get('yes_price', 0.5)
            prediction_prob = prediction_price  # Assuming price = probability
            
            # Calculate derivative-implied probability
            if self.ibkr_available:
                # Get actual options data from IBKR
                derivative_prob = self._get_options_implied_probability(
                    "SPX", strike_level, is_above, prediction_market.get('expiry_date')
                )
            else:
                # Use simplified Black-Scholes estimation
                derivative_prob = self._estimate_options_probability(
                    current_index_level, strike_level, is_above
                )
            
            if derivative_prob is None:
                return None
            
            # Calculate probability divergence
            prob_divergence = abs(prediction_prob - derivative_prob)
            
            # Only proceed if divergence is significant (>5%)
            if prob_divergence < 0.05:
                return None
            
            # Determine strategy
            if prediction_prob < derivative_prob - 0.05:
                strategy = "LONG_PREDICTION_SHORT_DERIVATIVE"
                expected_profit = prob_divergence * 1000  # Rough estimate
            elif prediction_prob > derivative_prob + 0.05:
                strategy = "SHORT_PREDICTION_LONG_DERIVATIVE"
                expected_profit = prob_divergence * 1000
            else:
                return None
            
            # Generate opportunity ID
            tracking_system = ArbitrageTrackingSystem()
            opportunity_id = tracking_system.generate_tradfi_id()
            
            return TradFiArbitrageOpportunity(
                timestamp=datetime.now().isoformat(),
                opportunity_id=opportunity_id,
                prediction_platform="Kalshi",  # Assuming Kalshi for now
                prediction_ticker=prediction_market.get('ticker', ''),
                prediction_question=question,
                prediction_price=prediction_price,
                prediction_implied_probability=prediction_prob,
                underlying_symbol="SPX",
                derivative_type="OPTIONS",
                derivative_description=f"SPX {strike_level} {'Call' if is_above else 'Put'}",
                derivative_price=0.0,  # Would get from IBKR
                implied_probability=derivative_prob,
                strike_price=strike_level,
                expiry_date=prediction_market.get('expiry_date', ''),
                option_type="CALL" if is_above else "PUT",
                strategy_type=strategy,
                probability_divergence=prob_divergence,
                edge_estimate=prob_divergence,
                recommended_position_size=1000.0,  # $1000 default
                max_loss=1000.0,
                expected_profit=expected_profit,
                profit_probability=0.6,  # Conservative estimate
                time_decay_risk=0.1,  # Low for short-term
                market_risk=0.5,  # Medium
                volatility_risk=0.3,  # Medium
                complexity_score=3,  # Moderate complexity
                status="ANALYZED",
                recommendation="ANALYZE_FURTHER" if prob_divergence > 0.1 else "MONITOR"
            )
            
        except Exception as e:
            logger.error(f"❌ Error analyzing index arbitrage: {e}")
            return None
    
    def _get_options_implied_probability(self, symbol: str, strike: float, 
                                       is_call: bool, expiry: str) -> Optional[float]:
        """Get implied probability from IBKR options data"""
        if not self.ibkr_available:
            return None
        
        try:
            # This would use IBKR API to get actual options prices
            # For now, return placeholder
            return 0.5  # Placeholder
        except Exception as e:
            logger.debug(f"Error getting IBKR options data: {e}")
            return None
    
    def _estimate_options_probability(self, current_price: float, strike: float, 
                                    is_above: bool) -> float:
        """Estimate probability using simplified Black-Scholes"""
        import math
        
        # Simplified probability estimation
        # In reality, would use full Black-Scholes with volatility, time to expiry, etc.
        
        moneyness = current_price / strike
        
        if is_above:
            # Probability of finishing above strike
            if moneyness > 1.1:
                return 0.8  # High probability
            elif moneyness > 1.05:
                return 0.6
            elif moneyness > 1.0:
                return 0.55
            elif moneyness > 0.95:
                return 0.45
            else:
                return 0.3
        else:
            # Probability of finishing below strike
            return 1.0 - self._estimate_options_probability(current_price, strike, True)

# Test the tracking system
async def test_tracking_system():
    """Test the separate tracking systems"""
    print("🧪 Testing Separate Arbitrage Tracking Systems...")
    
    tracking = ArbitrageTrackingSystem()
    tradfi_engine = TradFiAnalysisEngine()
    
    # Test traditional arbitrage opportunity
    traditional_opp = TraditionalArbitrageOpportunity(
        timestamp=datetime.now().isoformat(),
        opportunity_id=tracking.generate_traditional_id(),
        kalshi_ticker="NASDAQ100D-25JUL18",
        kalshi_question="Will NASDAQ close above 19000?",
        polymarket_condition_id="test123",
        polymarket_question="NASDAQ above 19000 July 18",
        match_confidence=0.85,
        strategy_type="YES_ARBITRAGE",
        buy_platform="Kalshi",
        sell_platform="Polymarket",
        buy_side="YES",
        sell_side="NO",
        kalshi_price=0.45,
        polymarket_price=0.52,
        spread=0.07,
        trade_size_usd=100.0,
        kalshi_cost=45.0,
        polymarket_cost=52.0,
        guaranteed_profit=7.0,
        profit_percentage=7.0,
        time_to_expiry_hours=24.0,
        liquidity_score=80.0,
        execution_certainty=90.0,
        status="ACTIVE",
        recommendation="EXECUTE"
    )
    
    tracking.store_traditional_opportunity(traditional_opp)
    
    # Test TradFi arbitrage opportunity
    tradfi_opp = TradFiArbitrageOpportunity(
        timestamp=datetime.now().isoformat(),
        opportunity_id=tracking.generate_tradfi_id(),
        prediction_platform="Kalshi",
        prediction_ticker="INXD-25JUL18-6000",
        prediction_question="Will SPX close above 6000?",
        prediction_price=0.65,
        prediction_implied_probability=0.65,
        underlying_symbol="SPX",
        derivative_type="OPTIONS",
        derivative_description="SPX Jul 6000 Calls",
        derivative_price=45.50,
        implied_probability=0.55,
        strike_price=6000.0,
        expiry_date="2025-07-18",
        option_type="CALL",
        delta=0.45,
        gamma=0.02,
        theta=-2.5,
        implied_volatility=0.18,
        strategy_type="DELTA_HEDGE",
        probability_divergence=0.10,
        edge_estimate=0.10,
        recommended_position_size=500.0,
        max_loss=500.0,
        expected_profit=50.0,
        profit_probability=0.65,
        time_decay_risk=0.15,
        market_risk=0.45,
        volatility_risk=0.25,
        complexity_score=4,
        status="ANALYZED",
        recommendation="EXECUTE_WITH_CAUTION"
    )
    
    tracking.store_tradfi_opportunity(tradfi_opp)
    
    # Test summary
    summary = tracking.get_performance_summary()
    
    print(f"\\n📊 Tracking System Test Results:")
    print(f"   Traditional Opportunities: {summary['traditional']['total_opportunities']}")
    print(f"   TradFi Opportunities: {summary['tradfi']['total_opportunities']}")
    print(f"   Active Traditional: {summary['traditional']['active_opportunities']}")
    print(f"   Active TradFi: {summary['tradfi']['active_opportunities']}")
    
    print(f"\\n📁 Files created:")
    print(f"   Traditional: {tracking.traditional_csv}")
    print(f"   TradFi: {tracking.tradfi_csv}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_tracking_system())
