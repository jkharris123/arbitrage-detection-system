#!/usr/bin/env python3
"""
Economic Market Filter - SIMPLIFIED
Focus on short-term economic events for direct event contract arbitrage
CROSS-ASSET REMOVED - Focus on Kalshi ↔ Polymarket arbitrage only
"""

import asyncio
import logging
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EconomicMarket:
    """Economic market for direct arbitrage (no cross-asset complexity)"""
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
    
    # Simple arbitrage assessment
    arbitrage_priority: str  # "HIGH", "MEDIUM", "LOW"
    notes: str

class EconomicMarketFilter:
    """Filter economic markets for direct event contract arbitrage"""
    
    # Economic categories for filtering (no cross-asset mapping)
    ECONOMIC_CATEGORIES = {
        'RATES': {
            'keywords': ['fed', 'federal reserve', 'interest rate', 'fomc', 'basis points', 'bps', 'monetary policy'],
            'underlying': ['FEDFUNDS', 'EFFR']
        },
        'INFLATION': {
            'keywords': ['cpi', 'consumer price index', 'pce', 'inflation', 'deflation', 'price'],
            'underlying': ['CPI', 'PCE', 'PPI']
        },
        'EMPLOYMENT': {
            'keywords': ['unemployment', 'jobs', 'payroll', 'employment', 'jobless', 'nfp'],
            'underlying': ['NFP', 'UNEMPLOYMENT']
        },
        'GDP': {
            'keywords': ['gdp', 'gross domestic product', 'economic growth', 'recession', 'growth'],
            'underlying': ['GDP']
        },
        'MARKETS': {
            'keywords': ['sp500', 's&p 500', 'nasdaq', 'dow', 'market', 'index', 'spx', 'ndx'],
            'underlying': ['SPX', 'SPY', 'NDX', 'QQQ', 'DJI']
        },
        'YIELDS': {
            'keywords': ['yield', 'treasury', 'bond', '10-year', '2-year', 'yield curve'],
            'underlying': ['10Y', '2Y', '30Y']
        },
        'CRYPTO': {
            'keywords': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto'],
            'underlying': ['BTC', 'ETH']
        }
    }
    
    def __init__(self):
        # Setup output directories
        import os
        os.makedirs('./output/economic_markets', exist_ok=True)
        
        # Initialize CSV files
        self.setup_csv_files()
        self.economic_markets = []
    
    def setup_csv_files(self):
        """Setup CSV files for tracking"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        self.economic_csv = f'./output/economic_markets/economic_markets_{timestamp}.csv'
        
        # Initialize CSV headers
        with open(self.economic_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(EconomicMarket.__annotations__.keys()))
            writer.writeheader()
    
    def categorize_market(self, question: str, ticker: str = "") -> Tuple[Optional[str], str]:
        """
        Categorize market and identify underlying asset
        Returns (category, underlying_asset)
        """
        question_lower = question.lower()
        ticker_lower = ticker.lower()
        
        for category, info in self.ECONOMIC_CATEGORIES.items():
            # Check keywords
            for keyword in info['keywords']:
                if keyword in question_lower or keyword in ticker_lower:
                    # Try to identify specific underlying asset
                    underlying = self._identify_underlying(question_lower, ticker_lower, info['underlying'])
                    return category, underlying
        
        return None, "UNKNOWN"
    
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
        Filter markets for economic events with short expiry
        Focus on direct arbitrage opportunities only
        """
        economic_markets = []
        
        logger.info("🔍 Filtering for short-term economic event markets...")
        
        # Process Kalshi markets
        for market in kalshi_markets:
            title = market.get('title', market.get('question', ''))
            ticker = market.get('ticker', '')
            
            category, underlying = self.categorize_market(title, ticker)
            
            if category:  # Only economic markets
                expiry_date, days_to_expiry = self.extract_expiry_date(title, ticker)
                
                # Focus on short-term markets (≤14 days for fast profit)
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
                        arbitrage_priority=self._assess_arbitrage_priority(category, days_to_expiry),
                        notes=f"Direct arbitrage candidate - expires in {days_to_expiry} days"
                    )
                    
                    economic_markets.append(economic_market)
        
        # Process Polymarket markets
        for market in polymarket_markets:
            if not market.has_pricing:
                continue
                
            question = market.question
            
            category, underlying = self.categorize_market(question)
            
            if category:  # Only economic markets
                expiry_date, days_to_expiry = self.extract_expiry_date(question)
                
                # Focus on short-term markets (≤14 days for fast profit)
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
                        arbitrage_priority=self._assess_arbitrage_priority(category, days_to_expiry),
                        notes=f"Direct arbitrage candidate - expires in {days_to_expiry} days"
                    )
                    
                    economic_markets.append(economic_market)
        
        # Sort by days to expiry (shortest first) then by priority
        economic_markets.sort(key=lambda x: (x.days_to_expiry, x.arbitrage_priority != "HIGH"))
        
        logger.info(f"📊 Found {len(economic_markets)} economic event markets ≤14 days")
        
        # Log summary by category
        categories = {}
        for market in economic_markets:
            categories[market.category] = categories.get(market.category, 0) + 1
        
        for category, count in categories.items():
            logger.info(f"   {category}: {count} markets")
        
        self.economic_markets = economic_markets
        self._save_economic_markets()
        
        return economic_markets
    
    def _assess_arbitrage_priority(self, category: str, days_to_expiry: int) -> str:
        """Assess direct arbitrage priority (removed cross-asset logic)"""
        # Prioritize short-term, high-volume economic events
        if category in ['MARKETS', 'RATES'] and days_to_expiry <= 7:
            return "HIGH"  # SP500/NASDAQ ranges, Fed decisions
        elif category in ['INFLATION', 'EMPLOYMENT'] and days_to_expiry <= 14:
            return "MEDIUM"  # CPI, jobs data
        elif days_to_expiry <= 3:
            return "HIGH"  # Any economic event ≤3 days is high priority
        else:
            return "LOW"
    
    def _save_economic_markets(self):
        """Save economic markets to CSV"""
        with open(self.economic_csv, 'a', newline='') as f:
            if self.economic_markets:
                writer = csv.DictWriter(f, fieldnames=list(EconomicMarket.__annotations__.keys()))
                for market in self.economic_markets:
                    row = asdict(market)
                    row['expiry_date'] = market.expiry_date.isoformat()
                    writer.writerow(row)
    
    def get_summary(self) -> Dict:
        """Get summary of economic markets for direct arbitrage"""
        economic_by_category = {}
        for market in self.economic_markets:
            economic_by_category[market.category] = economic_by_category.get(market.category, 0) + 1
        
        priority_counts = {}
        for market in self.economic_markets:
            priority_counts[market.arbitrage_priority] = priority_counts.get(market.arbitrage_priority, 0) + 1
        
        return {
            'total_economic_markets': len(self.economic_markets),
            'economic_by_category': economic_by_category,
            'priority_breakdown': priority_counts,
            'high_priority_count': len([m for m in self.economic_markets if m.arbitrage_priority == "HIGH"]),
            'short_term_count': len([m for m in self.economic_markets if m.days_to_expiry <= 7])
        }

# Test the simplified economic filter
async def test_economic_filter():
    """Test the simplified economic market filter"""
    print("🧪 Testing Simplified Economic Market Filter...")
    
    try:
        import sys
        sys.path.append('./data_collectors')
        
        # Robust imports
        try:
            from kalshi_client import KalshiClient
        except ImportError:
            sys.path.append('./data_collectors')
            from kalshi_client import KalshiClient
            
        try:
            from polymarket_client_enhanced import EnhancedPolymarketClient
        except ImportError:
            sys.path.append('./data_collectors')
            from polymarket_client_enhanced import EnhancedPolymarketClient
        
        # Get markets
        kalshi = KalshiClient()
        kalshi_markets = kalshi.get_markets()
        
        async with EnhancedPolymarketClient() as poly_client:
            polymarket_markets = await poly_client.get_active_markets_with_pricing(limit=50)
        
        # Filter for economic markets (no cross-asset)
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
                print(f"     Priority: {market.arbitrage_priority}")
        
        # Summary
        summary = filter_system.get_summary()
        print(f"\\n📈 Summary:")
        print(f"   High Priority Markets: {summary['high_priority_count']}")
        print(f"   Short-term (≤7 days): {summary['short_term_count']}")
        print(f"   Priority Breakdown: {summary['priority_breakdown']}")
        
        print(f"\\n📁 Data saved to: {filter_system.economic_csv}")
        print("✅ Ready for direct event contract arbitrage!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_economic_filter())
