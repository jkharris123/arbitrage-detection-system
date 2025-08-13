# Arbitrage Detection System

An automated system for detecting and executing arbitrage opportunities between Kalshi and Polymarket prediction markets.

## 🚀 Features

- **Automated Contract Matching**: Uses GPT-4o-mini to match equivalent contracts across platforms
- **Real-time Arbitrage Detection**: Continuously scans for profitable opportunities
- **Volume Optimization**: Calculates optimal trade sizes for maximum profit
- **Discord Integration**: Alerts and remote execution capabilities
- **Dual Modes**: Alert-only or fully automated execution

## 📁 Project Structure

```
arbitrage_bot/
├── src/                      # Main source code
│   ├── matchers/            # Contract matching logic
│   ├── detectors/           # Arbitrage detection
│   ├── bots/                # Discord and automation
│   └── data_collectors/     # API clients for platforms
├── tests/                   # Test files
├── docs/                    # Documentation
├── scripts/                 # Setup and utility scripts
├── keys/                    # API keys and credentials
├── output/                  # Generated files and logs
├── logs/                    # System logs
├── config/                  # Configuration files
├── run.py                   # Main entry point
├── fully_automated_enhanced.py  # Full system orchestrator
└── requirements.txt         # Python dependencies
```

## 🛠️ Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys** in `.env`:
   ```
   OPENAI_API_KEY=sk-...          # For contract matching
   KALSHI_API_KEY_ID=...          # Your Kalshi API ID
   DISCORD_BOT_TOKEN=...          # Discord bot token
   DISCORD_CHANNEL_ID=...         # Discord channel for alerts
   ```

3. **Add Kalshi private key**:
   - Place your `kalshi-private-key.pem` in the `keys/` directory

4. **Test the system**:
   ```bash
   python run.py
   ```

## 🎯 Quick Start

**Single Entry Point**: Use `run.py` for all operations

```bash
# Interactive launcher (RECOMMENDED)
python run.py

# Direct access (advanced users):
python fully_automated_enhanced.py test --mode alert
python fully_automated_enhanced.py monitor --mode alert
```

## 💡 How It Works

1. **Market Fetching**: Pulls active markets from Kalshi and Polymarket
2. **Contract Matching**: GPT-4o-mini identifies equivalent contracts
3. **Arbitrage Detection**: Calculates profit opportunities including fees
4. **Volume Optimization**: Tests multiple volumes to maximize profit
5. **Execution**: Either alerts via Discord or auto-executes trades

## 📊 Key Components

- **OpenAI Matcher** (`src/matchers/openai_enhanced_matcher.py`): Handles contract matching
- **Arbitrage Detector** (`src/detectors/`): Finds profitable opportunities
- **Discord Bot** (`src/bots/discord_bot.py`): Manages alerts and commands
- **API Clients** (`src/data_collectors/`): Interfaces with trading platforms

## 🔒 Safety Features

- Minimum profit thresholds
- Maximum position size limits
- Emergency halt functionality
- Confidence-based filtering
- Live testing mode before real execution

## 📈 Performance

- **Matching Cost**: ~$0.05-$0.25 per full scan (GPT-4o-mini)
- **Scan Frequency**: Every 15 minutes (configurable)
- **Target Profit**: $1,000+ daily from arbitrage opportunities

## 🤝 Contributing

See `docs/` for development guidelines and architecture details.

## ⚠️ Disclaimer

This software is for educational purposes. Trading involves risk. Always verify opportunities manually before executing large trades.
