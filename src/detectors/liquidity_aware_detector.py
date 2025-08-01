#!/usr/bin/env python3
"""
LIQUIDITY-AWARE ARBITRAGE DETECTOR
Multi-stage filtering with real orderbook data for matched contracts only

Key Innovation: Don't filter too early on liquidity - get real orderbook data after matching
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data_collectors.kalshi_client import KalshiClient
from data_collectors.polymarket_client import EnhancedPolymarketClient, PolymarketMarket
from contract_matcher import DateAwareContractMatcher
from arbitrage.detector import PreciseArbitrageOpportunity, EnhancedArbitrageDetector

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class OrderbookData:
    """Cached orderbook data with timestamp"""
    timestamp: float
    platform: str  # "kalshi" or "polymarket"
    ticker: str
    bids: List[Dict]  # [{'price': 0.45, 'size': 100}, ...]
    asks: List[Dict]  # [{'price': 0.55, 'size': 100}, ...]
    mid_price: float
    spread: float
    depth_10_percent: float  # Liquidity within 10% of mid
    
    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if orderbook data is too old (default 5 minutes)"""
        return time.time() - self.timestamp > max_age_seconds

class LiquidityAwareDetector(EnhancedArbitrageDetector):
    """
    Enhanced detector that uses real orderbook data for liquidity assessment
    
    Key features:
    - Stage 1: Broad initial filter (low volume threshold)
    - Stage 2: Get orderbooks only for matched contracts
    - Stage 3: Calculate real arbitrage with actual liquidity
    """
    
    def __init__(self):
        super().__init__()
        self.orderbook_cache = {}  # Cache orderbook data
        self.api_call_count = {"kalshi": 0, "polymarket": 0}
        self.rate_limit_window = {"kalshi": [], "polymarket": []}  # Track API calls
        
    async def scan_with_smart_liquidity(self, 
                                       min_initial_volume: float = 1_000,  # Much lower!
                                       min_final_liquidity: float = 10_000,  # Real liquidity check
                                       max_days_to_expiry: int = 14,
                                       max_orderbook_calls: int = 50) -> List[PreciseArbitrageOpportunity]:
        """
        Smart scanning with multi-stage liquidity filtering
        
        Args:
            min_initial_volume: Low threshold for initial filter (cast wide net)
            min_final_liquidity: Required liquidity after orderbook check
            max_days_to_expiry: Maximum days until market expiry
            max_orderbook_calls: Maximum orderbook API calls per scan
        """
        logger.info("🔍 Starting LIQUIDITY-AWARE arbitrage scan...")
        logger.info(f"📊 Stage 1 Filter: >${min_initial_volume:,.0f} volume (BROAD)")
        logger.info(f"📊 Stage 2 Filter: >${min_final_liquidity:,.0f} real liquidity (STRICT)")
        
        opportunities = []
        orderbook_calls_made = 0
        
        try:
            # STAGE 1: Broad initial filter
            logger.info("📡 STAGE 1: Fetching markets with BROAD filter...")
            
            # Get Kalshi markets with LOW volume threshold
            kalshi_markets = self.kalshi_client.get_markets_by_criteria(
                min_liquidity_usd=min_initial_volume,  # Cast wide net!
                max_days_to_expiry=max_days_to_expiry,
                min_volume=50,  # Lowered from 100
                debug=True
            )
            logger.info(f"✅ Found {len(kalshi_markets)} Kalshi markets (broad filter)")
            
            # Get Polymarket markets with LOW volume threshold
            async with EnhancedPolymarketClient() as poly_client:
                polymarket_markets = await poly_client.get_markets_by_criteria(
                    min_volume_usd=min_initial_volume,  # Cast wide net!
                    max_days_to_expiry=max_days_to_expiry,
                    limit=3000  # Get more markets
                )
            logger.info(f"✅ Found {len(polymarket_markets)} Polymarket markets (broad filter)")
            
            # STAGE 2: Find matches (no orderbook calls yet)
            logger.info("🔍 STAGE 2: Finding contract matches...")
            matches = await self.find_contract_matches(kalshi_markets, polymarket_markets)
            logger.info(f"🎯 Found {len(matches)} matched contract pairs")
            
            if not matches:
                logger.warning("⚠️ No matches found - try broader search criteria")
                return []
            
            # STAGE 3: Get orderbooks ONLY for matched pairs
            logger.info(f"📊 STAGE 3: Fetching orderbooks for {len(matches)} matches...")
            
            for i, (kalshi_market, poly_market, confidence) in enumerate(matches):
                if orderbook_calls_made >= max_orderbook_calls:
                    logger.warning(f"⚠️ Reached orderbook call limit ({max_orderbook_calls})")
                    break
                
                kalshi_ticker = kalshi_market.get('ticker', '')
                
                # Get Kalshi orderbook
                kalshi_orderbook = await self._get_kalshi_orderbook_cached(kalshi_ticker)
                if kalshi_orderbook:
                    orderbook_calls_made += 1
                
                # Get Polymarket orderbooks (YES and NO)
                poly_yes_orderbook = await self._get_polymarket_orderbook_cached(
                    poly_market.yes_token_id
                )
                poly_no_orderbook = await self._get_polymarket_orderbook_cached(
                    poly_market.no_token_id
                )
                if poly_yes_orderbook:
                    orderbook_calls_made += 1
                if poly_no_orderbook:
                    orderbook_calls_made += 1
                
                # Check real liquidity
                if not self._meets_liquidity_requirements(
                    kalshi_orderbook, poly_yes_orderbook, poly_no_orderbook, min_final_liquidity
                ):
                    logger.debug(f"❌ {kalshi_ticker} failed real liquidity check")
                    continue
                
                # Calculate arbitrage with REAL orderbook data
                opportunity = await self._calculate_arbitrage_with_orderbook(
                    kalshi_market, poly_market, confidence,
                    kalshi_orderbook, poly_yes_orderbook, poly_no_orderbook
                )
                
                if opportunity and opportunity.guaranteed_profit > 5.0:
                    opportunities.append(opportunity)
                    logger.info(f"💰 ARBITRAGE: {opportunity.opportunity_id} - ${opportunity.guaranteed_profit:.2f} profit with REAL liquidity")
                
                # Progress update
                if (i + 1) % 10 == 0:
                    logger.info(f"   Processed {i + 1}/{len(matches)} matches...")
            
            # Save results
            self.save_opportunities_to_csv(opportunities)
            
            # Summary
            logger.info(f"\n📊 LIQUIDITY-AWARE SCAN COMPLETE:")
            logger.info(f"   Stage 1: {len(kalshi_markets)} + {len(polymarket_markets)} markets")
            logger.info(f"   Stage 2: {len(matches)} matches found")
            logger.info(f"   Stage 3: {orderbook_calls_made} orderbook API calls")
            logger.info(f"   ✅ Result: {len(opportunities)} profitable opportunities")
            logger.info(f"   🎯 Efficiency: {len(opportunities) / max(orderbook_calls_made, 1):.1%} success rate")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"❌ Error in liquidity-aware scan: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _get_kalshi_orderbook_cached(self, ticker: str) -> Optional[OrderbookData]:
        """Get Kalshi orderbook with caching"""
        cache_key = f"kalshi_{ticker}"
        
        # Check cache
        if cache_key in self.orderbook_cache:
            cached = self.orderbook_cache[cache_key]
            if not cached.is_stale():
                logger.debug(f"📦 Using cached Kalshi orderbook for {ticker}")
                return cached
        
        # Fetch fresh data
        try:
            if self._check_rate_limit("kalshi"):
                orderbook_raw = self.kalshi_client.get_market_orderbook(ticker)
                if orderbook_raw and 'orderbook' in orderbook_raw:
                    ob = orderbook_raw['orderbook']
                    
                    # Parse orderbook
                    orderbook = OrderbookData(
                        timestamp=time.time(),
                        platform="kalshi",
                        ticker=ticker,
                        bids=[{'price': b[0]/100, 'size': b[1]} for b in ob.get('yes_bids', [])],
                        asks=[{'price': a[0]/100, 'size': a[1]} for a in ob.get('yes_asks', [])],
                        mid_price=0,
                        spread=0,
                        depth_10_percent=0
                    )
                    
                    # Calculate metrics
                    if orderbook.bids and orderbook.asks:
                        orderbook.mid_price = (orderbook.bids[0]['price'] + orderbook.asks[0]['price']) / 2
                        orderbook.spread = orderbook.asks[0]['price'] - orderbook.bids[0]['price']
                        orderbook.depth_10_percent = self._calculate_depth(orderbook, 0.1)
                    
                    # Cache it
                    self.orderbook_cache[cache_key] = orderbook
                    logger.debug(f"✅ Fetched Kalshi orderbook for {ticker}")
                    return orderbook
            else:
                logger.warning(f"⚠️ Rate limit reached for Kalshi")
                
        except Exception as e:
            logger.debug(f"❌ Error fetching Kalshi orderbook for {ticker}: {e}")
        
        return None
    
    async def _get_polymarket_orderbook_cached(self, token_id: str) -> Optional[OrderbookData]:
        """Get Polymarket orderbook with caching"""
        cache_key = f"polymarket_{token_id}"
        
        # Check cache
        if cache_key in self.orderbook_cache:
            cached = self.orderbook_cache[cache_key]
            if not cached.is_stale():
                logger.debug(f"📦 Using cached Polymarket orderbook for {token_id[:8]}...")
                return cached
        
        # Fetch fresh data
        try:
            if self._check_rate_limit("polymarket"):
                async with EnhancedPolymarketClient() as client:
                    orderbook_raw = await client.get_orderbook(token_id)
                    
                    if orderbook_raw:
                        # Parse orderbook
                        orderbook = OrderbookData(
                            timestamp=time.time(),
                            platform="polymarket",
                            ticker=token_id,
                            bids=[{'price': float(b['price']), 'size': float(b['size'])} 
                                  for b in orderbook_raw.get('bids', [])],
                            asks=[{'price': float(a['price']), 'size': float(a['size'])} 
                                  for a in orderbook_raw.get('asks', [])],
                            mid_price=0,
                            spread=0,
                            depth_10_percent=0
                        )
                        
                        # Calculate metrics
                        if orderbook.bids and orderbook.asks:
                            orderbook.mid_price = (orderbook.bids[0]['price'] + orderbook.asks[0]['price']) / 2
                            orderbook.spread = orderbook.asks[0]['price'] - orderbook.bids[0]['price']
                            orderbook.depth_10_percent = self._calculate_depth(orderbook, 0.1)
                        
                        # Cache it
                        self.orderbook_cache[cache_key] = orderbook
                        logger.debug(f"✅ Fetched Polymarket orderbook for {token_id[:8]}...")
                        return orderbook
            else:
                logger.warning(f"⚠️ Rate limit reached for Polymarket")
                
        except Exception as e:
            logger.debug(f"❌ Error fetching Polymarket orderbook for {token_id}: {e}")
        
        return None
    
    def _check_rate_limit(self, platform: str, max_calls_per_minute: int = 30) -> bool:
        """Check if we can make another API call without hitting rate limits"""
        now = time.time()
        window = self.rate_limit_window[platform]
        
        # Remove old calls outside 1-minute window
        self.rate_limit_window[platform] = [t for t in window if now - t < 60]
        
        # Check if we can make another call
        if len(self.rate_limit_window[platform]) < max_calls_per_minute:
            self.rate_limit_window[platform].append(now)
            self.api_call_count[platform] += 1
            return True
        
        return False
    
    def _calculate_depth(self, orderbook: OrderbookData, percent_from_mid: float) -> float:
        """Calculate orderbook depth within X% of mid price"""
        if not orderbook.mid_price:
            return 0
        
        threshold = orderbook.mid_price * percent_from_mid
        bid_threshold = orderbook.mid_price - threshold
        ask_threshold = orderbook.mid_price + threshold
        
        bid_depth = sum(b['size'] * b['price'] for b in orderbook.bids 
                       if b['price'] >= bid_threshold)
        ask_depth = sum(a['size'] * a['price'] for a in orderbook.asks 
                       if a['price'] <= ask_threshold)
        
        return bid_depth + ask_depth
    
    def _meets_liquidity_requirements(self, kalshi_ob: Optional[OrderbookData],
                                     poly_yes_ob: Optional[OrderbookData],
                                     poly_no_ob: Optional[OrderbookData],
                                     min_liquidity: float) -> bool:
        """Check if markets have sufficient real liquidity"""
        if not kalshi_ob:
            return False
        
        # Need at least one Polymarket side with good liquidity
        poly_liquidity = 0
        if poly_yes_ob:
            poly_liquidity = max(poly_liquidity, poly_yes_ob.depth_10_percent)
        if poly_no_ob:
            poly_liquidity = max(poly_liquidity, poly_no_ob.depth_10_percent)
        
        if poly_liquidity == 0:
            return False
        
        # Both sides need minimum liquidity
        total_liquidity = kalshi_ob.depth_10_percent + poly_liquidity
        
        return total_liquidity >= min_liquidity
    
    async def _calculate_arbitrage_with_orderbook(self, kalshi_market: Dict, 
                                                 poly_market: PolymarketMarket,
                                                 confidence: float,
                                                 kalshi_ob: Optional[OrderbookData],
                                                 poly_yes_ob: Optional[OrderbookData],
                                                 poly_no_ob: Optional[OrderbookData]) -> Optional[PreciseArbitrageOpportunity]:
        """Calculate arbitrage using real orderbook data"""
        # If no orderbook data, fall back to standard calculation
        if not kalshi_ob:
            return await self.calculate_precise_arbitrage(kalshi_market, poly_market, confidence)
        
        # Use orderbook prices instead of market prices
        kalshi_yes_price = kalshi_ob.bids[0]['price'] if kalshi_ob.bids else kalshi_market.get('yes_bid', 50) / 100
        kalshi_no_price = 1.0 - kalshi_yes_price
        
        # Update poly_market with orderbook prices
        if poly_yes_ob and poly_yes_ob.asks:
            poly_market.yes_token.price = poly_yes_ob.asks[0]['price']
            poly_market.yes_token.ask = poly_yes_ob.asks[0]['price']
        if poly_no_ob and poly_no_ob.asks:
            poly_market.no_token.price = poly_no_ob.asks[0]['price']
            poly_market.no_token.ask = poly_no_ob.asks[0]['price']
        
        # Calculate with real prices
        return await self.calculate_precise_arbitrage(kalshi_market, poly_market, confidence)
    
    def get_liquidity_summary(self) -> Dict:
        """Get summary of liquidity analysis"""
        return {
            'orderbook_cache_size': len(self.orderbook_cache),
            'kalshi_api_calls': self.api_call_count['kalshi'],
            'polymarket_api_calls': self.api_call_count['polymarket'],
            'total_api_calls': sum(self.api_call_count.values()),
            'cache_items': [
                {
                    'key': k,
                    'platform': v.platform,
                    'mid_price': v.mid_price,
                    'spread': v.spread,
                    'depth_10pct': v.depth_10_percent,
                    'age_seconds': time.time() - v.timestamp
                }
                for k, v in list(self.orderbook_cache.items())[:5]  # Show first 5
            ]
        }

# Test the liquidity-aware detector
async def test_liquidity_aware_detector():
    """Test the multi-stage liquidity-aware detector"""
    print("🚀 Testing LIQUIDITY-AWARE Arbitrage Detector...")
    print("🎯 Multi-stage approach:")
    print("   1️⃣ BROAD initial filter (>$1k volume)")
    print("   2️⃣ Match contracts between platforms")
    print("   3️⃣ Get REAL orderbook data for matches only")
    print("   4️⃣ Calculate arbitrage with actual liquidity\n")
    
    detector = LiquidityAwareDetector()
    
    # Run scan with smart liquidity filtering
    opportunities = await detector.scan_with_smart_liquidity(
        min_initial_volume=1_000,     # Cast wide net!
        min_final_liquidity=10_000,   # But require real liquidity
        max_days_to_expiry=14,
        max_orderbook_calls=50        # Limit API calls
    )
    
    print(f"\n✅ Liquidity-aware scan complete!")
    print(f"📊 Found {len(opportunities)} opportunities with REAL liquidity")
    
    # Show liquidity summary
    liquidity_summary = detector.get_liquidity_summary()
    print(f"\n📊 LIQUIDITY ANALYSIS:")
    print(f"   🔍 Total API calls: {liquidity_summary['total_api_calls']}")
    print(f"   📦 Orderbook cache size: {liquidity_summary['orderbook_cache_size']}")
    print(f"   🎯 Efficiency: {len(opportunities) / max(liquidity_summary['total_api_calls'], 1) * 100:.1f}% success rate")
    
    if opportunities:
        print(f"\n🏆 TOP OPPORTUNITIES (with real liquidity):")
        for i, opp in enumerate(opportunities[:3], 1):
            print(f"\n#{i}: {opp.opportunity_id}")
            print(f"   💰 Profit: ${opp.guaranteed_profit:.2f} ({opp.profit_percentage:.1f}%)")
            print(f"   📊 Volume: ${opp.trade_size_usd:.0f}")
            print(f"   🌊 Liquidity Score: {opp.liquidity_score:.0f}/100")
            print(f"   ⏰ Time to expiry: {opp.time_to_expiry_hours:.1f}h")
    
    return opportunities

if __name__ == "__main__":
    asyncio.run(test_liquidity_aware_detector())
