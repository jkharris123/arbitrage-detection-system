# Enhanced Arbitrage Bot - Quick Start Guide

## 🚀 New Enhanced Features

### ✅ What's New
1. **Individual Contract Matching**: Now matches specific thresholds (e.g., Fed rates 0%, 0.25%, 0.5% separately)
2. **Fully Automated Claude Integration**: No manual CSV export/import needed
3. **Dual Testing Modes**: Alert mode (Discord) and Auto mode (fully automated)
4. **Live Testing with PnL Tracking**: Records all opportunities for performance analysis

### 📋 Prerequisites
```bash
# Set your API keys in .env file:
ANTHROPIC_API_KEY=your_claude_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token  # For alert mode
DISCORD_CHANNEL_ID=your_channel_id       # For alert mode
```

## 🎯 Usage

### Test Run (Single Cycle)
```bash
# Test with Discord alerts
python fully_automated_enhanced.py test --mode alert

# Test with auto execution (no human intervention)
python fully_automated_enhanced.py test --mode auto
```

### Live Monitoring
```bash
# Live monitoring with Discord alerts (recommended to start)
python fully_automated_enhanced.py monitor --mode alert --interval 15

# Fully automated execution (use after testing)
python fully_automated_enhanced.py monitor --mode auto --interval 15
```

## 📊 Live Testing & PnL Tracking

All opportunities are logged to CSV files in the `output/` directory:
- `live_test_alert_YYYYMMDD.csv` - Alert mode opportunities
- `live_test_auto_YYYYMMDD.csv` - Auto mode opportunities

These files track:
- Every opportunity detected
- Execution decisions
- Timestamps
- Profit calculations

## 🔄 System Flow

1. **Fetch Markets**: Gets liquid markets from Kalshi & Polymarket
2. **Enhanced Claude Matching**: Matches individual contracts with specific thresholds
3. **Arbitrage Detection**: Scans matched pairs for profit opportunities
4. **Execution**:
   - Alert Mode: Sends to Discord, waits for your "EXECUTE A001" command
   - Auto Mode: Automatically executes all profitable opportunities

## 📱 Discord Commands (Alert Mode)

- `EXECUTE A001` - Execute opportunity A001
- `STATUS` - Show bot status
- `HALT` - Emergency stop
- `RESUME` - Resume after halt

## ⚙️ Configuration

Edit these values in `fully_automated_enhanced.py`:
- `min_profit`: Minimum profit to act on (default: $10)
- `max_days_to_expiry`: Maximum days until contract expiry (default: 14)
- `min_confidence`: Minimum Claude match confidence (default: 0.8)

## 🧪 Recommended Testing Approach

1. **Start with test runs** to verify the system works
2. **Run alert mode** for a few cycles to see opportunities
3. **Compare alert vs auto** by running both modes in parallel
4. **Analyze CSV logs** to calculate theoretical PnL
5. **Switch to auto mode** once confident

## 📈 Performance Analysis

After running for a day, analyze your results:
```python
import pandas as pd

# Load your test results
df = pd.read_csv('output/live_test_alert_20250731.csv')

# Calculate potential profits
total_profit = df['guaranteed_profit'].sum()
execution_rate = df[df['execution_decision'] == 'executed'].shape[0] / df.shape[0]

print(f"Total opportunities: {df.shape[0]}")
print(f"Potential profit: ${total_profit:.2f}")
print(f"Execution rate: {execution_rate:.1%}")
```

## ⚠️ Important Notes

- The system is in **live testing mode** - no real trades are executed yet
- All profits shown are theoretical based on orderbook data
- Monitor the CSV logs to track performance
- Start with small position sizes when switching to real trading

## 🐛 Troubleshooting

- **No opportunities found**: Markets might be efficient, try lowering `min_profit`
- **Claude API errors**: Check your API key and rate limits
- **Discord not working**: Ensure bot has proper permissions in your server
