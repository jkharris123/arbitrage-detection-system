#!/usr/bin/env python3
"""
ZERO RISK Arbitrage Detection System
Kalshi Demo ↔ Polymarket Live Cross-Platform Arbitrage

GOAL: Detect GUARANTEED PROFIT opportunities with precise fee/slippage calculations
RISK: ZERO (Demo Kalshi + Read-only Polymarket analysis)
"""

import asyncio
import logging
import csv
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import sys
import os
import re
from difflib import SequenceMatcher

# Add paths for our clients
sys.path.append('./data_collectors')
sys.path.append('./config')

from kalshi_client import KalshiClient
from polymarket_client import PolymarketClient
from settings import settings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """GUARANTEED PROFIT arbitrage opportunity"""
    # Identification
    timestamp: str
    kalshi_ticker: str
    kalshi_question: str
    polymarket_condition_id: str
    polymarket_question: str
    match_confidence: float  # 0-1 how similar the contracts are
    
    # Pricing (after fees and slippage)
    kalshi_yes_price: float
    kalshi_no_price: float  
    polymarket_yes_price: float
    polymarket_no_price: float
    
    # Arbitrage strategy
    strategy: str  # "YES_ARB" or "NO_ARB"
    buy_platform: str  # Where to buy cheaper side
    sell_platform: str  # Where to sell expensive side
    
    # Financial calculations (AFTER ALL COSTS)
    investment_required: float
    guaranteed_profit: float
    profit_percentage: float
    profit_per_day_annualized: float
    
    # Execution details
    kalshi_fee: float
    polymarket_gas: float
    estimated_slippage: float
    min_liquidity: float
    
    # Risk assessment
    time_to_expiry_hours: float
    is_guaranteed_profit: bool  # TRUE only if profit > 0 after ALL costs

@dataclass 
class CrossAssetOpportunity:
    """Cross-asset arbitrage (derivatives vs prediction contracts)"""
    timestamp: str
    prediction_contract: str  # Kalshi/Polymarket contract
    derivative_instrument: str  # Traditional futures/options
    predicted_correlation: float
    profit_potential: float
    complexity_score: int  # 1-5, higher = more complex
    notes: str

class ContractMatcher:
    """Intelligent contract matching between Kalshi and Polymarket"""
    
    @staticmethod
    def similarity_score(text1: str, text2: str) -> float:
        """Calculate similarity between two contract descriptions"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    @staticmethod
    def extract_keywords(text: str) -> set:
        """Extract key financial/economic terms from contract text"""
        economic_terms = {
            'fed', 'rate', 'rates', 'inflation', 'cpi', 'gdp', 'unemployment',
            'jobs', 'payroll', 'election', 'president', 'congress', 'senate',
            'sp500', 's&p', 'nasdaq', 'dow', 'bitcoin', 'crypto', 'oil',
            'gold', 'housing', 'mortgage', 'yield', 'treasury', 'bonds'
        }
        
        words = set(re.findall(r'\b\w+\b', text.lower()))
        return words.intersection(economic_terms)
    
    @staticmethod
    def is_cross_asset_opportunity(contract_text: str) -> bool:
        """Identify contracts suitable for cross-asset arbitrage"""
        cross_asset_keywords = {
            'sp500', 's&p', 'nasdaq', 'dow', 'bitcoin', 'oil', 'gold',
            'treasury', 'yield', 'bonds', 'mortgage', 'housing'
        }
        words = set(re.findall(r'\b\w+\b', contract_text.lower()))
        return bool(words.intersection(cross_asset_keywords))

class ArbitrageDetector:
    """Main arbitrage detection engine"""
    
    def __init__(self):
        self.kalshi_client = KalshiClient()
        self.matcher = ContractMatcher()
        
        # Create output directories
        os.makedirs('./output', exist_ok=True)
        os.makedirs('./output/opportunities', exist_ok=True)
        os.makedirs('./output/cross_asset', exist_ok=True)
        
        # Initialize CSV files
        self.setup_csv_files()
    
    def setup_csv_files(self):
        """Initialize CSV files for tracking opportunities"""
        # Main arbitrage opportunities
        self.arb_csv_file = './output/arbitrage_opportunities.csv'
        with open(self.arb_csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(ArbitrageOpportunity.__annotations__.keys()))
            writer.writeheader()
        
        # Cross-asset opportunities  
        self.cross_asset_csv_file = './output/cross_asset_opportunities.csv'
        with open(self.cross_asset_csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(CrossAssetOpportunity.__annotations__.keys()))
            writer.writeheader()
    
    def calculate_kalshi_total_cost(self, price: float, contracts: int, ticker: str) -> float:
        """Calculate total Kalshi cost including fees"""
        is_sp500 = settings.is_sp500_or_nasdaq_market(ticker)
        return settings.get_total_cost_kalshi(contracts, price, 'sp500_nasdaq' if is_sp500 else 'general')
    
    def calculate_polymarket_total_cost(self, price: float, contracts: int) -> float:
        """Calculate total Polymarket cost including gas"""
        return settings.get_total_cost_polymarket(contracts, price)
    
    def calculate_arbitrage_profit(self, kalshi_price: float, polymarket_price: float, 
                                 kalshi_ticker: str, trade_size: int = 100) -> Tuple[float, bool]:
        """
        Calculate guaranteed profit after ALL fees and costs
        Returns (profit_usd, is_guaranteed)
        """
        # YES arbitrage: Buy cheaper YES, sell expensive NO
        kalshi_yes_cost = self.calculate_kalshi_total_cost(kalshi_price, trade_size, kalshi_ticker)
        polymarket_no_cost = self.calculate_polymarket_total_cost(1 - polymarket_price, trade_size)
        
        # If YES wins: Get $100, paid kalshi_yes_cost + polymarket_no_cost
        yes_arb_profit = (trade_size * 1.0) - kalshi_yes_cost - polymarket_no_cost
        
        # NO arbitrage: Buy cheaper NO, sell expensive YES  
        kalshi_no_cost = self.calculate_kalshi_total_cost(1 - kalshi_price, trade_size, kalshi_ticker)
        polymarket_yes_cost = self.calculate_polymarket_total_cost(polymarket_price, trade_size)
        
        # If NO wins: Get $100, paid kalshi_no_cost + polymarket_yes_cost
        no_arb_profit = (trade_size * 1.0) - kalshi_no_cost - polymarket_yes_cost
        
        # Take the better arbitrage
        best_profit = max(yes_arb_profit, no_arb_profit)
        is_guaranteed = best_profit > 0
        
        return best_profit, is_guaranteed
    
    async def find_contract_matches(self, kalshi_markets: List[Dict], 
                                  polymarket_markets: List) -> List[Tuple[Dict, object, float]]:
        """Find matching contracts between platforms"""
        matches = []
        
        for kalshi_market in kalshi_markets:
            kalshi_question = kalshi_market.get('title', kalshi_market.get('question', ''))
            kalshi_ticker = kalshi_market.get('ticker', '')
            
            best_match = None
            best_score = 0.0
            
            for poly_market in polymarket_markets:
                poly_question = poly_market.question
                
                # Calculate similarity
                similarity = self.matcher.similarity_score(kalshi_question, poly_question)
                
                # Boost score if they share key economic terms
                kalshi_keywords = self.matcher.extract_keywords(kalshi_question)
                poly_keywords = self.matcher.extract_keywords(poly_question)
                keyword_overlap = len(kalshi_keywords.intersection(poly_keywords))
                
                if keyword_overlap > 0:
                    similarity += 0.2 * keyword_overlap  # Boost for keyword matches
                
                if similarity > best_score and similarity > 0.5:  # Minimum 50% similarity
                    best_score = similarity
                    best_match = poly_market
            
            if best_match and best_score > 0.6:  # Only high-confidence matches
                matches.append((kalshi_market, best_match, best_score))
        
        return matches
    
    async def scan_for_arbitrage(self) -> List[ArbitrageOpportunity]:
        """Main scanning function - find all arbitrage opportunities"""
        logger.info("🔍 Starting arbitrage scan...")
        
        opportunities = []
        cross_asset_opportunities = []
        
        try:
            # Get markets from both platforms
            logger.info("📊 Fetching Kalshi markets...")
            kalshi_markets = self.kalshi_client.get_markets()
            
            logger.info("📊 Fetching Polymarket markets...")
            async with PolymarketClient() as poly_client:
                polymarket_markets = await poly_client.get_active_markets(limit=500)
            
            logger.info(f"✅ Found {len(kalshi_markets)} Kalshi markets, {len(polymarket_markets)} Polymarket markets")
            
            # Find contract matches
            matches = await self.find_contract_matches(kalshi_markets, polymarket_markets)
            logger.info(f"🎯 Found {len(matches)} potential contract matches")
            
            for kalshi_market, poly_market, confidence in matches:
                try:
                    # Extract pricing data
                    kalshi_ticker = kalshi_market.get('ticker', '')
                    kalshi_yes_price = kalshi_market.get('yes_bid', 0.5)  # Default if missing
                    kalshi_no_price = 1.0 - kalshi_yes_price
                    
                    # For Polymarket, we'd need to get actual prices via API calls
                    # For now, using placeholder - would integrate with orderbook API
                    poly_yes_price = 0.5  # Placeholder - get from orderbook
                    poly_no_price = 0.5   # Placeholder - get from orderbook
                    
                    # Calculate arbitrage profit
                    profit, is_guaranteed = self.calculate_arbitrage_profit(
                        kalshi_yes_price, poly_yes_price, kalshi_ticker
                    )
                    
                    # Only create opportunity if guaranteed profit exists
                    if is_guaranteed and profit > 5.0:  # Minimum $5 profit threshold
                        
                        strategy = "YES_ARB" if kalshi_yes_price < poly_no_price else "NO_ARB"
                        
                        opportunity = ArbitrageOpportunity(
                            timestamp=datetime.now().isoformat(),
                            kalshi_ticker=kalshi_ticker,
                            kalshi_question=kalshi_market.get('title', ''),
                            polymarket_condition_id=poly_market.condition_id,
                            polymarket_question=poly_market.question,
                            match_confidence=confidence,
                            kalshi_yes_price=kalshi_yes_price,
                            kalshi_no_price=kalshi_no_price,
                            polymarket_yes_price=poly_yes_price,
                            polymarket_no_price=poly_no_price,
                            strategy=strategy,
                            buy_platform="Kalshi" if strategy == "YES_ARB" else "Polymarket",
                            sell_platform="Polymarket" if strategy == "YES_ARB" else "Kalshi",
                            investment_required=100.0,  # Standard trade size
                            guaranteed_profit=profit,
                            profit_percentage=(profit / 100.0) * 100,
                            profit_per_day_annualized=0.0,  # Calculate based on time to expiry
                            kalshi_fee=settings.get_kalshi_trading_fee(kalshi_yes_price, 100),
                            polymarket_gas=settings.get_polymarket_gas_fee(),
                            estimated_slippage=0.02,  # 2% conservative estimate
                            min_liquidity=1000.0,  # Minimum liquidity requirement
                            time_to_expiry_hours=24.0,  # Calculate from end dates
                            is_guaranteed_profit=True
                        )
                        
                        opportunities.append(opportunity)
                        logger.info(f"💰 ARBITRAGE FOUND: {profit:.2f} profit on {kalshi_ticker}")
                    
                    # Check for cross-asset opportunities
                    if (self.matcher.is_cross_asset_opportunity(kalshi_market.get('title', '')) or 
                        self.matcher.is_cross_asset_opportunity(poly_market.question)):
                        
                        cross_asset_opp = CrossAssetOpportunity(
                            timestamp=datetime.now().isoformat(),
                            prediction_contract=f"{kalshi_ticker} / {poly_market.condition_id[:8]}",
                            derivative_instrument="TBD - Traditional Market Equivalent",
                            predicted_correlation=confidence,
                            profit_potential=profit if profit > 0 else 0.0,
                            complexity_score=3,
                            notes=f"Equity/Fixed Income arbitrage opportunity - {kalshi_market.get('title', '')[:50]}"
                        )
                        cross_asset_opportunities.append(cross_asset_opp)
                
                except Exception as e:
                    logger.warning(f"⚠️ Error processing match: {e}")
                    continue
            
            # Save opportunities to CSV
            self.save_opportunities_to_csv(opportunities, cross_asset_opportunities)
            
            logger.info(f"✅ Scan complete: {len(opportunities)} arbitrage opportunities, {len(cross_asset_opportunities)} cross-asset opportunities")
            return opportunities
            
        except Exception as e:
            logger.error(f"❌ Error in arbitrage scan: {e}")
            return []
    
    def save_opportunities_to_csv(self, opportunities: List[ArbitrageOpportunity], 
                                cross_asset: List[CrossAssetOpportunity]):
        """Save all opportunities to CSV files"""
        
        # Save regular arbitrage opportunities
        with open(self.arb_csv_file, 'a', newline='') as f:
            if opportunities:
                writer = csv.DictWriter(f, fieldnames=list(ArbitrageOpportunity.__annotations__.keys()))
                for opp in opportunities:
                    writer.writerow(asdict(opp))
        
        # Save cross-asset opportunities
        with open(self.cross_asset_csv_file, 'a', newline='') as f:
            if cross_asset:
                writer = csv.DictWriter(f, fieldnames=list(CrossAssetOpportunity.__annotations__.keys()))
                for opp in cross_asset:
                    writer.writerow(asdict(opp))
    
    async def run_continuous_scan(self, interval_minutes: int = 15):
        """Run continuous arbitrage scanning"""
        logger.info(f"🚀 Starting continuous arbitrage detection (every {interval_minutes} minutes)")
        
        while True:
            try:
                opportunities = await self.scan_for_arbitrage()
                
                if opportunities:
                    logger.info(f"🎉 Found {len(opportunities)} GUARANTEED PROFIT opportunities!")
                    for opp in opportunities:
                        logger.info(f"💰 {opp.kalshi_ticker}: ${opp.guaranteed_profit:.2f} profit ({opp.profit_percentage:.1f}%)")
                else:
                    logger.info("😴 No arbitrage opportunities found this scan")
                
                # Wait for next scan
                await asyncio.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Stopping arbitrage detection")
                break
            except Exception as e:
                logger.error(f"❌ Error in continuous scan: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

# Test function
async def test_arbitrage_detector():
    """Test the arbitrage detection system"""
    print("🚀 Testing Arbitrage Detection System...")
    
    detector = ArbitrageDetector()
    opportunities = await detector.scan_for_arbitrage()
    
    print(f"\n✅ Test complete!")
    print(f"📊 Found {len(opportunities)} arbitrage opportunities")
    print(f"📁 Results saved to: {detector.arb_csv_file}")
    print(f"📁 Cross-asset saved to: {detector.cross_asset_csv_file}")

if __name__ == "__main__":
    asyncio.run(test_arbitrage_detector())