#!/usr/bin/env python3
"""
Kalshi API Client - Fixed Private Key Loading
"""

import os
import time
import json
import requests
import base64
from datetime import datetime
from typing import List, Dict, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from dotenv import load_dotenv

class KalshiClient:
    """Kalshi API client for arbitrage detection"""
    
    def __init__(self, verbose: bool = True):
        load_dotenv()
        
        self.api_key_id = os.getenv('KALSHI_API_KEY_ID')
        self.verbose = verbose
        
        # Use environment setting from .env
        environment = os.getenv('ENVIRONMENT', 'DEMO').upper()
        if environment == 'PRODUCTION':
            self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
            if self.verbose:
                print("🎯 Using PRODUCTION Kalshi API")
        else:
            self.base_url = "https://demo-api.kalshi.co/trade-api/v2"
            if self.verbose:
                print("🎯 Using DEMO Kalshi API")
        
        self.private_key = None
        self.session = requests.Session()
        
        if self.verbose:
            print("🔍 Initializing KalshiClient...")
        self._load_private_key()
        self._test_connection()
    
    def _load_private_key(self):
        """Load private key with multiple methods"""
        if self.verbose:
            print("🔍 Loading private key...")
        
        # Method 1: Try loading from separate file (recommended)
        # Updated path to keys directory
        key_file = os.getenv('KALSHI_PRIVATE_KEY_FILE', 'keys/kalshi-private-key.pem')
        if not os.path.exists(key_file):
            # Try from root directory as fallback
            key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), key_file)
        if os.path.exists(key_file):
            if self.verbose:
                print(f"🔍 Loading from file: {key_file}")
            try:
                with open(key_file, 'r') as f:
                    key_content = f.read()
                self.private_key = serialization.load_pem_private_key(
                    key_content.encode('utf-8'),
                    password=None
                )
                if self.verbose:
                    print("✅ Private key loaded from file successfully")
                return
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Failed to load from file: {e}")
        
        # Method 2: Try loading from environment variable
        private_key_str = os.getenv('KALSHI_PRIVATE_KEY')
        if private_key_str:
            try:
                # Fix common formatting issues
                fixed_key = self._fix_private_key_format(private_key_str)
                
                self.private_key = serialization.load_pem_private_key(
                    fixed_key.encode('utf-8'),
                    password=None
                )
                if self.verbose:
                    print("✅ Private key loaded from environment successfully")
                return
                
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Failed to load from environment: {e}")
        
        raise ValueError("Could not load private key from file or environment")
    
    def _fix_private_key_format(self, key_str: str) -> str:
        """Fix common private key formatting issues"""
        # Remove any quotes
        key_str = key_str.strip('"\'')
        
        # Fix literal \n characters
        if '\\n' in key_str:
            key_str = key_str.replace('\\n', '\n')
        
        return key_str
    
    def _test_connection(self):
        """Test basic connection"""
        if self.verbose:
            print("🔍 Testing connection...")
        try:
            response = self.session.get(f"{self.base_url}/exchange/status", timeout=10)
            if response.status_code == 200:
                if self.verbose:
                    print("✅ Basic connection successful")
            else:
                if self.verbose:
                    print(f"⚠️ Unexpected status: {response.status_code}")
        except Exception as e:
            if self.verbose:
                print(f"❌ Connection test failed: {e}")
    
    def _sign_request(self, method: str, path: str, timestamp: str, body: str = "") -> str:
        """Sign request for authentication"""
        message = timestamp + method.upper() + path + body
        message_bytes = message.encode('utf-8')
        
        signature = self.private_key.sign(
            message_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _make_authenticated_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make authenticated request to Kalshi API"""
        try:
            path = f"/trade-api/v2{endpoint}"
            timestamp_str = str(int(time.time() * 1000))
            body = json.dumps(data) if data else ""
            
            signature = self._sign_request(method, path, timestamp_str, body)
            
            headers = {
                'KALSHI-ACCESS-KEY': self.api_key_id,
                'KALSHI-ACCESS-SIGNATURE': signature,
                'KALSHI-ACCESS-TIMESTAMP': timestamp_str,
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}{endpoint}"
            
            if self.verbose:
                print(f"🔗 URL: {url}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, data=body, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if self.verbose and response.status_code != 200:
                print(f"⚠️ Response status: {response.status_code}")
                print(f"⚠️ Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None
    
    # Removed series/events methods since the API doesn't support that hierarchy
    # Using direct /markets endpoint instead
    
    def get_all_markets(self, status: str = None, limit: int = 1000, min_volume: int = 0) -> List[Dict]:
        """Get ALL markets using direct endpoint with pagination
        
        Args:
            status: Filter by status (applied after fetching)
            limit: Markets per page (max 1000)
            min_volume: Minimum volume filter (default 0)
        """
        try:
            all_markets = []
            seen_tickers = set()  # Track unique markets
            cursor = None
            page = 1
            max_pages = 200  # Safety limit - 200k markets max (but should stop much earlier)
            
            if self.verbose:
                print(f"📡 Fetching ALL markets with pagination...")
            
            while page <= max_pages:
                # Build URL with parameters
                params = [f"limit={limit}"]  # Max per page
                if cursor:
                    params.append(f"cursor={cursor}")
                
                endpoint = f"/markets?{'&'.join(params)}"
                response = self._make_authenticated_request("GET", endpoint)
                
                if not response or 'markets' not in response:
                    if page == 1 and self.verbose:
                        print("❌ Failed to get markets")
                    break
                
                markets = response['markets']
                if not markets:  # Empty page = done
                    break
                
                # Add only new markets (avoid duplicates) and apply volume filter
                new_markets_count = 0
                for market in markets:
                    ticker = market.get('ticker')
                    volume = market.get('volume', 0)
                    
                    if ticker and ticker not in seen_tickers and volume >= min_volume:
                        seen_tickers.add(ticker)
                        all_markets.append(market)
                        new_markets_count += 1
                
                if self.verbose:
                    print(f"📊 Page {page}: Got {len(markets)} markets ({new_markets_count} new) - Total unique: {len(all_markets)}")
                
                # Check for more pages
                new_cursor = response.get('cursor')
                if not new_cursor or new_cursor == cursor or new_markets_count == 0:
                    # No more data or stuck in loop
                    if self.verbose:
                        print("✅ Reached end of markets")
                    break
                
                cursor = new_cursor
                page += 1
            
            if self.verbose:
                print(f"🎉 TOTAL MARKETS FETCHED: {len(all_markets)}")
                
                # Show category breakdown
                categories = {}
                for market in all_markets:
                    cat = market.get('category', 'Unknown')
                    categories[cat] = categories.get(cat, 0) + 1
                
                print(f"📊 Categories found:")
                for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"   {cat}: {count}")
            
            return all_markets
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Error fetching markets: {e}")
            return []
    
    def get_active_markets(self, min_volume: int = 0) -> List[Dict]:
        """Get all markets and filter for active ones
        
        Args:
            min_volume: Minimum volume filter (default 0)
                       For dollar volume, use volume * average_price
                       E.g., 1,000,000 for $1M+ volume markets
        """
        # Get all markets with volume filter
        all_markets = self.get_all_markets(min_volume=min_volume)
        
        # Filter for active markets after fetching
        # Check what status values Kalshi actually uses
        active_markets = [m for m in all_markets if m.get('status', '').lower() in ['active', 'open', 'trading', 'live']]
        
        if len(active_markets) == 0 and len(all_markets) > 0:
            # If no active markets found, check what statuses we have
            statuses = set(m.get('status', 'unknown') for m in all_markets)
            print(f"⚠️ No active/open markets found. Available statuses: {statuses}")
            # Use all markets regardless of status
            active_markets = all_markets
        
        if self.verbose:
            print(f"Filtered to {len(active_markets)} active/open markets")
            if min_volume > 0:
                print(f"Volume filter: >= {min_volume:,}")
        
        return active_markets
    
    def get_markets_by_criteria(self, min_liquidity_usd: float = 0, max_days_to_expiry: int = None, 
                               min_volume: int = 0, status_filter: List[str] = None,
                               min_bid_ask_sum: int = 0, debug: bool = False) -> List[Dict]:
        """Get ALL markets filtered by criteria - optimized for arbitrage detection
        
        Args:
            min_liquidity_usd: Minimum liquidity in USD (orderbook depth)
            max_days_to_expiry: Maximum days until market closes
            min_volume: Minimum volume (number of contracts)
            status_filter: List of acceptable statuses (default: None - accept all)
            min_bid_ask_sum: Minimum bid+ask sum in cents (e.g., 180 = 90% combined)
            debug: Enable detailed debug logging
        
        Returns:
            List of market dicts with enhanced fields for arbitrage matching:
            - ticker, title, close_time, days_to_expiry
            - yes_bid, yes_ask, no_bid, no_ask (in cents)
            - liquidity_usd, volume, status
            - yes_price, no_price (mid prices in dollars)
            - spread_yes, spread_no (bid-ask spreads)
        """
        # Don't filter by status by default since Kalshi returns 'initialized' which isn't documented
        if status_filter is None:
            status_filter = []  # Accept all statuses
        
        if debug or self.verbose:
            print(f"\n🔍 ENHANCED MARKET FILTERING - Getting ALL markets within criteria")
            print(f"   Max days to expiry: {max_days_to_expiry}")
            print(f"   Min liquidity: ${min_liquidity_usd:,.0f}")
            print(f"   Min volume: {min_volume:,}")
            print(f"   Min bid+ask sum: {min_bid_ask_sum}¢")
            print(f"   Status filter: {status_filter or 'All statuses'}")
        
        # Track statistics
        stats = {
            'total_fetched': 0,
            'filtered_by_status': 0,
            'filtered_by_volume': 0,
            'filtered_by_liquidity': 0,
            'filtered_by_spread': 0,
            'passed_all_filters': 0
        }
        
        # Use timestamp filtering if max_days_to_expiry is specified
        if max_days_to_expiry is not None:
            now = int(time.time())
            max_close_ts = now + (max_days_to_expiry * 86400)
            
            all_markets = []
            seen_tickers = set()  # Track unique markets
            cursor = None
            page = 1
            max_pages = 50  # Increased limit to ensure we get all markets
            
            if debug:
                print(f"\n📅 Fetching markets closing between now and {max_days_to_expiry} days...")
            
            while page <= max_pages:
                params = [
                    "limit=1000",
                    f"min_close_ts={now}",
                    f"max_close_ts={max_close_ts}"
                ]
                if cursor:
                    params.append(f"cursor={cursor}")
                
                endpoint = f"/markets?{'&'.join(params)}"
                response = self._make_authenticated_request("GET", endpoint)
                
                if not response or 'markets' not in response:
                    if debug:
                        print(f"   Page {page}: No response or markets")
                    break
                
                markets = response['markets']
                if not markets:
                    if debug:
                        print(f"   Page {page}: Empty markets list")
                    break
                
                # Add only unique markets
                new_count = 0
                for market in markets:
                    ticker = market.get('ticker')
                    if ticker and ticker not in seen_tickers:
                        seen_tickers.add(ticker)
                        all_markets.append(market)
                        new_count += 1
                
                if debug:
                    print(f"   Page {page}: {len(markets)} markets ({new_count} new), Total: {len(all_markets)}")
                
                new_cursor = response.get('cursor')
                if not new_cursor or new_cursor == cursor or new_count == 0:
                    if debug:
                        print(f"   ✓ Reached end of results")
                    break
                
                cursor = new_cursor
                page += 1
        else:
            # Get all markets
            all_markets = self.get_all_markets(min_volume=min_volume)
        
        stats['total_fetched'] = len(all_markets)
        
        if debug:
            print(f"\n📦 Total markets fetched: {stats['total_fetched']}")
            print(f"\n🎯 Applying filters...")
        
        # Apply filters
        filtered_markets = []
        for market in all_markets:
            # Status filter
            if status_filter and market.get('status'):
                market_status = market.get('status', '').lower()
                # Check if market status matches any of our filter statuses
                if not any(status.lower() in market_status for status in status_filter):
                    stats['filtered_by_status'] += 1
                    continue
            
            # Volume filter
            if min_volume > 0 and market.get('volume', 0) < min_volume:
                stats['filtered_by_volume'] += 1
                continue
            
            # Get price data
            yes_bid = market.get('yes_bid', 0)
            yes_ask = market.get('yes_ask', 0)
            no_bid = market.get('no_bid', 0)
            no_ask = market.get('no_ask', 0)
            
            # Calculate true liquidity: Volume × Average Price
            # The 'liquidity' field from API seems incorrect, so we calculate it
            volume = market.get('volume', 0)
            
            # Get average price (YES price since YES + NO = $1)
            yes_bid = market.get('yes_bid', 0)
            yes_ask = market.get('yes_ask', 0)
            if yes_bid > 0 and yes_ask > 0:
                avg_price = (yes_bid + yes_ask) / 200.0  # Convert cents to dollars
            else:
                avg_price = 0.5  # Default to 50 cents if no price data
            
            # True liquidity in USD
            liquidity_usd = volume * avg_price
            
            # Apply liquidity filter
            if min_liquidity_usd > 0 and liquidity_usd < min_liquidity_usd:
                # Check bid/ask sum as alternative liquidity measure
                if min_bid_ask_sum > 0:
                    yes_sum = yes_bid + yes_ask
                    no_sum = no_bid + no_ask
                    
                    # If neither YES nor NO has tight spread, skip
                    if yes_sum < min_bid_ask_sum and no_sum < min_bid_ask_sum:
                        stats['filtered_by_spread'] += 1
                        continue
                else:
                    stats['filtered_by_liquidity'] += 1
                    continue
            
            # Market passed all filters - enhance with computed fields
            market['liquidity_usd'] = liquidity_usd  # This is now correctly calculated as volume * avg_price
            market['liquidity_api'] = market.get('liquidity', 0)  # Keep original API value for reference
            
            # Add mid prices in dollars for easy comparison
            if yes_bid > 0 and yes_ask > 0:
                market['yes_price'] = (yes_bid + yes_ask) / 200.0  # Convert cents to dollars
            else:
                market['yes_price'] = yes_ask / 100.0 if yes_ask > 0 else 0
            
            if no_bid > 0 and no_ask > 0:
                market['no_price'] = (no_bid + no_ask) / 200.0
            else:
                market['no_price'] = no_ask / 100.0 if no_ask > 0 else 0
            
            # Add spreads for liquidity assessment
            market['spread_yes'] = yes_ask - yes_bid if (yes_ask > 0 and yes_bid > 0) else 999
            market['spread_no'] = no_ask - no_bid if (no_ask > 0 and no_bid > 0) else 999
            
            # Calculate days to expiry if close_time exists
            close_time_str = market.get('close_time', '')
            if close_time_str:
                try:
                    from datetime import datetime, timezone
                    close_time = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    days_to_expiry = (close_time - now).total_seconds() / 86400
                    market['days_to_expiry'] = days_to_expiry
                    
                    # Add formatted close date for readability
                    market['close_date'] = close_time.strftime('%Y-%m-%d %H:%M UTC')
                except:
                    market['days_to_expiry'] = None
                    market['close_date'] = 'Unknown'
            
            # Add to filtered list
            filtered_markets.append(market)
            stats['passed_all_filters'] += 1
        
        # Sort by days to expiry (soonest first) for prioritization
        filtered_markets.sort(key=lambda x: x.get('days_to_expiry', 999))
        
        if debug or self.verbose:
            print(f"\n📨 FILTERING RESULTS:")
            print(f"   Total markets fetched: {stats['total_fetched']}")
            print(f"   Filtered by status: {stats['filtered_by_status']}")
            print(f"   Filtered by volume: {stats['filtered_by_volume']}")
            print(f"   Filtered by liquidity: {stats['filtered_by_liquidity']}")
            print(f"   Filtered by spread: {stats['filtered_by_spread']}")
            print(f"   ✔️  PASSED ALL FILTERS: {stats['passed_all_filters']}")
            
            if filtered_markets and debug:
                print(f"\n🎆 Sample of filtered markets (first 5):")
                for i, m in enumerate(filtered_markets[:5]):
                    print(f"\n   {i+1}. {m['ticker']}")
                    print(f"      Title: {m.get('title', '')[:60]}...")
                    print(f"      Days to expiry: {m.get('days_to_expiry', 'N/A'):.1f}")
                    print(f"      YES: ${m.get('yes_price', 0):.2f} ({m.get('yes_bid')}/{m.get('yes_ask')}¢)")
                    print(f"      NO: ${m.get('no_price', 0):.2f} ({m.get('no_bid')}/{m.get('no_ask')}¢)")
                    print(f"      Liquidity: ${m.get('liquidity_usd', 0):,.0f}")
                    print(f"      Volume: {m.get('volume', 0):,}")
        
        return filtered_markets
    
    def get_market_orderbook(self, ticker: str) -> Optional[Dict]:
        """Get orderbook for a specific market"""
        try:
            response = self._make_authenticated_request("GET", f"/markets/{ticker}/orderbook")
            return response
        except Exception as e:
            if self.verbose:
                print(f"❌ Error fetching orderbook for {ticker}: {e}")
            return None
    
    def get_markets_direct(self, limit: int = 1000, cursor: str = None, status: str = None) -> Dict:
        """Direct API call to markets endpoint - returns raw response"""
        try:
            params = []
            # NOTE: status parameter not supported by Kalshi API
            if limit:
                params.append(f"limit={limit}")
            if cursor:
                params.append(f"cursor={cursor}")
            
            endpoint = "/markets"
            if params:
                endpoint += "?" + "&".join(params)
            
            return self._make_authenticated_request("GET", endpoint)
        except Exception as e:
            if self.verbose:
                print(f"❌ Error in get_markets_direct: {e}")
            return {}
    
    def get_market_price(self, ticker: str) -> Optional[Dict]:
        """Get current pricing for a specific market"""
        try:
            # Get market details which include current pricing
            response = self._make_authenticated_request("GET", f"/markets/{ticker}")
            if response and 'market' in response:
                market = response['market']
                
                # Try both yes_price and yes_ask (different API versions)
                yes_price = market.get('yes_price')
                no_price = market.get('no_price')
                
                # If prices are None, try ask prices
                if yes_price is None:
                    yes_price = market.get('yes_ask', 0)
                if no_price is None:
                    no_price = market.get('no_ask', 0)
                
                return {
                    'ticker': ticker,
                    'yes_price': yes_price / 100 if yes_price else 0,  # Convert from cents
                    'no_price': no_price / 100 if no_price else 0,
                    'volume': market.get('volume', 0),
                    'open_interest': market.get('open_interest', 0),
                    'status': market.get('status', '')
                }
            return None
        except Exception as e:
            if self.verbose:
                print(f"❌ Error fetching price for {ticker}: {e}")
            return None
    
    # Backward compatibility
    def get_markets(self, limit_per_page: int = 1000, status: str = None) -> List[Dict]:
        """Backward compatibility wrapper for get_all_markets"""
        markets = self.get_all_markets(status=None, limit=limit_per_page)
        # If status was provided, filter after fetching
        if status:
            return [m for m in markets if m.get('status', '').lower() == status.lower()]
        return markets
    
    def place_order(self, ticker: str, side: str, action: str, count: int, 
                   order_type: str = "limit", price: float = None) -> Optional[Dict]:
        """Place an order on Kalshi"""
        if order_type == "limit" and price is None:
            raise ValueError("Limit orders require a price")
        
        order_data = {
            "ticker": ticker,
            "side": side, 
            "action": action,
            "count": count,
            "type": order_type
        }
        
        if price is not None:
            order_data["price"] = int(price * 100)  # Kalshi uses cents
        
        if self.verbose:
            print(f"📝 Placing order: {action} {count} {ticker} {side} @ ${price}")
        
        response = self._make_authenticated_request("POST", "/portfolio/orders", order_data)
        
        if response:
            if self.verbose:
                print(f"✅ Order placed successfully")
            return response
        else:
            if self.verbose:
                print(f"❌ Order placement failed")
            return None
    
    def get_market(self, ticker: str) -> Optional[Dict]:
        """Get market details by ticker"""
        try:
            response = self._make_authenticated_request("GET", f"/markets/{ticker}")
            if response and 'market' in response:
                return response['market']
            return None
        except Exception as e:
            if self.verbose:
                print(f"❌ Error fetching market {ticker}: {e}")
            return None
    
    def get_balance(self) -> Optional[float]:
        """Get account balance"""
        try:
            response = self._make_authenticated_request("GET", "/portfolio/balance")
            if response:
                return response.get('balance', 0) / 100  # Convert from cents
            return None
        except Exception as e:
            if self.verbose:
                print(f"❌ Error fetching balance: {e}")
            return None


# Simple test
if __name__ == "__main__":
    print("🚀 Testing Kalshi API client...")
    client = KalshiClient()
    
    # Test getting markets
    markets = client.get_active_markets()
    print(f"📊 Found {len(markets)} active markets")
    
    if markets:
        # Show sample
        print("\n📝 Sample markets:")
        for i, market in enumerate(markets[:5]):
            print(f"{i+1}. {market.get('ticker')}: {market.get('title')}")
    
    # Test balance
    balance = client.get_balance()
    if balance is not None:
        print(f"\n💰 Account balance: ${balance:.2f}")