#!/usr/bin/env python3
"""
Claude Matched Arbitrage Detector
Wrapper around CSV-based arbitrage detector for compatibility with the automated system
"""

import asyncio
import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass

# Add paths
sys.path.append('./src/detectors')

# Import the CSV-based detector
from csv_arbitrage_detector import CSVBasedArbitrageDetector, ArbitrageOpportunity

# Create a simpler opportunity class for backward compatibility
@dataclass 
class SimpleArbitrageOpportunity:
    """Simplified opportunity for the automated system"""
    opportunity_id: str
    kalshi_ticker: str
    polymarket_condition_id: str
    guaranteed_profit: float
    profit_percentage: float
    optimal_volume: int
    time_to_expiry_hours: float
    match_confidence: float
    buy_platform: str
    buy_side: str
    kalshi_slippage_percent: float = 0.0
    polymarket_slippage_percent: float = 0.0
    trade_size_usd: float = 0.0

class ClaudeMatchedArbitrageDetector:
    """Detector that works with matches from the OpenAI/Claude matching system"""
    
    def __init__(self, csv_file_path: str = 'manual_matches.csv'):
        self.csv_file_path = csv_file_path
        self.base_detector = CSVBasedArbitrageDetector(csv_file_path)
    
    async def scan_matched_contracts(self, max_orderbook_calls: int = 200) -> List[SimpleArbitrageOpportunity]:
        """Scan matched contracts for arbitrage opportunities"""
        # Use the CSV-based detector
        opportunities = await self.base_detector.detect_arbitrage_opportunities()
        
        # Convert to simple opportunities for compatibility
        simple_opportunities = []
        for i, opp in enumerate(opportunities):
            simple_opp = SimpleArbitrageOpportunity(
                opportunity_id=f"A{i+1:03d}",
                kalshi_ticker=opp.kalshi_ticker,
                polymarket_condition_id=opp.poly_condition_id,
                guaranteed_profit=opp.max_total_profit,
                profit_percentage=opp.profit_percentage,
                optimal_volume=opp.optimal_volume,
                time_to_expiry_hours=opp.time_to_expiry_hours,
                match_confidence=opp.match_confidence,
                buy_platform="Kalshi",  # Always buy YES on Kalshi
                buy_side="YES",
                kalshi_slippage_percent=2.0,  # Estimated
                polymarket_slippage_percent=1.0,  # Estimated
                trade_size_usd=opp.optimal_volume * opp.kalshi_yes_price
            )
            simple_opportunities.append(simple_opp)
        
        return simple_opportunities

# For direct testing
async def main():
    """Test the detector"""
    detector = ClaudeMatchedArbitrageDetector()
    opportunities = await detector.scan_matched_contracts()
    
    print(f"\n🎯 Found {len(opportunities)} arbitrage opportunities")
    for opp in opportunities[:5]:
        print(f"\n{opp.opportunity_id}: {opp.kalshi_ticker}")
        print(f"   Profit: ${opp.guaranteed_profit:.2f} ({opp.profit_percentage:.1f}%)")
        print(f"   Volume: {opp.optimal_volume} contracts")

if __name__ == "__main__":
    asyncio.run(main())
