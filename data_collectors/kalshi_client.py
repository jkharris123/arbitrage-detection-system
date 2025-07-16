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
    """Fixed Kalshi API client with proper private key loading"""
    
    def __init__(self):
        load_dotenv()
        
        self.api_key_id = os.getenv('KALSHI_API_KEY_ID')
        self.base_url = "https://demo-api.kalshi.co/trade-api/v2"
        
        self.private_key = None
        self.session = requests.Session()
        
        print("🔍 FIXED DEBUG: Initializing KalshiClient...")
        self._load_private_key()
        self._test_connection()
    
    def _load_private_key(self):
        """Load private key with multiple methods"""
        print("🔍 Loading private key...")
        
        # Method 1: Try loading from separate file (recommended)
        key_file = os.getenv('KALSHI_PRIVATE_KEY_FILE', 'kalshi-private-key.pem')
        if os.path.exists(key_file):
            print(f"🔍 Loading from file: {key_file}")
            try:
                with open(key_file, 'r') as f:
                    key_content = f.read()
                self.private_key = serialization.load_pem_private_key(
                    key_content.encode('utf-8'),
                    password=None
                )
                print("✅ Private key loaded from file successfully")
                return
            except Exception as e:
                print(f"⚠️ Failed to load from file: {e}")
        
        # Method 2: Try loading from environment variable (with fixes)
        private_key_str = os.getenv('KALSHI_PRIVATE_KEY')
        if private_key_str:
            print(f"🔍 Loading from environment variable...")
            print(f"🔍 Raw key length: {len(private_key_str)}")
            
            try:
                # Fix common formatting issues
                fixed_key = self._fix_private_key_format(private_key_str)
                print(f"🔍 Fixed key length: {len(fixed_key)}")
                
                self.private_key = serialization.load_pem_private_key(
                    fixed_key.encode('utf-8'),
                    password=None
                )
                print("✅ Private key loaded from environment successfully")
                return
                
            except Exception as e:
                print(f"⚠️ Failed to load from environment: {e}")
        
        raise ValueError("Could not load private key from file or environment")
    
    def _fix_private_key_format(self, key_str: str) -> str:
        """Fix common private key formatting issues"""
        print("🔍 Fixing private key format...")
        
        # Remove any quotes
        key_str = key_str.strip('"\'')
        
        # Fix literal \n characters
        if '\\n' in key_str:
            print("🔧 Fixing literal \\n characters...")
            key_str = key_str.replace('\\n', '\n')
        
        # Ensure proper BEGIN/END format
        if not key_str.startswith('-----BEGIN'):
            print("⚠️ Key doesn't start with -----BEGIN")
        
        if not key_str.endswith('-----'):
            print("⚠️ Key doesn't end with -----")
        
        # Debug output
        lines = key_str.split('\n')
        print(f"🔍 Key has {len(lines)} lines")
        print(f"🔍 First line: {lines[0] if lines else 'EMPTY'}")
        print(f"🔍 Last line: {lines[-1] if lines else 'EMPTY'}")
        
        return key_str
    
    def _test_connection(self):
        """Test basic connection"""
        print("🔍 Testing connection...")
        try:
            # Test public endpoint first
            response = self.session.get(f"{self.base_url}/exchange/status", timeout=10)
            print(f"🔍 Exchange status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Basic connection successful")
            else:
                print(f"⚠️ Unexpected status: {response.status_code}")
                
        except Exception as e:
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
    
    def test_authentication(self):
        """Test authenticated endpoint"""
        print("🧪 Testing authentication...")
        
        path = "/trade-api/v2/portfolio/balance"
        timestamp_str = str(int(time.time() * 1000))
        
        try:
            signature = self._sign_request("GET", path, timestamp_str)
            
            headers = {
                'KALSHI-ACCESS-KEY': self.api_key_id,
                'KALSHI-ACCESS-SIGNATURE': signature,
                'KALSHI-ACCESS-TIMESTAMP': timestamp_str,
                'Content-Type': 'application/json'
            }
            
            response = self.session.get(
                f"{self.base_url}/portfolio/balance",
                headers=headers,
                timeout=10
            )
            
            print(f"🔍 Auth test status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Authentication successful!")
                return response.json()
            elif response.status_code == 401:
                print("❌ Authentication failed - check API key or signature")
                print(f"🔍 Response: {response.text}")
            else:
                print(f"⚠️ Unexpected response: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
            
        return None
    
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
    
    print(f"📝 Placing order: {action} {count} {ticker} {side} @ ${price}")
    
    response = self._make_authenticated_request("POST", "/portfolio/orders", order_data)
    
    if response:
        print(f"✅ Order placed successfully")
        return response
    else:
        print(f"❌ Order placement failed")
        return None

def test_kalshi_client():
    """Test the fixed Kalshi client"""
    try:
        print("🚀 Testing FIXED Kalshi API client...")
        
        client = KalshiClient()
        
        # Test authentication
        balance = client.test_authentication()
        
        if balance:
            print(f"💰 Account balance: {balance}")
        
        print("🎉 Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_kalshi_client()