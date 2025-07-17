#!/bin/bash
# Cleanup script for redundant files

echo "🧹 Cleaning up redundant files..."

# Remove old versions
rm -f main.py
rm -f test_setup.py  
rm -f verify_enhanced_system.py
rm -f arbitrage/detector.py
rm -f data_collectors/polymarket_client.py

echo "✅ Cleanup complete!"
echo ""
echo "📁 Remaining core files:"
echo "✅ main_enhanced.py - Main orchestrator"
echo "✅ test_enhanced_system.py - Testing"
echo "✅ web_interface.py - Execution interface"
echo "✅ arbitrage/detector_enhanced.py - Enhanced detection"
echo "✅ data_collectors/kalshi_client.py - Kalshi API"
echo "✅ data_collectors/polymarket_client_enhanced.py - Polymarket API"
echo "✅ alerts/discord_alerter.py - Discord alerts"
echo "✅ config/settings.py - Configuration"
