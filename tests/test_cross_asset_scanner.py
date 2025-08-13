"""
Test file for cross-asset scanner
Run this to verify the scanner is working correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import logging
from src.scanners.cross_asset_scanner import CrossAssetScanner
from src.data_collectors.kalshi_client import KalshiClient
from src.data_collectors.ibkr_options_client import IBKROptionsClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_scanner():
    """Test the cross-asset scanner"""
    print("\n=== Cross-Asset Scanner Test ===")
    print(f"Test time: {datetime.now()}")
    
    try:
        # Initialize clients
        print("\n1. Initializing Kalshi client...")
        kalshi = KalshiClient()
        
        print("\n2. Initializing IBKR options client...")
        ibkr = IBKROptionsClient()
        
        if not ibkr.connect_to_tws():
            print("ERROR: Could not connect to TWS. Make sure it's running.")
            return
            
        print("Connected to TWS successfully!")
        
        # Create scanner with testing mode enabled
        print("\n3. Creating cross-asset scanner...")
        print("   🧪 TESTING MODE ENABLED (will look for tomorrow's contracts after 3:45 PM ET)")
        scanner = CrossAssetScanner(kalshi, ibkr, testing_mode=True)
        
        # Show current time for context
        from datetime import timezone
        current_time = datetime.now()
        print(f"\n⏰ Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Test getting S&P markets
        print("\n4. Testing Kalshi market retrieval...")
        markets = scanner._get_todays_sp_markets()
        print(f"Found {len(markets)} S&P 4pm ET markets")
        
        if markets:
            print("\nSample markets:")
            for i, market in enumerate(markets[:3]):  # Show first 3
                print(f"  {i+1}. {market.get('ticker')} - {market.get('title')}")
        
        # Test full scan
        print("\n5. Running full arbitrage scan...")
        opportunities = scanner.scan_opportunities()
        
        if opportunities:
            print(f"\nFound {len(opportunities)} arbitrage opportunities!")
            for i, opp in enumerate(opportunities):
                print(f"\n--- Opportunity {i+1} ---")
                print(f"Kalshi: {opp['kalshi_ticker']}")
                print(f"S&P Level: {opp['sp_level']}")
                print(f"Kalshi Side: {opp['kalshi_side']} @ {opp['kalshi_price']:.2f}")
                print(f"Options Probability: {opp['options_probability']:.2f}")
                print(f"Edge: {opp['edge_percentage']:.1f}%")
                print(f"Strategy: {opp['strategy']}")
                print(f"Spread Type: {opp.get('spread_type', 'N/A')}")
                print(f"Theta Note: {opp.get('theta_note', 'N/A')}")
                print(f"Estimated Profit: ${opp['estimated_profit']:.2f}")
        else:
            print("\nNo arbitrage opportunities found at this time.")
            print("This could mean:")
            print("- Markets are efficiently priced")
            print("- No S&P contracts expiring today at 4pm EDT")
            print("- Insufficient liquidity in options")
            
        # Disconnect
        print("\n6. Disconnecting from TWS...")
        ibkr.disconnect_from_tws()
        print("Test complete!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


def test_specific_market(ticker: str):
    """Test analysis of a specific Kalshi market"""
    print(f"\n=== Testing Specific Market: {ticker} ===")
    
    try:
        kalshi = KalshiClient()
        ibkr = IBKROptionsClient()
        
        if not ibkr.connect_to_tws():
            print("ERROR: Could not connect to TWS")
            return
            
        scanner = CrossAssetScanner(kalshi, ibkr, testing_mode=True)
        
        # Get market info
        markets = kalshi.get_markets()
        target_market = None
        for market in markets:
            if market.get('ticker') == ticker:
                target_market = market
                break
                
        if not target_market:
            print(f"Market {ticker} not found!")
            return
            
        print(f"Market: {target_market.get('title')}")
        
        # Analyze it
        opp = scanner._analyze_market(target_market)
        
        if opp:
            print("\nArbitrage opportunity found!")
            print(f"Edge: {opp['edge_percentage']:.1f}%")
            print(f"Strategy: {opp['strategy']}")
        else:
            print("\nNo arbitrage opportunity for this market")
            
            # Get more details
            orderbook = kalshi.get_market_orderbook(ticker)
            if orderbook:
                yes_data = orderbook.get('yes', {})
                no_data = orderbook.get('no', {})
                yes_bid = yes_data.get('offers', [{}])[0].get('price', 0) if yes_data.get('offers') else 0
                no_bid = no_data.get('offers', [{}])[0].get('price', 0) if no_data.get('offers') else 0
                print(f"Kalshi YES bid: ${yes_bid/100:.2f}, NO bid: ${no_bid/100:.2f}")
            else:
                # Try getting from market data
                yes_bid = target_market.get('yes_bid', 0) / 100.0
                no_bid = target_market.get('no_bid', 0) / 100.0
                print(f"Kalshi YES: ${yes_bid:.2f}, NO: ${no_bid:.2f}")
                
        ibkr.disconnect_from_tws()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the main test
    test_scanner()
    
    # Optionally test a specific market
    # Example: test_specific_market("KXINXU-25AUG12H1600-T6399.9999")
