"""
Cross-Asset Arbitrage Scanner
Identifies arbitrage opportunities between Kalshi S&P contracts and SPXW options

Key Features:
- Uses SPXW (weekly SPX with 4 PM settlement) to match Kalshi
- Short strike MUST be AT the Kalshi level for perfect hedge
- Provides theta decay notes based on time of day
"""
import logging
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional, Tuple
import math
from scipy.stats import norm

from src.data_collectors.kalshi_client import KalshiClient
from src.data_collectors.ibkr_options_client import IBKROptionsClient

logger = logging.getLogger(__name__)


class CrossAssetScanner:
    """Scans for arbitrage between Kalshi S&P predictions and SPXW options
    
    Time-aware behavior:
    - Production mode: Only scans until 2:45 PM CT (3:45 PM ET)
    - Testing mode: After 3:45 PM ET, automatically looks for tomorrow's contracts
    - Target: S&P 500 contracts expiring at 4 PM ET (KXINXU series)
    
    Option Strategy Rules:
    - Kalshi "over X": Sell X call, Buy (X+10) call (bear call spread)
    - Kalshi "under X": Sell X put, Buy (X-10) put (bull put spread)
    - ALWAYS place short strike AT the Kalshi level!
    """
    
    def __init__(self, kalshi_client: KalshiClient, ibkr_client: IBKROptionsClient, testing_mode: bool = False):
        self.kalshi = kalshi_client
        self.ibkr = ibkr_client
        self.min_edge_pct = 0.05  # 5% minimum edge
        self.min_profit_dollars = 500  # $500 minimum profit
        self.testing_mode = testing_mode  # Allow after-hours testing
        
        # Time zone handling (PM is in Central Time)
        try:
            import pytz
            self.et_tz = pytz.timezone('America/New_York')
            self.ct_tz = pytz.timezone('America/Chicago')
        except ImportError:
            logger.warning("pytz not installed, using basic time handling")
            self.et_tz = None
            self.ct_tz = None
        
    def scan_opportunities(self) -> List[Dict]:
        """Main scanning method - finds all arbitrage opportunities"""
        opportunities = []
        
        # Production mode time check
        if not self.testing_mode:
            now = datetime.now()
            if self.ct_tz:
                # Make sure now is timezone-aware first
                if now.tzinfo is None:
                    import pytz
                    ct_now = self.ct_tz.localize(datetime.now())
                else:
                    ct_now = now.astimezone(self.ct_tz)
                if ct_now.hour > 14 or (ct_now.hour == 14 and ct_now.minute >= 45):  # 2:45 PM CT or later
                    logger.warning("⚠️ Scanner disabled after 2:45 PM CT in production mode")
                    return []
            
        try:
            # Get S&P contracts from Kalshi
            kalshi_markets = self._get_todays_sp_markets()
            logger.info(f"Found {len(kalshi_markets)} S&P markets to analyze")
            
            for market in kalshi_markets:
                opp = self._analyze_market(market)
                if opp:
                    opportunities.append(opp)
                    
        except Exception as e:
            logger.error(f"Error scanning opportunities: {e}")
            
        return opportunities
    
    def _get_todays_sp_markets(self) -> List[Dict]:
        """Get S&P 'X or above' style contracts expiring at 4pm ET (today or tomorrow based on time)"""
        try:
            # Determine target date based on current time
            now = datetime.now()
            
            # Check if we should look for tomorrow's contracts
            if self.testing_mode:
                # In testing mode, if after 3:45 PM ET, look for tomorrow
                if self.et_tz:
                    # Make sure now is timezone-aware first
                    if now.tzinfo is None:
                        # Create a timezone-aware datetime
                        import pytz
                        et_now = self.et_tz.localize(datetime.now())
                    else:
                        et_now = now.astimezone(self.et_tz)
                    cutoff_time = et_now.replace(hour=15, minute=45, second=0)  # 3:45 PM ET
                    # Compare timezone-aware datetimes
                    if et_now > cutoff_time:
                        target_date = now + timedelta(days=1)
                        logger.info("🧪 TESTING MODE: After 3:45 PM ET, looking for tomorrow's contracts")
                    else:
                        target_date = now
                else:
                    # Fallback: assume ET is UTC-5 (EST) or UTC-4 (EDT)
                    cutoff_hour = 20 if now.month in [11, 12, 1, 2, 3] else 19  # UTC hour for 3:45 PM ET
                    if now.hour > cutoff_hour or (now.hour == cutoff_hour and now.minute >= 45):
                        target_date = now + timedelta(days=1)
                        logger.info("🧪 TESTING MODE: After 3:45 PM ET, looking for tomorrow's contracts")
                    else:
                        target_date = now
            else:
                # Production mode: always look for today
                target_date = now
                
                # But warn if it's after market close
                if self.et_tz:
                    # Make sure now is timezone-aware first
                    if now.tzinfo is None:
                        import pytz
                        et_now = self.et_tz.localize(datetime.now())
                    else:
                        et_now = now.astimezone(self.et_tz)
                    if et_now.hour >= 16:  # After 4 PM ET
                        logger.warning("⚠️ Markets closed! Enable testing_mode to scan tomorrow's contracts")
                        return []
            
            # Format the date for Kalshi ticker pattern
            date_str = target_date.strftime("%y%b%d").upper()  # e.g., "25AUG12"
            logger.info(f"🔍 Looking for S&P contracts expiring {date_str} at 4pm ET")
            
            # Get markets - be more permissive, filter later
            max_days = 2 if self.testing_mode else 1
            markets = self.kalshi.get_markets_by_criteria(
                max_days_to_expiry=max_days,
                min_bid_ask_sum=10,    # At least some liquidity
                debug=False
            )
            
            filtered = []
            for market in markets:
                ticker = market.get('ticker', '')
                
                # Must be KXINXU series (S&P 500 contracts)
                if not ticker.startswith('KXINXU'):
                    continue
                
                # Check if it's for our target date and 4pm ET
                # Pattern: KXINXU-25AUG12H1600-T6399.9999
                if f"-{date_str}H1600-" not in ticker:
                    continue
                
                # Must be "X or above" style (check title)
                title = market.get('title', '').lower()
                if 'be above' not in title and 'or above' not in title and 'greater than' not in title:
                    continue
                    
                # Extract and validate S&P level
                sp_level = self._extract_sp_level(ticker)
                if not sp_level:
                    continue
                    
                filtered.append(market)
                logger.debug(f"Found S&P market: {ticker} - {market.get('title')}")
            
            logger.info(f"✅ Found {len(filtered)} S&P 'or above' markets for {date_str} 4pm ET")
            
            # If no markets found and in testing mode, give helpful message
            if not filtered and self.testing_mode:
                logger.info("💡 No markets found. Try checking:")
                logger.info("   - Are there S&P contracts for tomorrow?")
                logger.info("   - Is it a weekend/holiday?")
                logger.info("   - Are markets properly loaded in Kalshi?")
                
            return filtered
            
        except Exception as e:
            logger.error(f"Error fetching Kalshi markets: {e}")
            return []
    
    def _extract_sp_level(self, ticker: str) -> Optional[float]:
        """Extract S&P level from ticker like KXINXU-25AUG12H1600-T6399.9999"""
        try:
            # Find the T followed by numbers
            parts = ticker.split('-T')
            if len(parts) < 2:
                return None
                
            level_str = parts[1]
            level = float(level_str)
            
            # Round to nearest whole number (6399.9999 -> 6400)
            return round(level)
            
        except Exception as e:
            logger.error(f"Error extracting S&P level from {ticker}: {e}")
            return None
    
    def _analyze_market(self, kalshi_market: Dict) -> Optional[Dict]:
        """Analyze a single Kalshi market for arbitrage opportunities"""
        try:
            ticker = kalshi_market.get('ticker', '')
            
            # Extract S&P level
            sp_level = self._extract_sp_level(ticker)
            if not sp_level:
                return None
                
            # Get Kalshi prices from market data
            # The market dict already has yes_bid, no_bid from get_markets_by_criteria
            kalshi_yes_price = kalshi_market.get('yes_bid', 0) / 100.0  # Convert cents to dollars
            kalshi_no_price = kalshi_market.get('no_bid', 0) / 100.0
            
            if kalshi_yes_price <= 0 or kalshi_no_price <= 0:
                return None
                
            # SPX strikes are same as S&P levels (no conversion needed)
            spx_strike_low = sp_level
            spx_strike_high = spx_strike_low + 10  # SPX strikes in 10-point increments
            
            # Get SPX spot price directly
            self.ibkr.get_underlying_price("SPX")
            import time
            time.sleep(2)  # Wait for data
            spx_spot = self.ibkr.underlying_price.get("SPX")
            if not spx_spot:
                logger.warning(f"No SPX price available")
                return None
                
            # Get options data for 0DTE
            expiry_date = datetime.now().strftime("%Y%m%d")  # Today
            
            # Calculate implied probabilities from options
            # For "be above X" (Kalshi YES), we need P(SPX >= X)
            options_prob_above = self._calculate_options_probability(
                spx_spot, spx_strike_low, expiry_date, is_above=True
            )
            
            if not options_prob_above:
                return None
                
            # Compare probabilities and find arbitrage
            # Kalshi YES = probability S&P >= level
            # Options prob = probability SPX >= strike
            
            # Check if we should buy YES or NO
            kalshi_yes_edge = kalshi_yes_price - options_prob_above
            kalshi_no_edge = kalshi_no_price - (1 - options_prob_above)
            
            # Pick the side with better edge
            if abs(kalshi_yes_edge) > abs(kalshi_no_edge) and abs(kalshi_yes_edge) > self.min_edge_pct:
                # Buy YES (bet on "over")
                return self._create_opportunity(
                    kalshi_market, sp_level, spx_strike_low, spx_strike_high,
                    kalshi_yes_price, options_prob_above, 'YES', kalshi_yes_edge
                )
            elif abs(kalshi_no_edge) > self.min_edge_pct:
                # Buy NO (bet on "under")
                return self._create_opportunity(
                    kalshi_market, sp_level, spx_strike_low, spx_strike_high,
                    kalshi_no_price, 1 - options_prob_above, 'NO', kalshi_no_edge
                )
                
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing market {kalshi_market.get('ticker')}: {e}")
            return None
    
    def _calculate_options_probability(self, spot: float, strike: float, 
                                     expiry_date: str, is_above: bool) -> Optional[float]:
        """Calculate probability from options prices using Black-Scholes"""
        try:
            # Get option chain if not already loaded
            if expiry_date not in self.ibkr.option_chains:
                # Get SPX option chain for the strike
                self.ibkr.get_spx_option_chain(expiry_date, [strike])
                import time
                time.sleep(3)  # Wait for data
            
            chain_data = self.ibkr.option_chains.get(expiry_date, {})
            if not chain_data:
                return None
                
            # Find the strike in the chain
            call_iv = None
            if strike in chain_data and 'C' in chain_data[strike]:
                call_option = chain_data[strike]['C']
                call_iv = call_option.implied_volatility
                    
            if not call_iv or call_iv <= 0:
                return None
                
            # Calculate time to expiry (fraction of year)
            # For 0DTE at 4pm, approximate as 6.5 hours / 252 trading days
            time_to_expiry = 6.5 / (252 * 6.5)  # Rough approximation
            
            # Risk-free rate (approximate)
            r = 0.045
            
            # Black-Scholes probability calculation
            d2 = (math.log(spot / strike) + (r - 0.5 * call_iv**2) * time_to_expiry) / (call_iv * math.sqrt(time_to_expiry))
            
            if is_above:
                prob = norm.cdf(d2)  # Probability of finishing above strike
            else:
                prob = 1 - norm.cdf(d2)  # Probability of finishing below strike
                
            return prob
            
        except Exception as e:
            logger.error(f"Error calculating options probability: {e}")
            return None
    
    def _create_opportunity(self, kalshi_market: Dict, sp_level: float,
                          spx_low: float, spx_high: float, 
                          kalshi_price: float, options_prob: float,
                          kalshi_side: str, edge: float) -> Dict:
        """Create opportunity dict with all relevant info"""
        
        # Determine strategy based on Kalshi side
        # CRITICAL: Short leg must be AT the Kalshi level!
        if kalshi_side == 'NO':  # Betting S&P stays under the level
            # Bull put spread: Sell put AT level, buy put below
            strategy = f"Buy Kalshi NO + Sell SPX {sp_level}/{sp_level-10} Bull Put Spread"
            spread_type = "bull put (credit)"
        else:  # YES - betting S&P goes over the level  
            # Bear call spread: Sell call AT level, buy call above
            strategy = f"Buy Kalshi YES + Sell SPX {sp_level}/{sp_level+10} Bear Call Spread"
            spread_type = "bear call (credit)"
            
        # Add theta decay note based on time of day
        current_hour = datetime.now().hour
        if current_hour < 11:  # Before 11 AM CT
            theta_note = "Morning entry: High premium (ideal for credit spreads)"
        elif current_hour < 14:  # 11 AM - 2 PM CT
            theta_note = "Midday entry: Moderate premium"
        else:  # After 2 PM CT
            theta_note = "Afternoon entry: Low premium (theta decay advanced)"
            
        # Estimate profit (simplified - would need position sizing)
        estimated_contracts = 1000  # Example size
        estimated_profit = estimated_contracts * abs(edge)
        
        return {
            'timestamp': datetime.now(),
            'kalshi_ticker': kalshi_market['ticker'],
            'kalshi_title': kalshi_market.get('title', ''),
            'sp_level': sp_level,
            'spx_strikes': (sp_level, sp_level+10 if kalshi_side == 'YES' else sp_level-10),
            'kalshi_side': kalshi_side,
            'kalshi_price': kalshi_price,
            'kalshi_probability': kalshi_price,
            'options_probability': options_prob,
            'edge_percentage': abs(edge) * 100,
            'strategy': strategy,
            'spread_type': spread_type,
            'theta_note': theta_note,
            'estimated_profit': estimated_profit,
            'expires': kalshi_market.get('close_time', '')
        }
