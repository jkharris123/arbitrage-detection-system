#!/usr/bin/env python3
"""
ENHANCED ARBITRAGE DETECTOR - CSV-Based
Reads from final matched pairs CSV instead of live API calls

New Flow:
1. Read CSV from enhanced matching system
2. Filter for SAFE_FOR_AUTOMATION matches only  
3. Check current prices via APIs for each match
4. Calculate arbitrage opportunities
5. Apply criteria filters (% gain, time to expiry)
6. Use profit optimization for volume sizing
7. Execute or alert

Key Advantages:
- No false matches (pre-filtered by matching system)
- Much faster (no redundant API calls)
- Focus only on verified contract pairs
- Clean separation of matching vs arbitrage detection
"""

import asyncio
import csv
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import sys
import os

# Add paths
sys.path.append('./data_collectors')
sys.path.append('./arbitrage')
sys.path.append('./')

from kalshi_client import KalshiClient
from polymarket_client import EnhancedPolymarketClient

@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity with all details"""
    # Contract pair info
    kalshi_ticker: str
    kalshi_question: str
    poly_condition_id: str
    poly_question: str
    
    # Current market prices
    kalshi_yes_price: float
    kalshi_yes_volume: float
    poly_no_price: float
    poly_no_volume: float
    
    # Arbitrage calculation
    combined_cost: float  # Cost to buy both sides
    guaranteed_payout: float  # Always $1.00
    gross_profit: float  # Before fees
    net_profit_per_contract: float  # After fees
    profit_percentage: float
    
    # Optimal volume calculation
    optimal_volume: int
    max_total_profit: float
    effective_liquidity: float
    
    # Risk assessment
    time_to_expiry_hours: float
    daily_return_annualized: float
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    
    # Execution details
    kalshi_fees: float
    poly_gas_cost: float
    total_fees: float
    
    # Metadata
    detection_timestamp: str
    match_confidence: float
    recommendation: str

class CSVBasedArbitrageDetector:
    """Enhanced arbitrage detector that reads from CSV matches"""
    
    def __init__(self, csv_file_path: str):
        self.csv_file_path = csv_file_path
        self.kalshi_client = KalshiClient()
        
        # Arbitrage criteria
        self.min_profit_percentage = 2.0  # 2% minimum profit
        self.max_days_to_expiry = 30      # Max 30 days out
        self.min_daily_return = 50.0      # 50% annualized minimum
        self.min_volume_per_contract = 100 # Minimum total volume
        
        print(f"🎯 CSV-BASED ARBITRAGE DETECTOR")
        print(f"📁 Reading matches from: {csv_file_path}")
        print(f"📊 Criteria: {self.min_profit_percentage}% profit, {self.max_days_to_expiry}d max expiry")
    
    async def detect_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """Main detection flow - read CSV and find arbitrage"""
        print(f"\n🚀 Starting CSV-based arbitrage detection...")
        
        # Step 1: Read and filter matched pairs
        matched_pairs = self.read_matched_pairs_csv()
        safe_pairs = self.filter_safe_matches(matched_pairs)
        
        print(f"📊 Loaded {len(matched_pairs)} total matched pairs")
        print(f"✅ Filtered to {len(safe_pairs)} SAFE_FOR_AUTOMATION pairs")
        
        # Step 2: Check current prices for each safe pair
        print(f"\n💰 Checking current prices for arbitrage opportunities...")
        opportunities = []
        
        async with EnhancedPolymarketClient() as poly_client:
            for i, pair in enumerate(safe_pairs):
                if i % 10 == 0:
                    print(f"📈 Progress: {i}/{len(safe_pairs)} pairs checked...")
                
                try:
                    # Get current market prices
                    kalshi_prices = await self.get_kalshi_current_prices(pair['kalshi_ticker'])
                    poly_prices = await self.get_polymarket_current_prices(poly_client, pair['poly_condition_id'])
                    
                    if kalshi_prices and poly_prices:
                        # Calculate arbitrage opportunity
                        opportunity = await self.calculate_arbitrage_opportunity(
                            pair, kalshi_prices, poly_prices, poly_client
                        )
                        
                        if opportunity and self.meets_arbitrage_criteria(opportunity):
                            opportunities.append(opportunity)
                            print(f"✅ ARBITRAGE FOUND: {opportunity.kalshi_ticker} - {opportunity.profit_percentage:.1f}% profit")
                
                except Exception as e:
                    print(f"⚠️ Error checking {pair['kalshi_ticker']}: {e}")
                    continue
        
        print(f"\n🎯 Detection complete: {len(opportunities)} arbitrage opportunities found!")
        return opportunities
    
    def read_matched_pairs_csv(self) -> List[Dict]:
        """Read the final matched pairs CSV"""
        try:
            matched_pairs = []
            with open(self.csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    matched_pairs.append(row)
            
            print(f"📁 Successfully read {len(matched_pairs)} matched pairs from CSV")
            return matched_pairs
            
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return []
    
    def filter_safe_matches(self, matched_pairs: List[Dict]) -> List[Dict]:
        """Filter for only SAFE_FOR_AUTOMATION matches with actual matches"""
        safe_pairs = []
        
        for pair in matched_pairs:
            # Only include pairs that:
            # 1. Have a match (has_match = "YES")
            # 2. Are marked as safe for automation
            # 3. Have reasonable confidence
            if (pair.get('has_match') == 'YES' and 
                pair.get('recommendation') == 'SAFE_FOR_AUTOMATION' and
                float(pair.get('match_confidence', 0)) > 0.8):
                
                safe_pairs.append(pair)
        
        print(f"🔒 Filtered to {len(safe_pairs)} safe, high-confidence matches")
        return safe_pairs
    
    async def get_kalshi_current_prices(self, ticker: str) -> Optional[Dict]:
        """Get current Kalshi prices for a ticker"""
        try:
            # This would call Kalshi API to get current market data
            # Placeholder for now - implement based on your Kalshi client
            market_data = self.kalshi_client.get_market(ticker)
            
            if market_data:
                return {
                    'yes_price': market_data.get('yes_bid', 0.5),  # Current YES price
                    'yes_volume': market_data.get('yes_volume', 0),
                    'last_trade_price': market_data.get('last_price', 0.5)
                }
        except Exception as e:
            print(f"⚠️ Error fetching Kalshi prices for {ticker}: {e}")
        
        return None
    
    async def get_polymarket_current_prices(self, client: EnhancedPolymarketClient, 
                                          condition_id: str) -> Optional[Dict]:
        """Get current Polymarket prices"""
        try:
            # Get market data from Polymarket
            market_data = await client.get_market_by_condition_id(condition_id)
            
            if market_data and market_data.no_token:
                return {
                    'no_price': market_data.no_token.price,  # Current NO price
                    'no_volume': market_data.no_token.volume_24h,
                    'gas_cost': client.estimate_gas_cost_usd()
                }
        except Exception as e:
            print(f"⚠️ Error fetching Polymarket prices for {condition_id}: {e}")
        
        return None
    
    async def calculate_arbitrage_opportunity(self, pair: Dict, kalshi_prices: Dict, 
                                           poly_prices: Dict, poly_client: EnhancedPolymarketClient) -> Optional[ArbitrageOpportunity]:
        """Calculate detailed arbitrage opportunity"""
        try:
            kalshi_yes_price = kalshi_prices['yes_price']
            poly_no_price = poly_prices['no_price']
            
            # Basic arbitrage check
            combined_cost = kalshi_yes_price + poly_no_price
            if combined_cost >= 1.0:
                return None  # No arbitrage opportunity
            
            # Calculate profits
            gross_profit = 1.0 - combined_cost
            
            # Calculate fees
            kalshi_fees = self.calculate_kalshi_fees(kalshi_yes_price, 1)  # 1 contract
            poly_gas_cost = poly_prices['gas_cost']
            total_fees = kalshi_fees + poly_gas_cost
            
            net_profit_per_contract = gross_profit - total_fees
            if net_profit_per_contract <= 0:
                return None  # Fees eat all profit
            
            profit_percentage = (net_profit_per_contract / combined_cost) * 100
            
            # Calculate time to expiry
            time_to_expiry = self.calculate_time_to_expiry(pair['kalshi_expiry'])
            if time_to_expiry <= 0:
                return None  # Already expired
            
            # Calculate optimal volume using profit optimization
            optimal_volume, max_total_profit = await self.calculate_optimal_volume(
                pair, kalshi_yes_price, poly_no_price, poly_client
            )
            
            # Calculate risk metrics
            daily_return = (profit_percentage / (time_to_expiry / 24)) if time_to_expiry > 0 else 0
            risk_level = self.assess_risk_level(profit_percentage, time_to_expiry, daily_return)
            
            return ArbitrageOpportunity(
                kalshi_ticker=pair['kalshi_ticker'],
                kalshi_question=pair['kalshi_question'],
                poly_condition_id=pair['poly_condition_id'],
                poly_question=pair['poly_question'],
                
                kalshi_yes_price=kalshi_yes_price,
                kalshi_yes_volume=kalshi_prices['yes_volume'],
                poly_no_price=poly_no_price,
                poly_no_volume=poly_prices['no_volume'],
                
                combined_cost=combined_cost,
                guaranteed_payout=1.0,
                gross_profit=gross_profit,
                net_profit_per_contract=net_profit_per_contract,
                profit_percentage=profit_percentage,
                
                optimal_volume=optimal_volume,
                max_total_profit=max_total_profit,
                effective_liquidity=min(kalshi_prices['yes_volume'], poly_prices['no_volume']),
                
                time_to_expiry_hours=time_to_expiry,
                daily_return_annualized=daily_return * 365,
                risk_level=risk_level,
                
                kalshi_fees=kalshi_fees,
                poly_gas_cost=poly_gas_cost,
                total_fees=total_fees,
                
                detection_timestamp=datetime.now().isoformat(),
                match_confidence=float(pair['match_confidence']),
                recommendation="EXECUTE" if profit_percentage > 5.0 else "CONSIDER"
            )
            
        except Exception as e:
            print(f"❌ Error calculating arbitrage: {e}")
            return None
    
    async def calculate_optimal_volume(self, pair: Dict, kalshi_yes_price: float, 
                                     poly_no_price: float, poly_client: EnhancedPolymarketClient) -> Tuple[int, float]:
        """Calculate optimal volume using profit optimization logic"""
        try:
            # Test different volume levels
            test_volumes = [10, 25, 50, 100, 200, 500, 1000]
            best_volume = 10
            best_total_profit = 0.0
            
            for volume in test_volumes:
                try:
                    # Get execution prices for this volume from APIs
                    kalshi_execution_price = await self.get_kalshi_execution_price(pair['kalshi_ticker'], volume)
                    poly_execution_data = await poly_client.get_execution_prices_for_volumes(
                        pair['poly_condition_id'], "buy", [volume * poly_no_price]
                    )
                    
                    if kalshi_execution_price and poly_execution_data:
                        poly_execution_price = poly_execution_data[0]['execution_price']
                        
                        # Calculate total cost and profit for this volume
                        total_cost = volume * (kalshi_execution_price + poly_execution_price)
                        total_fees = self.calculate_kalshi_fees(kalshi_execution_price, volume) + poly_execution_data[0]['gas_cost_usd']
                        total_profit = volume * 1.0 - total_cost - total_fees
                        
                        if total_profit > best_total_profit:
                            best_total_profit = total_profit
                            best_volume = volume
                
                except Exception:
                    continue
            
            return best_volume, best_total_profit
            
        except Exception as e:
            print(f"⚠️ Error calculating optimal volume: {e}")
            return 10, 0.0  # Fallback to small volume
    
    async def get_kalshi_execution_price(self, ticker: str, volume: int) -> Optional[float]:
        """Get Kalshi execution price for given volume"""
        try:
            # This would use Kalshi's slippage calculation API
            # Placeholder - implement based on Kalshi API capabilities
            market_data = self.kalshi_client.get_market(ticker)
            base_price = market_data.get('yes_bid', 0.5)
            
            # Simple slippage model (replace with API call)
            slippage_factor = min(volume / 1000 * 0.02, 0.1)  # 2% per 1000 contracts, max 10%
            execution_price = base_price * (1 + slippage_factor)
            
            return min(execution_price, 0.99)  # Cap at $0.99
            
        except Exception as e:
            print(f"⚠️ Error getting Kalshi execution price: {e}")
            return None
    
    def calculate_kalshi_fees(self, price: float, volume: int) -> float:
        """Calculate Kalshi fees based on their fee structure"""
        # Kalshi fee formula: round_up(0.07 * volume * price * (1-price))
        fee_per_contract = 0.07 * price * (1 - price)
        total_fee = volume * fee_per_contract
        return round(total_fee, 2)
    
    def calculate_time_to_expiry(self, expiry_str: str) -> float:
        """Calculate hours until expiry"""
        try:
            # Parse expiry date and calculate hours remaining
            # This depends on the format in your CSV
            expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            now = datetime.now()
            time_diff = expiry_date - now
            return max(time_diff.total_seconds() / 3600, 0)  # Hours
        except Exception:
            return 24.0  # Default to 24 hours if parsing fails
    
    def assess_risk_level(self, profit_percentage: float, time_to_expiry: float, daily_return: float) -> str:
        """Assess risk level of the opportunity"""
        if profit_percentage > 10.0 and time_to_expiry < 48:  # >10% profit, <48h
            return "LOW"
        elif profit_percentage > 5.0 and time_to_expiry < 168:  # >5% profit, <1 week
            return "MEDIUM"
        else:
            return "HIGH"
    
    def meets_arbitrage_criteria(self, opportunity: ArbitrageOpportunity) -> bool:
        """Check if opportunity meets our criteria"""
        return (
            opportunity.profit_percentage >= self.min_profit_percentage and
            opportunity.time_to_expiry_hours <= (self.max_days_to_expiry * 24) and
            opportunity.daily_return_annualized >= self.min_daily_return and
            opportunity.effective_liquidity >= self.min_volume_per_contract and
            opportunity.net_profit_per_contract > 0
        )
    
    def print_opportunities_summary(self, opportunities: List[ArbitrageOpportunity]):
        """Print summary of found opportunities"""
        if not opportunities:
            print("\n❌ No arbitrage opportunities found meeting criteria")
            return
        
        print(f"\n🎯 ARBITRAGE OPPORTUNITIES SUMMARY")
        print(f"=" * 80)
        print(f"📊 Total opportunities: {len(opportunities)}")
        
        # Sort by profit percentage
        opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)
        
        print(f"\n🚀 TOP OPPORTUNITIES:")
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"\n{i}. {opp.kalshi_ticker}")
            print(f"   📝 Question: {opp.kalshi_question[:60]}...")
            print(f"   💰 Profit: {opp.profit_percentage:.2f}% ({opp.net_profit_per_contract:.3f} per contract)")
            print(f"   📈 Optimal Volume: {opp.optimal_volume} contracts")
            print(f"   💵 Max Total Profit: ${opp.max_total_profit:.2f}")
            print(f"   ⏰ Time to Expiry: {opp.time_to_expiry_hours:.1f} hours")
            print(f"   📊 Daily Return: {opp.daily_return_annualized:.0f}% annualized")
            print(f"   🎯 Risk Level: {opp.risk_level}")
            print(f"   ✅ Recommendation: {opp.recommendation}")

async def main():
    """Run the CSV-based arbitrage detector"""
    print(f"🚀 CSV-BASED ARBITRAGE DETECTOR")
    print(f"📊 Reading from enhanced matching system output")
    
    # Find the most recent CSV file
    import glob
    csv_files = glob.glob('./output/comprehensive_matching_test_*.csv')
    if not csv_files:
        print("❌ No matching CSV files found. Run comprehensive_matching_test.py first!")
        return
    
    latest_csv = max(csv_files, key=os.path.getctime)
    print(f"📁 Using latest CSV: {latest_csv}")
    
    # Run arbitrage detection
    detector = CSVBasedArbitrageDetector(latest_csv)
    opportunities = await detector.detect_arbitrage_opportunities()
    
    # Print results
    detector.print_opportunities_summary(opportunities)
    
    print(f"\n🎉 Detection complete!")
    print(f"💡 Next steps:")
    print(f"   1. Review opportunities above")
    print(f"   2. Execute high-confidence trades")
    print(f"   3. Monitor for new opportunities")
    
    return opportunities

if __name__ == "__main__":
    asyncio.run(main())
