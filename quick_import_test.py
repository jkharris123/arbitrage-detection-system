#!/usr/bin/env python3
import sys
import os
sys.path.append('./arbitrage')
sys.path.append('./data_collectors')

try:
    print("Testing basic imports...")
    from polymarket_client_enhanced import EnhancedPolymarketClient
    print("✅ Polymarket client OK")
    
    from detector_enhanced import EnhancedArbitrageDetector  
    print("✅ Enhanced detector OK")
    
    print("✅ ALL IMPORTS SUCCESSFUL - Syntax error fixed!")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
