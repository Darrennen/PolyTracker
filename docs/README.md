# PolyTracker Documentation

## Polymarket Suspicious Activity Monitor

A comprehensive monitoring system for detecting suspicious betting patterns on Polymarket prediction markets.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [Dashboard Guide](#dashboard-guide)
8. [Alert Notifications](#alert-notifications)
9. [Manual Wallet Monitoring](#manual-wallet-monitoring)
10. [Detection Logic](#detection-logic)
11. [Database Schema](#database-schema)
12. [API Reference](#api-reference)
13. [Troubleshooting](#troubleshooting)
14. [Contributing](#contributing)

---

## Overview

PolyTracker monitors Polymarket prediction markets to detect potentially suspicious betting activity. It identifies trades that match patterns commonly associated with insider trading or market manipulation:

- **Fresh wallets** making large bets
- **Large bet sizes** above configurable thresholds
- **Low-odds bets** suggesting potential insider knowledge
- **Specific categories** like Crypto, News, Politics, Sports

### Use Cases

- Market surveillance and compliance
- Research on prediction market behavior
- Identifying potential insider trading
- Tracking specific wallets of interest

---

## Features

### Core Detection
| Feature | Description |
|---------|-------------|
| Wallet Age Detection | Flag wallets younger than N days |
| Bet Size Threshold | Flag bets larger than $X |
| Odds Threshold | Flag bets on outcomes with < Y% probability |
| Category Filtering | Monitor specific market categories |

### Notifications
| Channel | Status |
|---------|--------|
| Telegram | Supported |
| Slack | Planned |
| Discord | Planned |
| Email | Planned |

### Dashboard
- Real-time suspicious activity feed
- Wallet deep-dive analysis
- Historical statistics and charts
- Configurable filters and thresholds

### Manual Wallet Tracking
- Add specific wallets to monitor
- Track ALL activity from monitored wallets
- Assign labels and notes
- Bypass automatic thresholds

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/PolyTracker.git
cd PolyTracker
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
```
requests>=2.28.0
streamlit>=1.28.0
pandas>=1.5.0
plotly>=5.15.0
pyyaml>=6.0
python-dotenv>=1.0.0
tenacity>=8.2.0
```

### Step 3: Configuration

```bash
# Copy example configuration
cp config.example.yaml config.yaml

# Copy environment template
cp .env.example .env

# Edit with your settings
nano config.yaml
nano .env
```

---

## Quick Start

### Option 1: Command Line (Single Scan)

```bash
python polymarket_monitor.py
```

### Option 2: Continuous Monitoring

```python
from polymarket_monitor import PolymarketMonitor

monitor = PolymarketMonitor()
monitor.run_continuous(interval_minutes=5)
```

### Option 3: Dashboard

```bash
streamlit run dashboard.py
```

Then open http://localhost:8501 in your browser.

---

## Configuration

### Configuration File (config.yaml)

```yaml
# Detection Thresholds
detection:
  wallet_age_days: 30      # Flag wallets younger than this
  min_bet_size: 10000      # Flag bets larger than this ($)
  max_odds: 0.20           # Flag bets on outcomes below this probability

# Market Categories to Monitor
categories:
  enabled:
    - crypto
    - news
    - politics
    - sports
  custom_keywords: []      # Additional keywords to match

# API Configuration
api:
  polymarket_api_key: ""   # Optional: for higher rate limits
  polygonscan_api_key: ""  # Required: for wallet age detection
  scan_interval_minutes: 5
  retry_attempts: 3

# Telegram Notifications
notifications:
  telegram:
    enabled: false
    bot_token: ""
    chat_id: ""
  slack:
    enabled: false
    webhook_url: ""
    channel: "#polymarket-alerts"

# Database
database:
  path: "polymarket_monitor.db"
```

### Environment Variables (.env)

For sensitive values, use environment variables:

```bash
# API Keys
POLYMARKET_API_KEY=your_polymarket_key
POLYGONSCAN_API_KEY=your_polygonscan_key

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=-1001234567890

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/XXX

# Database
DATABASE_PATH=polymarket_monitor.db
```

### Configuration Priority

1. Environment variables (highest priority)
2. config.yaml file
3. Default values in code

---

## Usage

### Python API

```python
from polymarket_monitor import PolymarketMonitor

# Initialize with defaults
monitor = PolymarketMonitor()

# Initialize with custom settings
monitor = PolymarketMonitor(
    db_path="custom.db",
    telegram_token="your_token",
    telegram_chat_id="your_chat_id",
    api_key="your_api_key"
)

# Override thresholds
monitor.WALLET_AGE_DAYS = 14    # More aggressive
monitor.MIN_BET_SIZE = 5000     # Lower threshold
monitor.MAX_ODDS = 0.15         # Even lower odds

# Run single scan
monitor.scan_markets()

# Run continuous monitoring
monitor.run_continuous(interval_minutes=10)

# Query results
trades = monitor.get_suspicious_trades(limit=100)
stats = monitor.get_wallet_stats("0x1234...")
```

### CLI Commands (Planned)

```bash
# Basic operations
polytracker scan                    # Run single scan
polytracker scan --continuous       # Run continuously
polytracker scan --interval 5       # Custom interval (minutes)

# Wallet management
polytracker wallet add 0x1234... --label "Whale 1"
polytracker wallet list
polytracker wallet remove 0x1234...

# Configuration
polytracker config show
polytracker config set detection.min_bet_size 5000

# Alerts
polytracker alert test telegram
polytracker alert test slack

# Reports
polytracker report --format csv --output report.csv
```

---

## Dashboard Guide

### Starting the Dashboard

```bash
streamlit run dashboard.py
```

### Sidebar Configuration

| Section | Description |
|---------|-------------|
| Database Path | SQLite database location |
| Polymarket API | Optional API key for better rate limits |
| Detection Filters | Customize thresholds |
| Telegram Alerts | Configure Telegram notifications |
| Scanning | Manual scan controls |

### Main Tabs

#### Tab 1: Dashboard
- Time series chart of suspicious activity
- Top markets with suspicious bets
- Bet size distribution

#### Tab 2: Recent Activity
- Live feed of detected suspicious trades
- Advanced filtering (bet size, odds, position)
- Quick actions (view on Polygonscan, Arkham)

#### Tab 3: Wallet Analysis
- Deep-dive into specific wallets
- Trade history and patterns
- Position breakdown (YES vs NO)
- Betting timeline visualization

#### Tab 4: Statistics
- Position analysis (YES vs NO trends)
- Wallet age distribution
- Category breakdown
- Bet size vs odds correlation

---

## Alert Notifications

### Telegram Setup

1. **Create a Bot**
   - Message @BotFather on Telegram
   - Send `/newbot` and follow prompts
   - Save the bot token

2. **Get Chat ID**
   - Add bot to your group/channel
   - Send a message in the group
   - Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find `chat.id` in the response

3. **Configure**
   ```yaml
   notifications:
     telegram:
       enabled: true
       bot_token: "123456:ABC-DEF..."
       chat_id: "-1001234567890"
   ```

4. **Test**
   - Use "Test Telegram Connection" button in dashboard
   - Or run: `polytracker alert test telegram`

### Slack Setup (Planned)

1. **Create Webhook**
   - Go to Slack App Directory
   - Create new app or use existing
   - Add "Incoming Webhooks" feature
   - Create webhook for your channel

2. **Configure**
   ```yaml
   notifications:
     slack:
       enabled: true
       webhook_url: "https://hooks.slack.com/services/..."
       channel: "#polymarket-alerts"
   ```

### Alert Format

**Telegram Alert Example:**
```
🚨 SUSPICIOUS ACTIVITY DETECTED 🚨

Market: Will Bitcoin reach $100k by Dec 2024?
Category: crypto

Wallet: 0x1234...abcd
Wallet Age: 5 days

Bet Details:
• Size: $50,000.00
• Outcome: YES
• Odds: 12.5%

Time: 2024-01-15T14:30:00Z

View on Polygonscan
```

---

## Manual Wallet Monitoring

### Adding Wallets

**Via Dashboard:**
1. Go to "Wallet Analysis" tab
2. Enter wallet address in "Quick Wallet Lookup"
3. Click "Add to Monitored" button (coming soon)

**Via Python:**
```python
monitor.wallet_tracker.add_wallet(
    address="0x1234567890abcdef...",
    label="Whale #1",
    notes="Large trader spotted on crypto markets",
    bypass_thresholds=True  # Track ALL trades
)
```

**Via CLI (Planned):**
```bash
polytracker wallet add 0x1234... --label "Whale #1" --notes "Suspicious"
```

### Monitoring Behavior

| Setting | Behavior |
|---------|----------|
| `bypass_thresholds=True` | Track ALL trades from wallet |
| `bypass_thresholds=False` | Only track trades meeting thresholds |
| `alert_on_any_trade=True` | Send alert for every trade |
| `alert_on_any_trade=False` | Only alert on suspicious trades |

---

## Detection Logic

### Algorithm Flow

```
For each market in [News, Crypto, Politics, Sports]:
    Fetch current market odds
    Fetch recent trades

    For each trade:
        1. Extract wallet address
        2. Calculate bet value (size × price)

        3. IF bet_value < MIN_BET_SIZE:
              SKIP (too small)

        4. IF market_odds > MAX_ODDS:
              SKIP (betting on likely outcome)

        5. Get wallet age from blockchain

        6. IF wallet_age < WALLET_AGE_DAYS OR wallet is monitored:
              FLAG AS SUSPICIOUS
              Save to database
              Send alerts
```

### Detection Criteria

A trade is flagged as suspicious when ALL of these are true:

| Criterion | Default | Description |
|-----------|---------|-------------|
| Bet Size | > $10,000 | Large financial commitment |
| Market Odds | < 20% | Betting on unlikely outcome |
| Wallet Age | < 30 days | Recently created wallet |

### Why These Criteria?

- **Fresh wallets + large bets** = Possible wash trading or insider
- **Low odds + large bets** = Possible insider knowledge
- **Combined criteria** = High suspicion of manipulation

---

## Database Schema

### Tables

#### suspicious_trades
Primary table for detected suspicious activity.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| trade_id | TEXT | Polymarket trade ID (unique) |
| wallet_address | TEXT | Trader's wallet |
| market_id | TEXT | Market identifier |
| market_question | TEXT | Market question text |
| market_category | TEXT | Category tags |
| bet_size | REAL | Bet amount in USD |
| outcome | TEXT | YES or NO |
| odds | REAL | Market odds (0-1) |
| timestamp | TEXT | Trade timestamp |
| wallet_age_days | INTEGER | Wallet age at detection |
| detected_at | TEXT | When flagged |
| alerted | INTEGER | Alert sent (0/1) |

#### markets_cache
Cache of monitored markets.

| Column | Type | Description |
|--------|------|-------------|
| market_id | TEXT | Primary key |
| question | TEXT | Market question |
| category | TEXT | Category tags |
| active | INTEGER | Is active (0/1) |
| cached_at | TEXT | Cache timestamp |

#### wallet_analysis
Aggregated wallet statistics.

| Column | Type | Description |
|--------|------|-------------|
| wallet_address | TEXT | Primary key |
| first_seen | TEXT | First detection time |
| total_bets | INTEGER | Count of all bets |
| total_volume | REAL | Sum of bet sizes |
| suspicious_bets | INTEGER | Count of suspicious bets |
| last_updated | TEXT | Last activity time |

#### monitored_wallets (Planned)
Manually tracked wallets.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| wallet_address | TEXT | Wallet address (unique) |
| label | TEXT | User-assigned label |
| notes | TEXT | Notes about wallet |
| added_at | TEXT | When added |
| is_active | INTEGER | Is monitoring active |
| bypass_thresholds | INTEGER | Track all trades |

---

## API Reference

### PolymarketMonitor Class

```python
class PolymarketMonitor:
    # Class Constants
    BASE_URL = "https://clob.polymarket.com"
    GAMMA_URL = "https://gamma-api.polymarket.com"
    WALLET_AGE_DAYS = 30
    MIN_BET_SIZE = 10000
    MAX_ODDS = 0.20

    def __init__(
        self,
        db_path: str = "polymarket_monitor.db",
        telegram_token: str = None,
        telegram_chat_id: str = None,
        api_key: str = None
    )

    def init_database(self) -> None
    def get_markets(self, active_only: bool = True) -> List[Dict]
    def get_trades(self, market_id: str) -> List[Dict]
    def get_market_prices(self, market_id: str) -> Dict
    def analyze_trade(self, trade: Dict, market_data: Dict, current_odds: Dict) -> Optional[Dict]
    def save_suspicious_trade(self, suspicious_data: Dict) -> bool
    def send_telegram_alert(self, suspicious_data: Dict) -> bool
    def scan_markets(self) -> None
    def get_suspicious_trades(self, limit: int = 100) -> List[Dict]
    def get_wallet_stats(self, wallet_address: str) -> Optional[Dict]
    def run_continuous(self, interval_minutes: int = 10) -> None
```

### Data Structures

**Suspicious Trade Data:**
```python
{
    "trade_id": "abc123",
    "wallet_address": "0x1234...",
    "market_id": "market_456",
    "market_question": "Will X happen?",
    "market_category": "crypto, news",
    "bet_size": 50000.0,
    "outcome": "YES",
    "odds": 0.15,
    "timestamp": "2024-01-15T14:30:00Z",
    "wallet_age_days": 5
}
```

**Wallet Stats:**
```python
{
    "wallet_address": "0x1234...",
    "first_seen": "2024-01-10T10:00:00Z",
    "total_bets": 15,
    "total_volume": 250000.0,
    "suspicious_bets": 8,
    "last_updated": "2024-01-15T14:30:00Z",
    "trades": [...]  # List of trade dicts
}
```

---

## Troubleshooting

### Common Issues

#### "No suspicious activity detected"

**Possible causes:**
1. Thresholds too restrictive
2. No matching categories
3. API rate limited

**Solutions:**
- Lower `MIN_BET_SIZE` threshold
- Increase `MAX_ODDS` threshold
- Add API key for higher rate limits
- Check enabled categories

#### "Wallet age always unknown"

**Cause:** Polygonscan API not configured or rate limited

**Solution:**
1. Get free API key from https://polygonscan.com/apis
2. Add to config: `polygonscan_api_key: "your_key"`

#### "Telegram alerts not sending"

**Check:**
1. Bot token is correct
2. Chat ID is correct (include `-` for groups)
3. Bot is added to the chat
4. Use "Test Connection" to verify

#### "Database locked" error

**Cause:** Multiple processes accessing SQLite

**Solution:**
- Ensure only one scanner runs at a time
- Or switch to PostgreSQL for multi-process

#### "Rate limited by API"

**Solutions:**
1. Add Polymarket API key
2. Increase `scan_interval_minutes`
3. Reduce number of categories monitored

### Logs

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Log location: stdout (configure file handler for production)

---

## Contributing

### Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/PolyTracker.git
cd PolyTracker
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
flake8 .
black --check .
```

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public methods
- Add tests for new features

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Write tests
4. Ensure all tests pass
5. Submit PR with description

---

## License

MIT License - see LICENSE file

---

## Disclaimer

This tool is for research and educational purposes. It does not constitute financial advice. Trading on prediction markets carries risk. Always do your own research.

---

*Documentation Version: 1.0*
*Last Updated: 2026-01-05*
