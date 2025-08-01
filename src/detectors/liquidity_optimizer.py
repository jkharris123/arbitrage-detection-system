#!/usr/bin/env python3
"""
Liquidity Optimizer - Smart two-stage filtering to avoid rate limits

Stage 1: Filter by volume (proxy for activity)
Stage 2: Get real orderbook depth only for matched contracts
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OrderbookData:
    """Real orderbook data from API"""
    ticker: str
    platform: str
    bid_depth_usd: float  # Total USD available at bid
    ask_depth_usd: float  # Total USD available at ask
    spread_percent: float
    top_bid: float
    top_ask: float
    
    @property
    def total_liquidity_usd(self) -> float:
        """Total liquidity available"""
        return self.bid_depth_usd + self.ask_depth_usd


class LiquidityOptimizer:
    """
    Smart liquidity filtering to avoid rate limits
    
    Problem: Can't get orderbook for 500+ markets without hitting limits
    Solution: Two-stage filtering
    """
    
    def __init__(self, kalshi_client, min_volume_threshold: int = 1000):
        self.kalshi_client = kalshi_client
        self.min_volume_threshold = min_volume_threshold
        self.orderbook_cache = {}  # Cache to avoid repeated calls
        
    async def filter_markets_smart(self, kalshi_markets: List[Dict], 
                                 polymarket_markets: List, 
                                 min_volume_usd: float = 5000) -> Tuple[List[Dict], List]:
        """
        Smart two-stage filtering
        
        Stage 1: Filter by raw volume (not volume × price)
        Stage 2: Get orderbook only for promising markets
        """
        logger.info("🎯 Smart liquidity filtering - Stage 1: Volume filter")
        
        # Stage 1: Filter by pure volume (better proxy than volume × price)
        kalshi_filtered = []
        for market in kalshi_markets:
            volume = market.get('volume', 0)
            if volume >= self.min_volume_threshold:
                # Add computed fields for compatibility
                market['volume_usd'] = volume  # Use raw volume as proxy
                kalshi_filtered.append(market)
        
        poly_filtered = []
        for market in polymarket_markets:
            if hasattr(market, 'volume') and market.volume >= self.min_volume_threshold:
                poly_filtered.append(market)
        
        logger.info(f"✅ Stage 1 complete: {len(kalshi_filtered)} Kalshi, {len(poly_filtered)} Polymarket markets")
        
        # Return filtered markets - orderbook will be fetched only for matches
        return kalshi_filtered, poly_filtered
    
    async def get_orderbook_for_match(self, kalshi_ticker: str, 
                                    poly_condition_id: str) -> Tuple[Optional[OrderbookData], Optional[OrderbookData]]:
        """
        Get real orderbook data for a specific matched pair
        This is called ONLY after contracts are matched to avoid rate limits
        """
        logger.info(f"📊 Fetching orderbook for matched pair: {kalshi_ticker} ↔ {poly_condition_id[:8]}...")
        
        # Check cache first
        kalshi_cache_key = f"kalshi_{kalshi_ticker}"
        if kalshi_cache_key in self.orderbook_cache:
            kalshi_orderbook = self.orderbook_cache[kalshi_cache_key]
        else:
            kalshi_orderbook = await self._get_kalshi_orderbook(kalshi_ticker)
            if kalshi_orderbook:
                self.orderbook_cache[kalshi_cache_key] = kalshi_orderbook
        
        # Get Polymarket orderbook
        poly_orderbook = await self._get_polymarket_orderbook(poly_condition_id)
        
        return kalshi_orderbook, poly_orderbook
    
    async def _get_kalshi_orderbook(self, ticker: str) -> Optional[OrderbookData]:
        """Get Kalshi orderbook data"""
        try:
            # Call Kalshi GetMarketOrderbook endpoint
            orderbook = self.kalshi_client.get_market_orderbook(ticker)
            
            if not orderbook:
                return None
            
            # Calculate liquidity from orderbook
            bid_depth_usd = 0
            ask_depth_usd = 0
            
            # Sum up bid side liquidity
            for bid in orderbook.get('yes_bids', [])[:5]:  # Top 5 levels
                price = bid.get('price', 0) / 100  # Convert cents to dollars
                quantity = bid.get('quantity', 0)
                bid_depth_usd += price * quantity
            
            # Sum up ask side liquidity  
            for ask in orderbook.get('yes_asks', [])[:5]:  # Top 5 levels
                price = ask.get('price', 0) / 100
                quantity = ask.get('quantity', 0)
                ask_depth_usd += price * quantity
            
            # Get best bid/ask
            best_bid = orderbook.get('yes_bids', [{}])[0].get('price', 0) / 100 if orderbook.get('yes_bids') else 0
            best_ask = orderbook.get('yes_asks', [{}])[0].get('price', 0) / 100 if orderbook.get('yes_asks') else 0
            
            spread_percent = ((best_ask - best_bid) / best_bid * 100) if best_bid > 0 else 999
            
            return OrderbookData(
                ticker=ticker,
                platform="Kalshi",
                bid_depth_usd=bid_depth_usd,
                ask_depth_usd=ask_depth_usd,
                spread_percent=spread_percent,
                top_bid=best_bid,
                top_ask=best_ask
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Error fetching Kalshi orderbook for {ticker}: {e}")
            return None
    
    async def _get_polymarket_orderbook(self, condition_id: str) -> Optional[OrderbookData]:
        """Get Polymarket orderbook data"""
        try:
            from data_collectors.polymarket_client import EnhancedPolymarketClient
            
            async with EnhancedPolymarketClient() as client:
                # Get orderbook for YES token
                yes_token_id = f"{condition_id}_YES"
                orderbook = await client.get_orderbook(yes_token_id)
                
                if not orderbook:
                    return None
                
                # Calculate liquidity
                bid_depth_usd = 0
                ask_depth_usd = 0
                
                # Sum up bid side
                for bid in orderbook.get('bids', [])[:5]:
                    price = float(bid.get('price', 0))
                    size = float(bid.get('size', 0))
                    bid_depth_usd += price * size
                
                # Sum up ask side
                for ask in orderbook.get('asks', [])[:5]:
                    price = float(ask.get('price', 0))
                    size = float(ask.get('size', 0))
                    ask_depth_usd += price * size
                
                # Get best bid/ask
                best_bid = float(orderbook.get('bids', [{}])[0].get('price', 0)) if orderbook.get('bids') else 0
                best_ask = float(orderbook.get('asks', [{}])[0].get('price', 0)) if orderbook.get('asks') else 0
                
                spread_percent = ((best_ask - best_bid) / best_bid * 100) if best_bid > 0 else 999
                
                return OrderbookData(
                    ticker=condition_id,
                    platform="Polymarket",
                    bid_depth_usd=bid_depth_usd,
                    ask_depth_usd=ask_depth_usd,
                    spread_percent=spread_percent,
                    top_bid=best_bid,
                    top_ask=best_ask
                )
                
        except Exception as e:
            logger.warning(f"⚠️ Error fetching Polymarket orderbook for {condition_id}: {e}")
            return None
    
    def meets_liquidity_requirements(self, kalshi_orderbook: OrderbookData, 
                                   poly_orderbook: OrderbookData,
                                   min_liquidity_usd: float = 5000) -> bool:
        """
        Check if matched pair has sufficient real liquidity
        """
        if not kalshi_orderbook or not poly_orderbook:
            return False
        
        # Both sides need minimum liquidity
        kalshi_ok = kalshi_orderbook.total_liquidity_usd >= min_liquidity_usd
        poly_ok = poly_orderbook.total_liquidity_usd >= min_liquidity_usd
        
        # Also check spreads aren't too wide
        spread_ok = kalshi_orderbook.spread_percent < 5 and poly_orderbook.spread_percent < 5
        
        return kalshi_ok and poly_ok and spread_ok


# Test the liquidity optimizer
async def test_liquidity_optimizer():
    """Test the smart liquidity filtering"""
    print("🚀 Testing Smart Liquidity Optimizer")
    print("=" * 60)
    
    from data_collectors.kalshi_client import KalshiClient
    from data_collectors.polymarket_client import EnhancedPolymarketClient
    
    # Initialize
    kalshi_client = KalshiClient(verbose=False)
    optimizer = LiquidityOptimizer(kalshi_client, min_volume_threshold=1000)
    
    # Get some markets
    print("\n📊 Getting sample markets...")
    kalshi_markets = kalshi_client.get_all_markets(min_volume=1000)[:20]
    
    async with EnhancedPolymarketClient() as poly_client:
        poly_markets = await poly_client.get_active_markets_with_pricing(limit=20)
    
    # Stage 1: Volume filter
    print("\n🎯 Stage 1: Volume-based filtering")
    kalshi_filtered, poly_filtered = await optimizer.filter_markets_smart(
        kalshi_markets, poly_markets, min_volume_usd=5000
    )
    
    print(f"✅ Filtered markets: {len(kalshi_filtered)} Kalshi, {len(poly_filtered)} Polymarket")
    
    # Stage 2: Get orderbook for a sample match
    if kalshi_filtered and poly_filtered:
        print("\n🎯 Stage 2: Getting orderbook for sample match")
        
        sample_kalshi = kalshi_filtered[0]
        sample_poly = poly_filtered[0]
        
        kalshi_ob, poly_ob = await optimizer.get_orderbook_for_match(
            sample_kalshi['ticker'],
            sample_poly.condition_id
        )
        
        if kalshi_ob:
            print(f"\n📊 Kalshi Orderbook for {kalshi_ob.ticker}:")
            print(f"   Bid depth: ${kalshi_ob.bid_depth_usd:.2f}")
            print(f"   Ask depth: ${kalshi_ob.ask_depth_usd:.2f}")
            print(f"   Total liquidity: ${kalshi_ob.total_liquidity_usd:.2f}")
            print(f"   Spread: {kalshi_ob.spread_percent:.2f}%")
        
        if poly_ob:
            print(f"\n📊 Polymarket Orderbook:")
            print(f"   Total liquidity: ${poly_ob.total_liquidity_usd:.2f}")
            print(f"   Spread: {poly_ob.spread_percent:.2f}%")
        
        # Check if meets requirements
        if kalshi_ob and poly_ob:
            meets_reqs = optimizer.meets_liquidity_requirements(kalshi_ob, poly_ob)
            print(f"\n✅ Meets liquidity requirements: {meets_reqs}")

if __name__ == "__main__":
    asyncio.run(test_liquidity_optimizer())
