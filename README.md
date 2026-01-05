# PolyTracker

**Suspicious Wallet Activity Monitor for Polymarket**

Detect and track suspicious betting patterns on Polymarket prediction markets in real-time.

---

## What It Does

PolyTracker monitors Polymarket to identify potentially suspicious trading activity:

- **Fresh Wallets** - Flags newly created wallets making large bets
- **Large Bets** - Tracks bets above configurable thresholds
- **Low-Odds Bets** - Identifies bets on unlikely outcomes (potential insider knowledge)
- **Category Filtering** - Focus on Crypto, News, Politics, Sports markets

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run single scan
python polymarket_monitor.py

# Or launch the dashboard
streamlit run dashboard.py
```

## Features

| Feature | Status |
|---------|--------|
| Suspicious trade detection | ✅ Working |
| Streamlit dashboard | ✅ Working |
| Telegram alerts | ✅ Working |
| Slack alerts | 🔄 Planned |
| Manual wallet tracking | 🔄 Planned |
| Custom category filters | 🔄 Planned |
| Configurable thresholds | ✅ Working |

## Configuration

Copy the example configuration and customize:

```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

### Default Detection Thresholds

| Threshold | Default | Description |
|-----------|---------|-------------|
| Wallet Age | < 30 days | Flag new wallets |
| Bet Size | > $10,000 | Flag large bets |
| Odds | < 20% | Flag low-probability bets |

## Documentation

- [Full Documentation](docs/README.md) - Complete usage guide
- [Implementation Plan](IMPLEMENTATION_PLAN.md) - Roadmap and technical details

## Dashboard

Launch the interactive dashboard:

```bash
streamlit run dashboard.py
```

Features:
- Real-time suspicious activity feed
- Wallet deep-dive analysis
- Historical statistics
- Configurable filters

## Requirements

- Python 3.8+
- See [requirements.txt](requirements.txt) for dependencies

## License

MIT License

## Disclaimer

This tool is for research and educational purposes only. It does not constitute financial advice.
