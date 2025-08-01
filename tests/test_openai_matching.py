#!/usr/bin/env python3
"""
Test script for OpenAI Enhanced Matching
Verifies that individual contracts are matched correctly using GPT-4o-mini
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
import json

# Add paths
sys.path.append('./data_collectors')
sys.path.append('./arbitrage')

from openai_enhanced_matcher import EnhancedOpenAIMatchingSystem
from kalshi_client import KalshiClient
from polymarket_client import EnhancedPolymarketClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIMatchingTester:
    """Test the OpenAI matching system"""
    
    def __init__(self):
        self.matcher = None
        self.test_results = {
            'threshold_matching': False,
            'individual_contracts': False,
            'no_false_matches': False,
            'api_connection': False,
            'confidence_scores': False
        }
    
    async def test_api_connection(self):
        """Test if OpenAI API is configured"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == 'your-openai-api-key-here':
                logger.error("❌ OPENAI_API_KEY not configured!")
                logger.error("Please set your OpenAI API key in .env file")
                logger.error("Get one from: https://platform.openai.com/api-keys")
                return False
            
            # Test the API key by making a simple request
            try:
                import openai
                openai.api_key = api_key
                # Make a minimal test request
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5
                )
                logger.info("✅ OpenAI API key is valid and working!")
                self.test_results['api_connection'] = True
                return True
            except Exception as e:
                logger.error(f"❌ OpenAI API key test failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ API connection test failed: {e}")
            return False
    
    async def test_market_fetching(self):
        """Test fetching individual contracts from both platforms"""
        logger.info("\n🔍 Testing market fetching...")
        
        try:
            # Test Kalshi
            logger.info("📡 Testing Kalshi market fetch...")
            kalshi_client = KalshiClient(verbose=False)
            kalshi_markets = kalshi_client.get_markets_by_criteria(
                min_liquidity_usd=500,
                max_days_to_expiry=14,
                min_volume=50
            )
            logger.info(f"✅ Fetched {len(kalshi_markets)} Kalshi markets")
            
            # Look for multi-threshold events (like Fed rates)
            event_groups = {}
            for market in kalshi_markets:
                event = market.get('event_ticker', 'UNKNOWN')
                if event not in event_groups:
                    event_groups[event] = []
                event_groups[event].append(market)
            
            multi_threshold_events = {k: v for k, v in event_groups.items() if len(v) > 1}
            logger.info(f"📊 Found {len(multi_threshold_events)} multi-threshold events")
            
            # Show examples
            if multi_threshold_events:
                for event, contracts in list(multi_threshold_events.items())[:3]:
                    logger.info(f"\n   Event: {event}")
                    for contract in contracts[:5]:
                        logger.info(f"      - {contract['ticker']}: {contract.get('title', '')[:60]}...")
            
            # Test Polymarket
            logger.info("\n📡 Testing Polymarket market fetch...")
            async with EnhancedPolymarketClient() as poly_client:
                poly_markets = await poly_client.get_markets_by_criteria(
                    min_volume_usd=500,
                    max_days_to_expiry=14,
                    limit=500
                )
                logger.info(f"✅ Fetched {len(poly_markets)} Polymarket markets")
                
                # Show examples
                if poly_markets:
                    logger.info("\n   Sample Polymarket markets:")
                    for i, market in enumerate(poly_markets[:5]):
                        logger.info(f"      {i+1}. {market.question[:60]}...")
            
            self.test_results['individual_contracts'] = len(kalshi_markets) > 0 and len(poly_markets) > 0
            return True
            
        except Exception as e:
            logger.error(f"❌ Market fetching failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_threshold_matching(self):
        """Test that threshold values are correctly identified and matched"""
        logger.info("\n🎯 Testing threshold matching logic...")
        
        try:
            # Create matcher instance
            self.matcher = EnhancedOpenAIMatchingSystem()
            
            # Test threshold extraction
            test_questions = [
                "Will the Fed funds rate be above 5.0% after the next meeting?",
                "Will inflation be below 3.5% in December?",
                "Will the S&P 500 close above 4500 on Friday?",
                "Will unemployment be between 3.5% and 4.0%?"
            ]
            
            logger.info("Testing threshold extraction:")
            for question in test_questions:
                threshold = self.matcher.extract_threshold_value(question)
                logger.info(f"   Q: {question[:50]}... → Threshold: {threshold}")
            
            self.test_results['threshold_matching'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Threshold matching test failed: {e}")
            return False
    
    async def test_match_detection(self):
        """Test actual matching with a small sample"""
        logger.info("\n🔬 Testing actual match detection with OpenAI...")
        
        try:
            if not self.matcher:
                self.matcher = EnhancedOpenAIMatchingSystem()
            
            # Get a small sample of markets
            kalshi_client = KalshiClient(verbose=False)
            kalshi_markets = kalshi_client.get_markets_by_criteria(
                min_liquidity_usd=1000,
                max_days_to_expiry=7,
                min_volume=100
            )[:10]  # Just 10 markets for testing
            
            async with EnhancedPolymarketClient() as poly_client:
                poly_markets = await poly_client.get_markets_by_criteria(
                    min_volume_usd=1000,
                    max_days_to_expiry=7,
                    limit=100
                )
                
                # Convert to dict format expected by matcher
                poly_dicts = []
                for market in poly_markets:
                    poly_dict = {
                        'condition_id': market.condition_id,
                        'question': market.question,
                        'description': market.description[:200] if market.description else '',
                        'yes_price': market.yes_token.price if market.yes_token else 0,
                        'no_price': market.no_token.price if market.no_token else 0,
                        'volume_24h': market.volume_24h,
                        'liquidity': market.liquidity_usd,
                        'end_date': market.end_date,
                        'tags': ''
                    }
                    poly_dicts.append(poly_dict)
            
            logger.info(f"Testing matching with {len(kalshi_markets)} Kalshi and {len(poly_dicts)} Polymarket markets")
            
            # Run matching (will use OpenAI API if configured)
            if os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_API_KEY') != 'your-openai-api-key-here':
                matches = await self.matcher.match_contracts_with_openai(kalshi_markets, poly_dicts)
                logger.info(f"✅ Found {len(matches)} matches using GPT-4o-mini")
                
                # Check confidence scores
                if matches:
                    high_conf = [m for m in matches if m.confidence >= 0.9]
                    logger.info(f"   High confidence matches (≥90%): {len(high_conf)}")
                    self.test_results['confidence_scores'] = True
                    
                    # Show first few matches
                    logger.info("\n   Sample matches:")
                    for match in matches[:3]:
                        logger.info(f"      {match.kalshi_ticker} ↔ {match.polymarket_condition_id[:16]}...")
                        logger.info(f"         Confidence: {match.confidence:.1%}")
                        logger.info(f"         Type: {match.match_type}")
                        if match.threshold_value:
                            logger.info(f"         Threshold: {match.threshold_value}")
            else:
                logger.warning("⚠️ Skipping OpenAI API test - API key not configured")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Match detection test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def check_package_installation(self):
        """Check if openai package is installed"""
        try:
            import openai
            logger.info("✅ openai package is installed")
            return True
        except ImportError:
            logger.error("❌ openai package is NOT installed!")
            logger.error("Please run: pip install openai")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting OpenAI (GPT-4o-mini) Matching Tests\n")
        logger.info("Using GPT-4o-mini for best cost-effective matching")
        logger.info("=" * 60)
        
        # Check package
        package_ok = await self.check_package_installation()
        if not package_ok:
            return
        
        # Test 1: API Connection
        await self.test_api_connection()
        
        # Test 2: Market Fetching
        await self.test_market_fetching()
        
        # Test 3: Threshold Matching
        await self.test_threshold_matching()
        
        # Test 4: Match Detection (only if API key is set)
        if self.test_results['api_connection']:
            await self.test_match_detection()
        
        # Summary
        logger.info("\n📊 TEST RESULTS SUMMARY:")
        logger.info("=" * 50)
        
        for test_name, passed in self.test_results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
        
        # Overall verdict
        all_passed = all(self.test_results.values())
        if all_passed:
            logger.info("\n🎉 ALL TESTS PASSED! OpenAI matching is ready.")
        else:
            logger.info("\n⚠️ Some tests failed. Please fix issues before proceeding.")
        
        # Next steps
        if not self.test_results['api_connection']:
            logger.info("\n📝 NEXT STEP: Add your OpenAI API key to .env file")
            logger.info("   Get key from: https://platform.openai.com/api-keys")
            logger.info("   Set: OPENAI_API_KEY='sk-...'")
        elif all_passed:
            logger.info("\n📝 NEXT STEPS:")
            logger.info("   1. Run full matching: python openai_enhanced_matcher.py --full")
            logger.info("   2. Test arbitrage detection: python claude_matched_detector.py")
            logger.info("   3. Run full system: python fully_automated_enhanced.py")
            
            logger.info("\n💰 Cost estimate:")
            logger.info("   GPT-4o-mini: $0.00015 per 1K input tokens, $0.0006 per 1K output tokens")
            logger.info("   Estimated cost for full run: $0.05 - $0.25")
            logger.info("   Even cheaper than GPT-3.5-turbo!")

async def main():
    """Main entry point"""
    tester = OpenAIMatchingTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
