#!/usr/bin/env python3
"""
Configuration settings for the arbitrage bot
Includes real fee structures from Kalshi and IBKR
Updated with demo/test environment support for zero-risk testing
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Configuration settings for the arbitrage bot"""
    
    def __init__(self):
        # Environment mode - determines which APIs and credentials to use
        self.environment = os.getenv('ENVIRONMENT', 'DEMO').upper()  # DEMO, PAPER, LIVE
        
        # Trading parameters
        self.min_profit_margin_percent = float(os.getenv('MIN_PROFIT_MARGIN', '1.0'))  # 1% minimum
        self.max_position_size = int(os.getenv('MAX_POSITION_SIZE', '1000'))  # Max contracts per trade
        self.scan_interval_seconds = int(os.getenv('SCAN_INTERVAL', '900'))  # 15 minute scans
        
        # Risk management (for live trading only - demos are risk-free)
        self.max_total_exposure = float(os.getenv('MAX_TOTAL_EXPOSURE', '10000'))  # $10k max exposure
        self.max_slippage_tolerance = float(os.getenv('MAX_SLIPPAGE', '0.02'))  # 2% max slippage
        
        # Demo/Test capital limits
        self.demo_capital_kalshi = float(os.getenv('DEMO_CAPITAL_KALSHI', '1000'))
        self.demo_capital_polymarket = float(os.getenv('DEMO_CAPITAL_POLYMARKET', '1000'))
        
        # API credentials - environment specific
        self.kalshi_credentials = self._get_kalshi_credentials()
        self.ibkr_credentials = self._get_ibkr_credentials()
        self.polymarket_credentials = self._get_polymarket_credentials()
        
        # Alert settings
        self.email_enabled = os.getenv('EMAIL_ALERTS', 'False').lower() == 'true'
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK')
        self.sms_enabled = os.getenv('SMS_ALERTS', 'False').lower() == 'true'
        
        # Fee structures (same for all environments)
        self.kalshi_fees = self._get_kalshi_fee_structure()
        self.ibkr_fees = self._get_ibkr_fee_structure()
        self.polymarket_fees = self._get_polymarket_fee_structure()
        
        # Platform endpoints based on environment
        self.api_endpoints = self._get_api_endpoints()
        
    def _get_kalshi_credentials(self) -> Dict[str, Any]:
        """Get Kalshi credentials based on environment"""
        if self.environment == 'DEMO':
            return {
                'base_url': 'https://demo-api.kalshi.co/trade-api/v2',
                'api_key_id': os.getenv('KALSHI_API_KEY_ID'),
                'private_key_path': os.getenv('KALSHI_PRIVATE_KEY_FILE', 'kalshi-demo-private-key.pem'),
                'rate_limit_per_minute': 100  # More lenient for demo
            }
        elif self.environment == 'LIVE':
            return {
                'base_url': 'https://trading-api.kalshi.co/trade-api/v2',
                'api_key_id': os.getenv('KALSHI_API_KEY_ID'),
                'private_key_path': os.getenv('KALSHI_PRIVATE_KEY_FILE', 'kalshi-private-key.pem'),
                'rate_limit_per_minute': 50
            }
        else:  # PAPER - use demo for now
            return self._get_kalshi_credentials()
    
    def _get_ibkr_credentials(self) -> Dict[str, Any]:
        """Get IBKR credentials based on environment"""
        if self.environment in ['DEMO', 'PAPER']:
            return {
                'host': os.getenv('IBKR_HOST', '127.0.0.1'),
                'port': int(os.getenv('IBKR_PAPER_PORT', '7497')),  # Paper trading port
                'client_id': int(os.getenv('IBKR_CLIENT_ID', '1')),
                'account': os.getenv('IBKR_PAPER_ACCOUNT'),
                'paper_trading': True
            }
        else:  # LIVE
            return {
                'host': os.getenv('IBKR_HOST', '127.0.0.1'),
                'port': int(os.getenv('IBKR_LIVE_PORT', '7496')),  # Live trading port
                'client_id': int(os.getenv('IBKR_CLIENT_ID', '1')),
                'account': os.getenv('IBKR_LIVE_ACCOUNT'),
                'paper_trading': False
            }
    
    def _get_polymarket_credentials(self) -> Dict[str, Any]:
        """Get Polymarket credentials based on environment (read-only for arbitrage detection)"""
        # For arbitrage detection, we only need read-only access to live data
        return {
            'api_url': 'https://clob.polymarket.com',
            'gamma_url': 'https://gamma-api.polymarket.com',
            'read_only': True,  # No trading, just data collection
            'chain_id': 137,  # Polygon mainnet for live data
            'usdc_address': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
        }
    
    def _get_api_endpoints(self) -> Dict[str, Dict[str, str]]:
        """Get API endpoints for each platform"""
        return {
            'kalshi': {
                'login': '/login',
                'markets': '/markets',
                'market_orderbook': '/markets/{market_ticker}/orderbook',
                'portfolio': '/portfolio',
                'orders': '/portfolio/orders',
                'place_order': '/portfolio/orders'
            },
            'polymarket': {
                'markets': '/markets',
                'orderbook': '/book',
                'prices': '/prices',
                'trades': '/trades',
                'user_orders': '/orders'
            },
            'ibkr': {
                'host': self.ibkr_credentials['host'],
                'port': self.ibkr_credentials['port']
            }
        }
    
    def _get_kalshi_fee_structure(self) -> Dict[str, Any]:
        """
        Real Kalshi fee structure from their documentation
        Based on the fee schedule you provided
        """
        return {
            'trading_fee_formula': {
                'general': 0.07,  # 7% of expected value
                'sp500_nasdaq': 0.035,  # 3.5% for S&P500/NASDAQ markets
            },
            'maker_fees': {
                'enabled': True,
                'rate': 0.0025,  # $0.25 per 100 contracts
                'minimum_rebate': 10.0,  # $10 minimum for rebate
            },
            'trading_fee_tables': {
                # General markets - fee per contract by price
                'general': {
                    0.01: 0.01, 0.05: 0.01, 0.10: 0.01, 0.15: 0.01, 0.20: 0.02,
                    0.25: 0.02, 0.30: 0.02, 0.35: 0.02, 0.40: 0.02, 0.45: 0.02,
                    0.50: 0.02, 0.55: 0.02, 0.60: 0.02, 0.65: 0.02, 0.70: 0.02,
                    0.75: 0.02, 0.80: 0.02, 0.85: 0.01, 0.90: 0.01, 0.95: 0.01, 0.99: 0.01
                },
                # S&P500/NASDAQ markets - lower fees
                'sp500_nasdaq': {
                    0.01: 0.01, 0.05: 0.01, 0.10: 0.01, 0.15: 0.01, 0.20: 0.01,
                    0.25: 0.01, 0.30: 0.01, 0.35: 0.01, 0.40: 0.01, 0.45: 0.01,
                    0.50: 0.01, 0.55: 0.01, 0.60: 0.01, 0.65: 0.01, 0.70: 0.01,
                    0.75: 0.01, 0.80: 0.01, 0.85: 0.01, 0.90: 0.01, 0.95: 0.01, 0.99: 0.01
                }
            },
            'special_tickers': [
                'KXAAAGASM', 'KXGDP', 'KXPAYROLLS', 'KXU3', 'KXEGGS', 'KXCPI', 
                'KXCPIYOY', 'KXFEDDECISION', 'KXFED', 'KXNBA', 'KXNBAEAST', 
                'KXNBAWEST', 'KXNBASERIES', 'KXNBAGAME', 'KXNHL', 'KXNHLEAST',
                'KXNHLWEST', 'KXNHLSERIES', 'KXNHLGAME'
            ],
            'settlement_fees': 0.0,
            'membership_fees': 0.0,
            'ach_fees': 0.0,
            'debit_deposit_fee': 0.02,  # 2%
            'debit_withdrawal_fee': 2.0  # $2
        }
    
    def _get_ibkr_fee_structure(self) -> Dict[str, Any]:
        """
        IBKR ForecastEx fee structure from their documentation
        """
        return {
            'forecast_contracts': {
                'tiered': 0.0,  # $0.00 per contract
                'fixed': 0.0,   # $0.00 per contract
                'third_party_fees': None
            },
            'cme_event_contracts': {
                'tiered': 0.10,  # $0.10 per contract
                'fixed': 0.10,   # $0.10 per contract
            },
            'exchange_fees': 'varies',  # Passed through from exchange
            'regulatory_fees': 'varies',  # Passed through
            'overnight_position_fees': 'varies'
        }
    
    def _get_polymarket_fee_structure(self) -> Dict[str, Any]:
        """Polymarket fee structure"""
        return {
            'trading_fees': 0.0,  # 0% trading fees
            'gas_estimate_mainnet': 5.0,  # $5 estimate for Polygon gas
            'gas_estimate_testnet': 0.1,  # $0.10 for Mumbai testnet
            'gas_limit_estimate': 150000,  # Gas limit for typical trade
        }
    
    def get_kalshi_trading_fee(self, price: float, contracts: int, 
                              market_type: str = 'general') -> float:
        """
        Calculate Kalshi trading fee for a specific trade
        Uses real fee tables from Kalshi documentation
        """
        import math
        
        # Determine fee table to use
        fee_table = self.kalshi_fees['trading_fee_tables'][market_type]
        
        # Find closest price point in fee table
        price_points = sorted(fee_table.keys())
        closest_price = min(price_points, key=lambda x: abs(x - price))
        fee_per_contract = fee_table[closest_price]
        
        total_fee = fee_per_contract * contracts
        
        # Round up to next cent as per Kalshi rules
        return math.ceil(total_fee * 100) / 100
    
    def get_kalshi_maker_fee(self, contracts: int) -> float:
        """Calculate Kalshi maker fee for resting orders"""
        import math
        
        if not self.kalshi_fees['maker_fees']['enabled']:
            return 0.0
            
        rate = self.kalshi_fees['maker_fees']['rate']
        fee = rate * contracts
        
        # Round up to next cent
        return math.ceil(fee * 100) / 100
    
    def get_ibkr_trading_fee(self, contracts: int, contract_type: str = 'forecast') -> float:
        """Calculate IBKR trading fee"""
        if contract_type == 'forecast':
            return 0.0  # ForecastEx contracts are free
        elif contract_type == 'cme_event':
            return 0.10 * contracts
        else:
            return 0.0
    
    def get_polymarket_gas_fee(self) -> float:
        """Get estimated gas fee for Polymarket trades"""
        if self.environment in ['DEMO', 'PAPER']:
            return self.polymarket_fees['gas_estimate_testnet']
        else:
            return self.polymarket_fees['gas_estimate_mainnet']
    
    def is_sp500_or_nasdaq_market(self, ticker: str) -> bool:
        """Check if market qualifies for reduced Kalshi fees"""
        ticker_upper = ticker.upper()
        return (ticker_upper.startswith('INX') or 
                ticker_upper.startswith('NASDAQ100'))
    
    def estimate_slippage(self, price: float, volume: int, 
                         market_depth: int = 100) -> float:
        """
        Estimate slippage based on order size and market depth
        Conservative estimates for prediction markets
        """
        if volume <= 10:
            return 0.0  # No slippage for small orders
        elif volume <= 50:
            return 0.005 * price  # 0.5% for medium orders
        elif volume <= market_depth:
            return 0.01 * price   # 1% for large orders
        else:
            return 0.02 * price   # 2% for very large orders
    
    def get_total_cost_kalshi(self, contracts: int, price: float, market_type: str = 'general') -> float:
        """Calculate total cost including fees for Kalshi trade"""
        base_cost = contracts * price
        trading_fee = self.get_kalshi_trading_fee(price, contracts, market_type)
        return base_cost + trading_fee
    
    def get_total_cost_polymarket(self, contracts: int, price: float) -> float:
        """Calculate total cost including gas for Polymarket trade"""
        base_cost = contracts * price
        gas_fee = self.get_polymarket_gas_fee()
        return base_cost + gas_fee
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo/test mode"""
        return self.environment in ['DEMO', 'PAPER']
    
    def validate_configuration(self) -> bool:
        """Validate configuration settings"""
        issues = []
        
        if self.min_profit_margin_percent <= 0:
            issues.append("Minimum profit margin must be positive")
            
        if self.max_position_size <= 0:
            issues.append("Maximum position size must be positive")
            
        if self.scan_interval_seconds < 60:
            issues.append("Scan interval should be at least 60 seconds for API stability")
            
        # Check required credentials based on environment
        if self.environment == 'DEMO':
            if not self.kalshi_credentials.get('api_key_id'):
                issues.append("Kalshi API key ID required for demo mode")
            # Polymarket is read-only, no credentials needed
        elif self.environment == 'LIVE':
            if not self.kalshi_credentials.get('api_key_id'):
                issues.append("Kalshi API key ID required for live mode")
            # Polymarket is read-only, no credentials needed
            
        if issues:
            print("⚠️ Configuration issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
            
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging"""
        return {
            'environment': self.environment,
            'min_profit_margin': f"{self.min_profit_margin_percent}%",
            'max_position_size': self.max_position_size,
            'scan_interval': f"{self.scan_interval_seconds}s",
            'max_exposure': f"${self.max_total_exposure:,.2f}",
            'demo_mode': self.is_demo_mode(),
            'kalshi_fees_enabled': True,
            'ibkr_fees_enabled': True,
            'polymarket_fees_enabled': True,
            'alerts_email': self.email_enabled,
            'alerts_discord': bool(self.discord_webhook),
            'alerts_sms': self.sms_enabled
        }

# Global settings instance
settings = Settings()