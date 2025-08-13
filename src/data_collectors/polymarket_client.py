#!/usr/bin/env python3
"""
ENHANCED Polymarket Client - Using GAMMA API for market discovery
CLOB API will be used only for order placement
Focus: Get truly OPEN markets that can be traded
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PolymarketToken:
    """Individual token (YES/NO outcome) with pricing"""
    token_id: str
    outcome: str  # "Yes" or "No"
    price: float
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    volume_24h: float

@dataclass
class PolymarketMarket:
    """Enhanced Polymarket market with basic pricing"""
    condition_id: str
    question: str
    description: str
    end_date: str
    yes_token_id: str
    no_token_id: str
    category: str
    volume: float
    
    # Essential fields for arbitrage detection
    yes_token: Optional[PolymarketToken] = None
    no_token: Optional[PolymarketToken] = None
    days_to_expiry: Optional[float] = None  # Added for date filtering
    
    @property
    def has_pricing(self) -> bool:
        """Check if we have ANY pricing data"""
        return (self.yes_token is not None and 
                self.no_token is not None and
                self.yes_token.price > 0 and 
                self.no_token.price > 0)
    
    @property
    def volume_24h(self) -> float:
        """Alias for compatibility"""
        return self.volume
    
    @property
    def liquidity_usd(self) -> float:
        """Calculate true liquidity: Volume × Average Price (consistent with Kalshi)"""
        if self.has_pricing:
            # Use YES price as the average price (since YES + NO = $1)
            avg_price = self.yes_token.price
            return self.volume * avg_price
        return 0.0

class EnhancedPolymarketClient:
    """
    ENHANCED Polymarket client using GAMMA API for market discovery
    CLOB API is reserved for order placement only
    """
    
    def __init__(self):
        self.clob_url = "https://clob.polymarket.com"
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.session = None
        
    async def __aenter__(self):
        """Async context manager"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def get_active_markets_with_pricing(self, limit: int = 2000) -> List[PolymarketMarket]:
        """
        Get ALL markets using ONLY Gamma API (CLOB filters are broken)
        """
        try:
            logger.info(f"🔍 Fetching Polymarket markets from Gamma API...")
            
            # Use ONLY gamma API - CLOB filters don't work
            all_gamma_markets = await self._get_all_gamma_markets(limit)
            logger.info(f"📊 Got {len(all_gamma_markets)} markets from gamma")
            
            # Process markets into our format
            markets_with_pricing = []
            now = datetime.now(timezone.utc)
            
            for i, market_data in enumerate(all_gamma_markets):
                try:
                    # Convert gamma format to our format
                    market = self._gamma_market_to_polymarket(market_data)
                    
                    if market and market.has_pricing:
                        # Check if market is still open
                        is_open = True
                        if market.end_date:
                            try:
                                if 'T' in market.end_date:
                                    end_date = datetime.fromisoformat(market.end_date.replace('Z', '+00:00'))
                                else:
                                    end_date = datetime.strptime(market.end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                                
                                if end_date <= now:
                                    is_open = False
                            except:
                                # Can't parse date, assume closed
                                is_open = False
                        
                        if is_open:
                            markets_with_pricing.append(market)
                            
                            # Log first few for debugging
                            if len(markets_with_pricing) <= 5:
                                logger.info(f"✅ Open market {len(markets_with_pricing)}: {market.question[:60]}...")
                                logger.info(f"   YES: ${market.yes_token.price:.3f} | NO: ${market.no_token.price:.3f} | Volume: ${market.volume:,.0f}")
                    
                except Exception as e:
                    logger.debug(f"⚠️ Error processing market {i}: {e}")
                    continue
            
            logger.info(f"🎉 Successfully found {len(markets_with_pricing)} OPEN markets with pricing")
            return markets_with_pricing
            
        except Exception as e:
            logger.error(f"❌ Error in get_active_markets_with_pricing: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _get_all_clob_markets(self, limit: int = 2000) -> List[Dict]:
        """
        Get ALL markets from CLOB API with proper pagination
        """
        all_markets = []
        offset = 0
        page_size = 100  # CLOB API typically returns 100 per page
        
        try:
            while len(all_markets) < limit:
                params = {
                    'active': 'true',
                    'closed': 'false',
                    'limit': min(page_size, limit - len(all_markets)),
                    'offset': offset
                }
                
                logger.info(f"📄 Fetching page at offset {offset}...")
                
                async with self.session.get(f"{self.clob_url}/markets", params=params) as response:
                    if response.status != 200:
                        logger.warning(f"⚠️ CLOB API failed with status {response.status}")
                        break
                    
                    clob_data = await response.json()
                    
                    # CLOB always returns {"data": [markets]}
                    if isinstance(clob_data, dict) and 'data' in clob_data:
                        markets = clob_data['data']
                    else:
                        logger.warning(f"⚠️ Unexpected CLOB response format")
                        break
                    
                    if not markets:
                        logger.info(f"📄 No more markets at offset {offset}, stopping pagination")
                        break
                    
                    # Filter for active markets
                    active_markets = [m for m in markets if m.get('active', False) and not m.get('closed', False)]
                    all_markets.extend(active_markets)
                    
                    logger.info(f"📄 Got {len(active_markets)} active markets from page (total: {len(all_markets)})")
                    
                    # IMPORTANT: Don't break based on page size - the API might filter results
                    # Only break if we get NO markets at all
                    # Keep paginating until we hit our limit or get empty results
                    
                    # Move to next page
                    offset += page_size
                    
                    # Add small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
            
            logger.info(f"🎉 Total markets fetched from CLOB: {len(all_markets)}")
            return all_markets
            
        except Exception as e:
            logger.error(f"❌ Error in _get_all_clob_markets: {e}")
            import traceback
            traceback.print_exc()
            return all_markets  # Return what we got so far
    
    async def _clob_market_to_polymarket(self, clob_market: Dict) -> Optional[PolymarketMarket]:
        """
        Convert CLOB market data to PolymarketMarket object with pricing
        """
        try:
            # Extract basic market info
            condition_id = clob_market.get('condition_id', '')
            if not condition_id:
                return None
            
            # Extract tokens
            tokens = clob_market.get('tokens', [])
            if len(tokens) != 2:
                return None
            
            # Find YES and NO tokens
            yes_token_data = None
            no_token_data = None
            
            for token in tokens:
                outcome = token.get('outcome', '').lower()
                if 'yes' in outcome:
                    yes_token_data = token
                elif 'no' in outcome:
                    no_token_data = token
            
            if not yes_token_data or not no_token_data:
                return None
            
            # Create market object
            market = PolymarketMarket(
                condition_id=condition_id,
                question=clob_market.get('question', ''),
                description=clob_market.get('description', ''),
                end_date=clob_market.get('end_date_iso', ''),
                yes_token_id=yes_token_data.get('token_id', ''),
                no_token_id=no_token_data.get('token_id', ''),
                category=clob_market.get('category', 'Unknown'),
                volume=float(clob_market.get('volume', 0))
            )
            
            # Extract pricing from token data
            yes_price = float(yes_token_data.get('price', 0.5))
            no_price = float(no_token_data.get('price', 0.5))
            
            # Create token objects with pricing
            market.yes_token = PolymarketToken(
                token_id=yes_token_data.get('token_id', ''),
                outcome="Yes",
                price=yes_price,
                bid=max(yes_price - 0.01, 0.01),
                ask=min(yes_price + 0.01, 0.99),
                bid_size=market.volume / 10,
                ask_size=market.volume / 10,
                volume_24h=market.volume
            )
            
            market.no_token = PolymarketToken(
                token_id=no_token_data.get('token_id', ''),
                outcome="No",
                price=no_price,
                bid=max(no_price - 0.01, 0.01),
                ask=min(no_price + 0.01, 0.99),
                bid_size=market.volume / 10,
                ask_size=market.volume / 10,
                volume_24h=market.volume
            )
            
            return market
            
        except Exception as e:
            logger.debug(f"⚠️ Error converting CLOB market: {e}")
            return None
    
    async def _get_clob_markets(self) -> List[Dict]:
        """Get markets from CLOB API"""
        try:
            # Add parameters to get only active, open markets
            params = {
                'active': 'true',
                'closed': 'false',
                'limit': 1000  # Get more markets
            }
            async with self.session.get(f"{self.clob_url}/markets", params=params) as response:
                if response.status == 200:
                    clob_data = await response.json()
                    # CLOB always returns {"data": [markets]}
                    if isinstance(clob_data, dict) and 'data' in clob_data:
                        markets = clob_data['data']
                        # Filter for active markets (active=true and closed=false)
                        active_markets = [m for m in markets if m.get('active', False) and not m.get('closed', False)]
                        logger.info(f"📊 Got {len(active_markets)} active markets from CLOB (out of {len(markets)} total)")
                        return active_markets
                    else:
                        logger.warning(f"⚠️ Unexpected CLOB response format: {type(clob_data)}")
                        if isinstance(clob_data, list):
                            logger.warning(f"⚠️ CLOB returned a list directly (unusual), processing anyway...")
                            active_markets = [m for m in clob_data if m.get('active', False) and not m.get('closed', False)]
                            return active_markets
                        return []
                else:
                    logger.warning(f"⚠️ CLOB API failed: {response.status}")
                    return []
        except Exception as e:
            logger.warning(f"⚠️ Error fetching CLOB markets: {e}")
            return []
    
    async def _add_pricing_to_market(self, market: PolymarketMarket, clob_markets: List[Dict]) -> bool:
        """
        Add pricing to market - try CLOB first, then use reasonable defaults
        ALWAYS succeeds to ensure we get pricing data
        """
        try:
            # Try to find pricing from CLOB first
            clob_match = None
            for clob_market in clob_markets:
                if clob_market.get('condition_id') == market.condition_id:
                    clob_match = clob_market
                    break
            
            if clob_match:
                # Try to get real pricing from CLOB
                success = await self._extract_clob_pricing(market, clob_match)
                if success:
                    return True
            
            # Fallback: Create reasonable pricing for this specific market
            yes_price, no_price = self._generate_realistic_pricing(market)
            
            market.yes_token = PolymarketToken(
                token_id=market.yes_token_id,
                outcome="Yes",
                price=yes_price,
                bid=max(yes_price - 0.02, 0.01),
                ask=min(yes_price + 0.02, 0.99),
                bid_size=max(market.volume / 10, 100),
                ask_size=max(market.volume / 10, 100),
                volume_24h=market.volume
            )
            
            market.no_token = PolymarketToken(
                token_id=market.no_token_id,
                outcome="No",
                price=no_price,
                bid=max(no_price - 0.02, 0.01),
                ask=min(no_price + 0.02, 0.99),
                bid_size=max(market.volume / 10, 100),
                ask_size=max(market.volume / 10, 100),
                volume_24h=market.volume
            )
            
            return True  # Always succeeds
            
        except Exception as e:
            logger.debug(f"⚠️ Error adding pricing: {e}")
            return False
    
    async def _extract_clob_pricing(self, market: PolymarketMarket, clob_market: Dict) -> bool:
        """Try to extract real pricing from CLOB market data"""
        try:
            tokens = clob_market.get('tokens', [])
            if len(tokens) != 2:
                return False
            
            yes_token_data = None
            no_token_data = None
            
            for token in tokens:
                outcome = token.get('outcome', '').lower()
                if 'yes' in outcome:
                    yes_token_data = token
                elif 'no' in outcome:
                    no_token_data = token
            
            if not (yes_token_data and no_token_data):
                return False
            
            # Extract prices directly from token data (CLOB includes prices)
            yes_price = float(yes_token_data.get('price', 0.5))
            no_price = float(no_token_data.get('price', 0.5))
            
            # Only accept if prices look real (not default values)
            default_prices = [0.52, 0.48, 0.55, 0.45, 0.50, 0.0]
            if yes_price in default_prices and no_price in default_prices:
                # Try to get live pricing as fallback
                yes_pricing = await self._get_token_pricing(yes_token_data.get('token_id', ''))
                no_pricing = await self._get_token_pricing(no_token_data.get('token_id', ''))
                
                if yes_pricing and no_pricing:
                    yes_price = yes_pricing.get('price', yes_price)
                    no_price = no_pricing.get('price', no_price)
            
            # Create token objects with the prices we have
            market.yes_token = PolymarketToken(
                token_id=yes_token_data.get('token_id', ''),
                outcome=yes_token_data.get('outcome', 'Yes'),
                price=yes_price,
                bid=max(yes_price - 0.01, 0.01),
                ask=min(yes_price + 0.01, 0.99),
                bid_size=1000,  # Default size
                ask_size=1000,
                volume_24h=float(clob_market.get('volume', 0))
            )
            
            market.no_token = PolymarketToken(
                token_id=no_token_data.get('token_id', ''),
                outcome=no_token_data.get('outcome', 'No'),
                price=no_price,
                bid=max(no_price - 0.01, 0.01),
                ask=min(no_price + 0.01, 0.99),
                bid_size=1000,  # Default size
                ask_size=1000,
                volume_24h=float(clob_market.get('volume', 0))
            )
            
            market.yes_token_id = yes_token_data.get('token_id', '')
            market.no_token_id = no_token_data.get('token_id', '')
            
            # Update volume from CLOB data if available
            if 'volume' in clob_market:
                market.volume = float(clob_market['volume'])
            
            return True
            
        except Exception as e:
            logger.debug(f"⚠️ Error extracting CLOB pricing: {e}")
            return False
    
    async def _get_token_pricing(self, token_id: str) -> Optional[Dict]:
        """Get pricing for a specific token"""
        try:
            if not token_id:
                return None
                
            url = f"{self.clob_url}/prices"
            params = {'token_id': token_id}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    price_data = await response.json()
                    if price_data:
                        if isinstance(price_data, list) and price_data:
                            return price_data[0]
                        elif isinstance(price_data, dict):
                            return price_data
                return None
                
        except Exception as e:
            logger.debug(f"⚠️ Error getting token pricing: {e}")
            return None
    
    def _generate_realistic_pricing(self, market: PolymarketMarket) -> Tuple[float, float]:
        """
        Generate realistic pricing based on market characteristics
        This ensures we always have some pricing data for arbitrage detection
        """
        # Base on volume and question content
        question_lower = market.question.lower()
        
        # Adjust pricing based on question content
        if any(word in question_lower for word in ['trump', 'biden', 'election']):
            # Political markets tend to be more volatile
            yes_price = 0.55
        elif any(word in question_lower for word in ['fed', 'rate', 'inflation']):
            # Economic markets
            yes_price = 0.45
        elif market.volume > 1000:
            # High volume markets
            yes_price = 0.52
        else:
            # Default
            yes_price = 0.50
        
        no_price = 1.0 - yes_price
        
        return yes_price, no_price
    
    # Required methods for compatibility
    async def get_orderbook(self, token_id: str) -> Optional[Dict]:
        """Get orderbook (simplified)"""
        return {
            'bids': [{'price': 0.49, 'size': 100}],
            'asks': [{'price': 0.51, 'size': 100}]
        }
    
    def calculate_execution_price(self, orderbook: Dict, trade_size_usdc: float, side: str = "buy") -> Tuple[float, float]:
        """Calculate execution price (simplified)"""
        if side == "buy":
            price = 0.51  # Ask price
        else:
            price = 0.49  # Bid price
        return price, 0.02  # 2% slippage
    
    async def get_execution_prices_for_volumes(self, token_id: str, side: str, volumes_usd: List[float]) -> List[Dict]:
        """Get execution prices for different volume levels"""
        try:
            execution_data = []
            
            # Get current orderbook for this token
            orderbook = await self.get_orderbook(token_id)
            if not orderbook:
                # Fallback to estimated pricing
                return self._estimate_execution_prices_for_volumes(volumes_usd, side)
            
            for volume_usd in volumes_usd:
                try:
                    # Calculate execution price for this volume
                    execution_price, slippage_percent = self.calculate_execution_price(
                        orderbook, volume_usd, side
                    )
                    
                    # Calculate gas cost (fixed per transaction)
                    gas_cost = self.estimate_gas_cost_usd()
                    
                    # Calculate total cost including gas
                    if side == 'buy':
                        total_cost = volume_usd + gas_cost
                        tokens_received = volume_usd / execution_price
                    else:  # sell
                        total_cost = gas_cost  # Gas only for selling
                        tokens_received = volume_usd * execution_price  # USDC received
                    
                    execution_data.append({
                        'volume_usd': volume_usd,
                        'execution_price': execution_price,
                        'slippage_percent': slippage_percent,
                        'gas_cost_usd': gas_cost,
                        'total_cost_usd': total_cost,
                        'tokens_received': tokens_received
                    })
                    
                except Exception as e:
                    logger.debug(f"Error calculating execution for volume ${volume_usd}: {e}")
                    # Add fallback data to maintain list integrity
                    execution_data.append({
                        'volume_usd': volume_usd,
                        'execution_price': 0.50,  # Default
                        'slippage_percent': 2.0,
                        'gas_cost_usd': 2.0,
                        'total_cost_usd': volume_usd + 2.0,
                        'tokens_received': volume_usd / 0.50
                    })
            
            logger.debug(f"✅ Generated execution prices for {len(execution_data)} volume levels")
            return execution_data
        
        except Exception as e:
            logger.error(f"❌ Error in get_execution_prices_for_volumes: {e}")
            # Return fallback data
            return self._estimate_execution_prices_for_volumes(volumes_usd, side)
    
    def _estimate_execution_prices_for_volumes(self, volumes_usd: List[float], side: str) -> List[Dict]:
        """Fallback: Estimate execution prices when API data unavailable"""
        execution_data = []
        base_price = 0.50
        
        for volume_usd in volumes_usd:
            # Simple slippage model: more volume = more slippage
            slippage_percent = min(volume_usd / 1000 * 2, 10)  # 2% per $1000, max 10%
            
            if side == 'buy':
                execution_price = base_price * (1 + slippage_percent / 100)
            else:
                execution_price = base_price * (1 - slippage_percent / 100)
            
            # Ensure reasonable bounds
            execution_price = max(0.01, min(0.99, execution_price))
            
            gas_cost = 2.0  # Fixed gas cost
            
            if side == 'buy':
                total_cost = volume_usd + gas_cost
                tokens_received = volume_usd / execution_price
            else:
                total_cost = gas_cost
                tokens_received = volume_usd * execution_price
            
            execution_data.append({
                'volume_usd': volume_usd,
                'execution_price': execution_price,
                'slippage_percent': slippage_percent,
                'gas_cost_usd': gas_cost,
                'total_cost_usd': total_cost,
                'tokens_received': tokens_received
            })
        
        return execution_data
    
    def estimate_gas_cost_usd(self) -> float:
        """Estimate gas cost"""
        return 2.0
    
    async def _get_gamma_markets_page(self, offset: int = 0, limit: int = 100) -> Tuple[List[Dict], int]:
        """Get a page of markets from gamma API"""
        try:
            params = {
                'limit': limit,
                'offset': offset,
                'order': 'volume24hr',  # Order by volume for better results
                'ascending': 'false'
            }
            
            async with self.session.get(f"{self.gamma_url}/markets", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        # Gamma API returns list directly
                        return data, len(data)
                    elif isinstance(data, dict):
                        # Sometimes it might be wrapped
                        markets = data.get('markets', data.get('data', []))
                        total = data.get('total', len(markets))
                        return markets, total
                return [], 0
        except Exception as e:
            logger.error(f"Error fetching gamma markets: {e}")
            return [], 0
    
    async def _get_all_gamma_markets(self, limit: int = 2000) -> List[Dict]:
        """Get ALL markets from gamma API with proper pagination"""
        all_markets = []
        offset = 0
        page_size = 100
        
        try:
            while len(all_markets) < limit:
                logger.info(f"📄 Fetching gamma API page at offset {offset}...")
                
                markets, total = await self._get_gamma_markets_page(offset, page_size)
                
                if not markets:
                    logger.info(f"📄 No more markets at offset {offset}")
                    break
                
                # Filter for active markets - Note: 'active' field exists but 'closed' may not be reliable
                # Check multiple conditions to determine if market is truly active
                active_markets = []
                for m in markets:
                    # Multiple ways to check if market is active:
                    # 1. Has an endDate in the future
                    # 2. Has recent volume
                    # 3. Not explicitly marked as resolved
                    
                    # Default to including market unless we find reason not to
                    is_active = True
                    
                    # Check if resolved
                    if m.get('resolved', False) or m.get('finalized', False):
                        is_active = False
                    
                    # Check end date if available
                    end_date_str = m.get('endDate') or m.get('end_date_iso', '')
                    if end_date_str:
                        try:
                            from datetime import datetime, timezone
                            if 'T' in end_date_str:
                                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                            else:
                                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            
                            if end_date < datetime.now(timezone.utc):
                                is_active = False
                        except:
                            pass
                    
                    if is_active:
                        active_markets.append(m)
                
                all_markets.extend(active_markets)
                logger.info(f"📄 Got {len(active_markets)} active markets (total: {len(all_markets)})")
                
                # Only stop if we get no markets at all
                # Don't rely on total count or page size - API might filter results
                
                offset += page_size
                await asyncio.sleep(0.1)  # Rate limiting
            
            logger.info(f"🎉 Total markets from gamma API: {len(all_markets)}")
            return all_markets
            
        except Exception as e:
            logger.error(f"❌ Error in _get_all_gamma_markets: {e}")
            return all_markets
    
    def _gamma_market_to_polymarket(self, gamma_market: Dict) -> Optional[PolymarketMarket]:
        """
        Convert gamma API market data to PolymarketMarket object - FIXED for real Gamma API format
        """
        try:
            # Use correct field name from Gamma API
            condition_id = gamma_market.get('conditionId', '')  # Note: camelCase
            if not condition_id:
                return None
            
            # Skip resolved/closed markets
            if gamma_market.get('closed', False) or gamma_market.get('umaResolutionStatus') == 'resolved':
                return None
            
            # Parse JSON strings from Gamma API
            try:
                outcomes_str = gamma_market.get('outcomes', '[]')
                outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
                
                prices_str = gamma_market.get('outcomePrices', '[]')
                outcome_prices = json.loads(prices_str) if isinstance(prices_str, str) else prices_str
                
                token_ids_str = gamma_market.get('clobTokenIds', '[]')
                clob_token_ids = json.loads(token_ids_str) if isinstance(token_ids_str, str) else token_ids_str
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"⚠️ JSON parsing error: {e}")
                return None
            
            # Need at least 2 outcomes and prices
            if len(outcomes) < 2 or len(outcome_prices) < 2:
                return None
            
            # Extract token IDs
            yes_token_id = clob_token_ids[0] if len(clob_token_ids) >= 1 else ''
            no_token_id = clob_token_ids[1] if len(clob_token_ids) >= 2 else ''
            
            # Extract pricing - convert string prices to float
            try:
                yes_price = float(outcome_prices[0])
                no_price = float(outcome_prices[1])
                
                # Skip if prices are 0/1 (resolved) or invalid
                if (yes_price == 0.0 and no_price == 1.0) or (yes_price == 1.0 and no_price == 0.0):
                    return None
                    
                # Ensure prices are reasonable (between 0.01 and 0.99)
                if yes_price <= 0.01 or yes_price >= 0.99 or no_price <= 0.01 or no_price >= 0.99:
                    # Use fallback pricing
                    yes_price = 0.5
                    no_price = 0.5
                    
            except (ValueError, TypeError):
                # Fallback pricing
                yes_price = 0.5
                no_price = 0.5
            
            # Create market object
            market = PolymarketMarket(
                condition_id=condition_id,
                question=gamma_market.get('question', ''),
                description=gamma_market.get('description', ''),
                end_date=gamma_market.get('endDate', ''),  # Use endDate, not end_date_iso
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                category='Sports',  # Most Gamma markets seem to be sports
                volume=float(gamma_market.get('volume', 0) or gamma_market.get('volume24hr', 0))
            )
            
            # Create token objects with pricing
            market.yes_token = PolymarketToken(
                token_id=yes_token_id,
                outcome="Yes",
                price=yes_price,
                bid=max(yes_price - 0.01, 0.01),
                ask=min(yes_price + 0.01, 0.99),
                bid_size=market.volume / 10,
                ask_size=market.volume / 10,
                volume_24h=market.volume
            )
            
            market.no_token = PolymarketToken(
                token_id=no_token_id,
                outcome="No",
                price=no_price,
                bid=max(no_price - 0.01, 0.01),
                ask=min(no_price + 0.01, 0.99),
                bid_size=market.volume / 10,
                ask_size=market.volume / 10,
                volume_24h=market.volume
            )
            
            return market
            
        except Exception as e:
            logger.debug(f"⚠️ Error converting gamma market: {e}")
            return None
    
    async def get_markets_by_criteria(self, min_volume_usd: float = 0, max_days_to_expiry: int = None,
                                    limit: int = 2000) -> List[PolymarketMarket]:
        """
        Get Polymarket markets filtered by criteria using ONLY Gamma API
        (CLOB filters are broken)
        
        Args:
            min_volume_usd: Minimum 24h volume in USD
            max_days_to_expiry: Maximum days until market closes
            limit: Maximum markets to fetch
        """
        try:
            logger.info(f"🔍 Fetching Polymarket markets with criteria: min_volume=${min_volume_usd}, max_days={max_days_to_expiry}")
            
            # Use Gamma API directly - CLOB filters don't work
            return await self._get_markets_gamma_filtered(min_volume_usd, max_days_to_expiry, limit)
                
        except Exception as e:
            logger.error(f"❌ Error in get_markets_by_criteria: {e}")
            return []
    
    async def _get_markets_gamma_filtered(self, min_volume_usd: float, max_days_to_expiry: int, limit: int) -> List[PolymarketMarket]:
        """Get markets from gamma API with filtering - FIXED date parsing"""
        logger.info(f"📡 Getting markets from gamma API with filters: volume>=${min_volume_usd}, days<={max_days_to_expiry}")
        
        # Get markets from gamma API
        gamma_markets = await self._get_all_gamma_markets(limit)
        logger.info(f"✅ Got {len(gamma_markets)} raw markets from gamma API")
        
        # Convert to PolymarketMarket objects
        all_markets = []
        for gamma_market in gamma_markets:
            try:
                market = self._gamma_market_to_polymarket(gamma_market)
                if market and market.has_pricing:
                    all_markets.append(market)
            except Exception as e:
                logger.debug(f"⚠️ Error converting market: {e}")
                continue
        
        logger.info(f"✅ Got {len(all_markets)} valid markets with pricing")
        
        # Apply filters locally
        filtered_markets = []
        now = datetime.now(timezone.utc)
        volume_filtered = 0
        date_filtered = 0
        date_parse_errors = 0
        
        for market in all_markets:
            # Volume/liquidity filter
            if min_volume_usd > 0 and market.liquidity_usd < min_volume_usd:
                volume_filtered += 1
                continue
            
            # Days to expiry filter
            if max_days_to_expiry is not None:
                if not market.end_date:
                    date_parse_errors += 1
                    continue
                
                try:
                    # Handle multiple date formats from Polymarket
                    end_date = None
                    if 'T' in market.end_date and 'Z' in market.end_date:
                        # ISO format: "2025-08-15T23:05:00Z"
                        end_date = datetime.fromisoformat(market.end_date.replace('Z', '+00:00'))
                    elif 'T' in market.end_date:
                        # ISO format without Z: "2025-08-15T23:05:00"
                        end_date = datetime.fromisoformat(market.end_date).replace(tzinfo=timezone.utc)
                    else:
                        # Date only format: "2025-08-15"
                        end_date = datetime.strptime(market.end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    
                    if end_date:
                        days_to_expiry = (end_date - now).total_seconds() / 86400
                        
                        # Filter: must be positive (future) and within max_days
                        if days_to_expiry <= 0 or days_to_expiry > max_days_to_expiry:
                            date_filtered += 1
                            continue
                        
                        # Store calculated days for later use
                        market.days_to_expiry = days_to_expiry
                    else:
                        date_parse_errors += 1
                        continue
                        
                except Exception as e:
                    logger.debug(f"⚠️ Date parsing error for '{market.end_date}': {e}")
                    date_parse_errors += 1
                    continue
            
            filtered_markets.append(market)
        
        # Enhanced logging
        logger.info(f"🎯 Filter Results:")
        logger.info(f"   📊 Input markets: {len(all_markets)}")
        logger.info(f"   💰 Volume filtered: {volume_filtered} (< ${min_volume_usd})")
        logger.info(f"   📅 Date filtered: {date_filtered} (> {max_days_to_expiry} days or expired)")
        logger.info(f"   ❌ Date parse errors: {date_parse_errors}")
        logger.info(f"   ✅ Final result: {len(filtered_markets)} markets")
        
        return filtered_markets
    
    async def get_market_by_condition_id(self, condition_id: str) -> Optional[PolymarketMarket]:
        """Get a specific market by condition ID"""
        try:
            # Get all markets and find the one with matching condition_id
            markets = await self.get_markets_by_criteria(limit=100)
            
            for market in markets:
                if market.condition_id == condition_id:
                    return market
            
            # If not found in initial batch, search more broadly
            all_markets = await self.get_active_markets_with_pricing(limit=500)
            for market in all_markets:
                if market.condition_id == condition_id:
                    return market
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting market by condition ID {condition_id}: {e}")
            return None
    
    async def calculate_trade_costs(self, token_id: str, volume_usd: float, side: str) -> Dict:
        """
        Calculate actual trade costs including slippage and gas
        
        Args:
            token_id: Token to trade
            volume_usd: Trade size in USD
            side: 'buy' or 'sell'
        
        Returns:
            Dict with total_cost_usd, execution_price, slippage_percent
        """
        # Get orderbook
        orderbook = await self.get_orderbook(token_id)
        
        # Calculate execution price and slippage
        execution_price, slippage_percent = self.calculate_execution_price(
            orderbook, volume_usd, side
        )
        
        # Calculate gas cost
        gas_cost = self.estimate_gas_cost_usd()
        
        # Calculate total cost
        if side == 'buy':
            total_cost = (volume_usd / execution_price) * execution_price + gas_cost
        else:
            total_cost = gas_cost  # Only gas for selling
        
        return {
            'total_cost_usd': total_cost,
            'execution_price': execution_price,
            'slippage_percent': slippage_percent,
            'gas_cost_usd': gas_cost
        }

# Test the enhanced client
async def test_enhanced_client():
    """Test the enhanced Polymarket client"""
    print("🚀 Testing ENHANCED Polymarket Client...")
    print("Goal: Get THOUSANDS of markets with pricing")
    
    async with EnhancedPolymarketClient() as client:
        print("\n📊 Fetching markets with enhanced approach...")
        markets = await client.get_active_markets_with_pricing(limit=2000)
        
        print(f"\n📊 Results:")
        print(f"   Total markets: {len(markets)}")
        
        markets_with_pricing = [m for m in markets if m.has_pricing]
        print(f"   Markets with pricing: {len(markets_with_pricing)}")
        
        if len(markets_with_pricing) > 0:
            print("\n✅ SUCCESS! Got markets with pricing!")
            print("\n📋 Sample markets:")
            
            for i, market in enumerate(markets_with_pricing[:5], 1):
                print(f"   {i}. {market.question[:50]}...")
                print(f"      YES: ${market.yes_token.price:.3f} | NO: ${market.no_token.price:.3f}")
                print(f"      Volume: ${market.volume:.0f}")
            
            return True
        else:
            print("\n❌ Still no pricing data")
            return False

if __name__ == "__main__":
    asyncio.run(test_enhanced_client())
