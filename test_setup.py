"""
Quick test to verify Python environment and key libraries are working
"""

import sys
import platform
from datetime import datetime

def test_environment():
    print("=== Arbitrage Bot Environment Test ===")
    print(f"Python Version: {sys.version}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Current Time: {datetime.now()}")
    print()
    
    # Test key imports
    libraries = [
        ('requests', 'HTTP requests for APIs'),
        ('pandas', 'Data manipulation'),
        ('numpy', 'Numerical computing'),
        ('selenium', 'Web scraping'),
        ('playwright', 'Modern web scraping'),
        ('dotenv', 'Environment variables')
    ]
    
    for lib_name, description in libraries:
        try:
            __import__(lib_name)
            print(f"✅ {lib_name:<12} - {description}")
        except ImportError:
            print(f"❌ {lib_name:<12} - {description} (MISSING)")
    
    print()
    print("🚀 Environment ready for arbitrage bot development!")
    print("📊 Next: Build Kalshi API client and IBKR scraper")

if __name__ == "__main__":
    test_environment()