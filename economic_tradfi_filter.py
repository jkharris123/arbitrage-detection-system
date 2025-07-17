#!/usr/bin/env python3
"""
Economic & TradFi Market Filter
Focus on short-term economic data and traditional finance markets
Stores data for cross-asset arbitrage opportunities
"""

import asyncio
import logging
import json
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EconomicMarket:
    """Economic/TradFi market with cross-asset potential"""
    platform: str  # "Kalshi" or "Polymarket"
    ticker: str
    question: str
    category: str  # "RATES", "INFLATION", "EMPLOYMENT", "GDP", "MARKETS", "YIELDS"
    underlying_asset: str  # "SPX", "10Y", "FEDFUNDS", "CPI", etc.
    expiry_date: datetime
    days_to_expiry: int
    
    # Pricing data
    yes_price: float
    no_price: float
    volume_24h: float
    
    # Cross-asset mapping
    tradfi_equivalent: str  # "SPX Options", "Treasury Futures", etc.
    arbitrage_potential: str  # "HIGH", "MEDIUM", "LOW"
    notes: str

@dataclass
class CrossAssetOpportunity:
    """Cross-asset arbitrage opportunity"""
    timestamp: str
    opportunity_id: str
    
    # Prediction market side
    prediction_platform: str
    prediction_ticker: str
    prediction_question: str
    prediction_price: float
    prediction_side: str  # "YES" or "NO"
    
    # Traditional finance side
    tradfi_instrument: str  # "SPX Dec 6000 Calls", "10Y Treasury Futures"
    tradfi_action: str  # "BUY", "SELL", "HEDGE"
    tradfi_price: str  # "Estimated" or actual
    
    # Opportunity analysis
    strategy_type: str  # "LONG_GAMMA", "RATE_HEDGE", "INDEX_ARB"
    estimated_profit: float
    confidence_score: float  # 0-100
    complexity: int  # 1-5 (1=simple, 5=complex)
    time_to_expiry: int  # days
    
    recommendation: str

class EconomicMarketFilter:
    """Filter and categorize economic/tradfi markets"""
    
    # Economic categories and keywords
    ECONOMIC_CATEGORIES = {
        'RATES': {
            'keywords': ['fed', 'federal reserve', 'interest rate', 'fomc', 'basis points', 'bps', 'monetary policy'],
            'underlying': ['FEDFUNDS', 'EFFR'],
            'tradfi_equivalent': 'Treasury Futures, SOFR Futures',
            'instruments': ['ZB', 'ZN', 'ZF', 'ZT', 'SOFR']
        },
        'INFLATION': {
            'keywords': ['cpi', 'consumer price index', 'pce', 'inflation', 'deflation', 'price'],
            'underlying': ['CPI', 'PCE', 'PPI'],
            'tradfi_equivalent': 'TIPS, Treasury Futures',
            'instruments': ['TIPS', 'ZB', 'ZN']
        },
        'EMPLOYMENT': {
            'keywords': ['unemployment', 'jobs', 'payroll', 'employment', 'jobless', 'nfp'],
            'underlying': ['NFP', 'UNEMPLOYMENT'],
            'tradfi_equivalent': 'Bond Futures, Equity Futures',
            'instruments': ['ES', 'ZB', 'ZN']
        },
        'GDP': {
            'keywords': ['gdp', 'gross domestic product', 'economic growth', 'recession', 'growth'],
            'underlying': ['GDP'],
            'tradfi_equivalent': 'Equity Index Futures',
            'instruments': ['ES', 'NQ', 'RTY']
        },
        'MARKETS': {
            'keywords': ['sp500', 's&p 500', 'nasdaq', 'dow', 'market', 'index', 'spx', 'ndx'],
            'underlying': ['SPX', 'SPY', 'NDX', 'QQQ', 'DJI'],
            'tradfi_equivalent': 'Index Options, Index Futures',
            'instruments': ['ES', 'NQ', 'YM', 'SPX', 'NDX']
        },
        'YIELDS': {
            'keywords': ['yield', 'treasury', 'bond', '10-year', '2-year', 'yield curve'],
            'underlying': ['10Y', '2Y', '30Y'],
            'tradfi_equivalent': 'Treasury Futures, Bond Options',
            'instruments': ['ZB', 'ZN', 'ZF', 'ZT']
        },
        'CRYPTO': {
            'keywords': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto'],
            'underlying': ['BTC', 'ETH'],
            'tradfi_equivalent': 'Bitcoin Futures, ETH Futures',
            'instruments': ['BTC', 'ETH', 'MBT', 'MET']
        }
    }
    
    def __init__(self):
        # Setup output directories
        import os
        os.makedirs('./output/economic_markets', exist_ok=True)
        os.makedirs('./output/cross_asset', exist_ok=True)
        
        # Initialize CSV files
        self.setup_csv_files()
        
        self.economic_markets = []
        self.cross_asset_opportunities = []
    
    def setup_csv_files(self):
        """Setup CSV files for tracking"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        self.economic_csv = f'./output/economic_markets/economic_markets_{timestamp}.csv'
        self.cross_asset_csv = f'./output/cross_asset/cross_asset_opps_{timestamp}.csv'
        
        # Initialize CSV headers
        with open(self.economic_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(EconomicMarket.__annotations__.keys()))
            writer.writeheader()
        
        with open(self.cross_asset_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(CrossAssetOpportunity.__annotations__.keys()))
            writer.writeheader()
    
    def categorize_market(self, question: str, ticker: str = "") -> Tuple[Optional[str], str, str]:
        """
        Categorize market and identify underlying asset
        Returns (category, underlying_asset, tradfi_equivalent)
        """
        question_lower = question.lower()
        ticker_lower = ticker.lower()
        
        for category, info in self.ECONOMIC_CATEGORIES.items():
            # Check keywords
            for keyword in info['keywords']:
                if keyword in question_lower or keyword in ticker_lower:
                    # Try to identify specific underlying asset
                    underlying = self._identify_underlying(question_lower, ticker_lower, info['underlying'])
                    return category, underlying, info['tradfi_equivalent']
        
        return None, "UNKNOWN", "Unknown"
    
    def _identify_underlying(self, question: str, ticker: str, possible_assets: List[str]) -> str:
        """Identify specific underlying asset"""
        text = f"{question} {ticker}"
        
        for asset in possible_assets:
            if asset.lower() in text:
                return asset
        
        # Default to first asset in list
        return possible_assets[0] if possible_assets else "UNKNOWN"
    
    def extract_expiry_date(self, question: str, ticker: str = "") -> Tuple[Optional[datetime], int]:
        """
        Extract expiry date from market question/ticker
        Returns (expiry_date, days_to_expiry)
        """
        try:
            text = f"{question} {ticker}".lower()
            
            # Common date patterns
            date_patterns = [
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
                r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
                r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})',
                r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})',
                r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
                r'end of (\d{4})',
                r'by (\d{4})'
            ]
            
            # Try to find date patterns
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    # Parse based on pattern type
                    try:
                        if 'end of' in pattern or 'by' in pattern:
                            year = int(match.group(1))
                            expiry = datetime(year, 12, 31)
                        elif len(match.groups()) == 3:
                            # Full date
                            if pattern.startswith(r'(\d{1,2})/'):
                                month, day, year = map(int, match.groups())
                                expiry = datetime(year, month, day)
                            elif pattern.startswith(r'(\d{4})'):
                                year, month, day = map(int, match.groups())
                                expiry = datetime(year, month, day)
                            else:
                                # Month name format
                                month_name = match.group(1).lower()
                                day = int(match.group(2))
                                year = int(match.group(3))
                                month_map = {
                                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                                    'september': 9, 'october': 10, 'november': 11, 'december': 12
                                }
                                month = month_map.get(month_name, 1)
                                expiry = datetime(year, month, day)
                        
                        days_to_expiry = (expiry - datetime.now()).days
                        return expiry, max(days_to_expiry, 0)
                        
                    except (ValueError, KeyError):
                        continue
            
            # Default: assume 30 days if no date found
            default_expiry = datetime.now() + timedelta(days=30)
            return default_expiry, 30
            
        except Exception as e:
            logger.debug(f"Error parsing expiry date: {e}")
            default_expiry = datetime.now() + timedelta(days=30)
            return default_expiry, 30
    
    def filter_economic_markets(self, kalshi_markets: List[Dict], polymarket_markets: List) -> List[EconomicMarket]:
        """
        Filter markets to focus on economic/tradfi with short expiry
        """
        economic_markets = []
        
        logger.info("🔍 Filtering for economic and traditional finance markets...")
        
        # Process Kalshi markets
        for market in kalshi_markets:
            title = market.get('title', market.get('question', ''))
            ticker = market.get('ticker', '')
            
            category, underlying, tradfi_equiv = self.categorize_market(title, ticker)
            
            if category:  # Only economic/tradfi markets
                expiry_date, days_to_expiry = self.extract_expiry_date(title, ticker)
                
                # Focus on short-term markets (≤14 days)
                if days_to_expiry <= 14:
                    economic_market = EconomicMarket(
                        platform="Kalshi",
                        ticker=ticker,
                        question=title,
                        category=category,
                        underlying_asset=underlying,
                        expiry_date=expiry_date,
                        days_to_expiry=days_to_expiry,
                        yes_price=market.get('yes_bid', 0.5),
                        no_price=market.get('no_bid', 0.5),
                        volume_24h=market.get('volume', 0),
                        tradfi_equivalent=tradfi_equiv,
                        arbitrage_potential=self._assess_arbitrage_potential(category, days_to_expiry),
                        notes=f"Expires in {days_to_expiry} days"
                    )
                    
                    economic_markets.append(economic_market)
        
        # Process Polymarket markets
        for market in polymarket_markets:
            if not market.has_pricing:
                continue
                
            question = market.question
            
            category, underlying, tradfi_equiv = self.categorize_market(question)
            
            if category:  # Only economic/tradfi markets
                expiry_date, days_to_expiry = self.extract_expiry_date(question)
                
                # Focus on short-term markets (≤14 days)
                if days_to_expiry <= 14:
                    economic_market = EconomicMarket(
                        platform="Polymarket",
                        ticker=market.condition_id[:8],
                        question=question,
                        category=category,
                        underlying_asset=underlying,
                        expiry_date=expiry_date,
                        days_to_expiry=days_to_expiry,
                        yes_price=market.yes_token.price,
                        no_price=market.no_token.price,
                        volume_24h=market.volume,
                        tradfi_equivalent=tradfi_equiv,
                        arbitrage_potential=self._assess_arbitrage_potential(category, days_to_expiry),
                        notes=f"Expires in {days_to_expiry} days"
                    )
                    
                    economic_markets.append(economic_market)
        
        # Sort by days to expiry (shortest first)
        economic_markets.sort(key=lambda x: x.days_to_expiry)
        
        logger.info(f"📊 Found {len(economic_markets)} economic/tradfi markets ≤14 days")
        
        # Log summary by category
        categories = {}
        for market in economic_markets:
            categories[market.category] = categories.get(market.category, 0) + 1
        
        for category, count in categories.items():
            logger.info(f"   {category}: {count} markets")
        
        self.economic_markets = economic_markets
        self._save_economic_markets()
        
        return economic_markets
    
    def _assess_arbitrage_potential(self, category: str, days_to_expiry: int) -> str:
        """Assess cross-asset arbitrage potential"""
        if category in ['MARKETS', 'YIELDS', 'RATES'] and days_to_expiry <= 7:
            return "HIGH"
        elif category in ['INFLATION', 'EMPLOYMENT'] and days_to_expiry <= 14:
            return "MEDIUM"
        else:
            return "LOW"
    
    def detect_cross_asset_opportunities(self, economic_markets: List[EconomicMarket]) -> List[CrossAssetOpportunity]:
        """
        Detect cross-asset arbitrage opportunities
        Between prediction markets and traditional derivatives
        """
        opportunities = []
        
        logger.info("🔍 Scanning for cross-asset arbitrage opportunities...")
        
        for market in economic_markets:
            if market.arbitrage_potential == "LOW":
                continue
            
            # Generate cross-asset opportunity based on category
            opp = self._generate_cross_asset_strategy(market)
            if opp:
                opportunities.append(opp)
        
        logger.info(f"💰 Found {len(opportunities)} cross-asset opportunities")
        
        self.cross_asset_opportunities = opportunities
        self._save_cross_asset_opportunities()
        
        return opportunities
    
    def _generate_cross_asset_strategy(self, market: EconomicMarket) -> Optional[CrossAssetOpportunity]:
        """Generate specific cross-asset strategy for a market"""
        try:
            if market.category == "MARKETS":
                return self._generate_index_arbitrage(market)
            elif market.category == "RATES":
                return self._generate_rate_arbitrage(market)
            elif market.category == "YIELDS":
                return self._generate_yield_arbitrage(market)
            else:
                return None
                
        except Exception as e:
            logger.debug(f"Error generating cross-asset strategy: {e}")
            return None
    
    def _generate_index_arbitrage(self, market: EconomicMarket) -> Optional[CrossAssetOpportunity]:
        """Generate index arbitrage opportunity (e.g., SPX prediction vs SPX options)"""
        
        # Extract strike/level from question
        question_lower = market.question.lower()
        
        # Look for price levels
        price_match = re.search(r'(\d{4,5})', question_lower)
        if not price_match:
            return None
        
        strike_level = int(price_match.group(1))
        
        # Determine strategy based on prediction market pricing
        if market.yes_price < 0.3:  # Prediction market thinks unlikely
            strategy = "LONG_GAMMA"
            tradfi_action = "BUY CALLS" if "above" in question_lower else "BUY PUTS"
            confidence = 75.0
        elif market.yes_price > 0.7:  # Prediction market thinks likely
            strategy = "SHORT_GAMMA"
            tradfi_action = "SELL CALLS" if "above" in question_lower else "SELL PUTS"
            confidence = 70.0
        else:
            return None  # Not extreme enough for arbitrage
        
        # Estimate profit (simplified)
        estimated_profit = abs(market.yes_price - 0.5) * 1000  # Rough estimate
        
        opp_id = f"CROSS_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.cross_asset_opportunities):03d}"
        
        return CrossAssetOpportunity(
            timestamp=datetime.now().isoformat(),
            opportunity_id=opp_id,
            prediction_platform=market.platform,
            prediction_ticker=market.ticker,
            prediction_question=market.question,
            prediction_price=market.yes_price,
            prediction_side="YES",
            tradfi_instrument=f"{market.underlying_asset} {strike_level} Options",
            tradfi_action=tradfi_action,
            tradfi_price="Market Price",
            strategy_type=strategy,
            estimated_profit=estimated_profit,
            confidence_score=confidence,
            complexity=3,
            time_to_expiry=market.days_to_expiry,
            recommendation="ANALYZE" if confidence > 70 else "MONITOR"
        )
    
    def _generate_rate_arbitrage(self, market: EconomicMarket) -> Optional[CrossAssetOpportunity]:
        """Generate interest rate arbitrage opportunity"""
        
        # Rate arbitrage with bond futures
        if market.yes_price < 0.25:  # Rate hike unlikely
            tradfi_action = "BUY BOND FUTURES"
            strategy = "RATE_HEDGE"
        elif market.yes_price > 0.75:  # Rate hike likely
            tradfi_action = "SELL BOND FUTURES"
            strategy = "RATE_HEDGE"
        else:
            return None
        
        estimated_profit = abs(market.yes_price - 0.5) * 500
        
        opp_id = f"CROSS_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.cross_asset_opportunities):03d}"
        
        return CrossAssetOpportunity(
            timestamp=datetime.now().isoformat(),
            opportunity_id=opp_id,
            prediction_platform=market.platform,
            prediction_ticker=market.ticker,
            prediction_question=market.question,
            prediction_price=market.yes_price,
            prediction_side="YES",
            tradfi_instrument="Treasury Futures (ZB/ZN)",
            tradfi_action=tradfi_action,
            tradfi_price="Market Price",
            strategy_type=strategy,
            estimated_profit=estimated_profit,
            confidence_score=65.0,
            complexity=4,
            time_to_expiry=market.days_to_expiry,
            recommendation="ANALYZE"
        )
    
    def _generate_yield_arbitrage(self, market: EconomicMarket) -> Optional[CrossAssetOpportunity]:
        """Generate yield curve arbitrage opportunity"""
        
        # Similar to rate arbitrage but focused on yield curve
        if "invert" in market.question.lower() or "curve" in market.question.lower():
            strategy = "YIELD_CURVE_ARB"
            tradfi_action = "YIELD CURVE TRADE"
        else:
            return None
        
        estimated_profit = abs(market.yes_price - 0.5) * 300
        
        opp_id = f"CROSS_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.cross_asset_opportunities):03d}"
        
        return CrossAssetOpportunity(
            timestamp=datetime.now().isoformat(),
            opportunity_id=opp_id,
            prediction_platform=market.platform,
            prediction_ticker=market.ticker,
            prediction_question=market.question,
            prediction_price=market.yes_price,
            prediction_side="YES",
            tradfi_instrument="Yield Curve Spread",
            tradfi_action=tradfi_action,
            tradfi_price="Market Price",
            strategy_type=strategy,
            estimated_profit=estimated_profit,
            confidence_score=60.0,
            complexity=5,
            time_to_expiry=market.days_to_expiry,
            recommendation="MONITOR"
        )
    
    def _save_economic_markets(self):
        """Save economic markets to CSV"""
        with open(self.economic_csv, 'a', newline='') as f:
            if self.economic_markets:
                writer = csv.DictWriter(f, fieldnames=list(EconomicMarket.__annotations__.keys()))
                for market in self.economic_markets:
                    row = asdict(market)
                    row['expiry_date'] = market.expiry_date.isoformat()
                    writer.writerow(row)
    
    def _save_cross_asset_opportunities(self):
        """Save cross-asset opportunities to CSV"""
        with open(self.cross_asset_csv, 'a', newline='') as f:
            if self.cross_asset_opportunities:
                writer = csv.DictWriter(f, fieldnames=list(CrossAssetOpportunity.__annotations__.keys()))
                for opp in self.cross_asset_opportunities:
                    writer.writerow(asdict(opp))
    
    def get_summary(self) -> Dict:
        """Get summary of economic markets and cross-asset opportunities"""
        economic_by_category = {}
        for market in self.economic_markets:
            economic_by_category[market.category] = economic_by_category.get(market.category, 0) + 1
        
        cross_asset_by_strategy = {}
        for opp in self.cross_asset_opportunities:
            cross_asset_by_strategy[opp.strategy_type] = cross_asset_by_strategy.get(opp.strategy_type, 0) + 1
        
        return {
            'total_economic_markets': len(self.economic_markets),
            'economic_by_category': economic_by_category,
            'total_cross_asset_opportunities': len(self.cross_asset_opportunities),
            'cross_asset_by_strategy': cross_asset_by_strategy,
            'high_potential_count': len([m for m in self.economic_markets if m.arbitrage_potential == "HIGH"]),
            'short_term_count': len([m for m in self.economic_markets if m.days_to_expiry <= 7])
        }

# Test the economic filter
async def test_economic_filter():
    """Test the economic market filter"""
    print("🧪 Testing Economic Market Filter...")
    
    try:
        import sys
        sys.path.append('./data_collectors')
        sys.path.append('./arbitrage')
        
        from kalshi_client import KalshiClient
        from polymarket_client_enhanced import EnhancedPolymarketClient
        
        # Get markets
        kalshi = KalshiClient()
        kalshi_markets = kalshi.get_markets()
        
        async with EnhancedPolymarketClient() as poly_client:
            polymarket_markets = await poly_client.get_active_markets_with_pricing(limit=50)
        
        # Filter for economic markets
        filter_system = EconomicMarketFilter()
        economic_markets = filter_system.filter_economic_markets(kalshi_markets, polymarket_markets)
        
        print(f"\\n📊 Economic Market Filter Results:")
        print(f"   Total Economic Markets: {len(economic_markets)}")
        
        # Show top markets by category
        categories = {}
        for market in economic_markets:
            if market.category not in categories:
                categories[market.category] = []
            categories[market.category].append(market)
        
        for category, markets in categories.items():
            print(f"\\n🏷️ {category} ({len(markets)} markets):")
            for market in markets[:2]:  # Show top 2 per category
                print(f"   • {market.question[:60]}...")
                print(f"     Platform: {market.platform} | Expires: {market.days_to_expiry} days")
                print(f"     TradFi Equivalent: {market.tradfi_equivalent}")
        
        # Detect cross-asset opportunities
        cross_asset_opps = filter_system.detect_cross_asset_opportunities(economic_markets)
        
        print(f"\\n💰 Cross-Asset Opportunities: {len(cross_asset_opps)}")
        for opp in cross_asset_opps[:3]:  # Show top 3
            print(f"   • {opp.strategy_type}: {opp.prediction_question[:50]}...")
            print(f"     TradFi Action: {opp.tradfi_action}")
            print(f"     Estimated Profit: ${opp.estimated_profit:.0f}")
        
        # Summary
        summary = filter_system.get_summary()
        print(f"\\n📈 Summary:")
        print(f"   High Potential Markets: {summary['high_potential_count']}")
        print(f"   Short-term (≤7 days): {summary['short_term_count']}")
        
        print(f"\\n📁 Data saved to:")
        print(f"   Economic Markets: {filter_system.economic_csv}")
        print(f"   Cross-Asset Opportunities: {filter_system.cross_asset_csv}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_economic_filter())
