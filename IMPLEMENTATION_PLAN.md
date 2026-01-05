# PolyTracker Implementation Plan

## Executive Summary

This document outlines the implementation plan for enhancing PolyTracker - a suspicious wallet activity monitoring system for Polymarket. The enhancements focus on improving detection accuracy, adding manual wallet tracking, expanding notification channels, and providing comprehensive customization options.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Requirements](#2-requirements)
3. [Architecture Overview](#3-architecture-overview)
4. [Implementation Phases](#4-implementation-phases)
5. [Detailed Task Breakdown](#5-detailed-task-breakdown)
6. [Database Schema Changes](#6-database-schema-changes)
7. [API Design](#7-api-design)
8. [Configuration System](#8-configuration-system)
9. [Testing Strategy](#9-testing-strategy)
10. [Risk Assessment](#10-risk-assessment)

---

## 1. Current State Analysis

### What Exists
- Basic monitoring engine (`polymarket_monitor.py`)
- Streamlit dashboard (`dashboard.py`)
- SQLite database with 3 tables
- Telegram alerting (partial)
- Fixed detection thresholds

### Critical Issues to Address
| Issue | Severity | Description |
|-------|----------|-------------|
| Wallet age detection broken | Critical | `get_wallet_age_days()` always returns `None` |
| No manual wallet tracking | High | Cannot add specific wallets to monitor |
| No Slack integration | High | Only Telegram supported |
| Hardcoded categories | Medium | Limited to News/Crypto/Politics |
| No configuration file | Medium | All settings hardcoded |
| Database connection leaks | Medium | Missing context managers |
| No retry logic for APIs | Medium | Transient failures cause data loss |

---

## 2. Requirements

### Functional Requirements

#### FR-1: Suspicious Bet Detection
- **FR-1.1**: Detect fresh wallets (configurable age threshold)
- **FR-1.2**: Detect large bets (configurable size threshold)
- **FR-1.3**: Detect low-odds bets (configurable odds threshold)
- **FR-1.4**: Combine criteria with AND/OR logic

#### FR-2: Manual Wallet Monitoring
- **FR-2.1**: Add wallet addresses manually via dashboard
- **FR-2.2**: Add wallet addresses via API/CLI
- **FR-2.3**: Assign labels/notes to monitored wallets
- **FR-2.4**: Track ALL activity from monitored wallets (bypass thresholds)
- **FR-2.5**: Remove wallets from monitoring list

#### FR-3: Multi-Channel Alerts
- **FR-3.1**: Telegram alerts (existing, needs improvement)
- **FR-3.2**: Slack webhook integration (new)
- **FR-3.3**: Configurable alert templates
- **FR-3.4**: Alert deduplication
- **FR-3.5**: Alert rate limiting (prevent spam)

#### FR-4: Category Customization
- **FR-4.1**: Enable/disable specific categories
- **FR-4.2**: Support categories: Crypto, Sports, Politics, News, Entertainment, Science, Business
- **FR-4.3**: Add custom category keywords
- **FR-4.4**: Per-category threshold overrides

#### FR-5: Configuration Management
- **FR-5.1**: YAML/JSON configuration file
- **FR-5.2**: Environment variable overrides
- **FR-5.3**: Runtime configuration via dashboard
- **FR-5.4**: Configuration validation

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | API response handling | Retry 3x with exponential backoff |
| NFR-2 | Database performance | Index on frequently queried columns |
| NFR-3 | Scan frequency | Configurable, default 5 minutes |
| NFR-4 | Alert latency | < 30 seconds from detection |
| NFR-5 | Uptime | Handle API failures gracefully |

---

## 3. Architecture Overview

### Current Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ Polymarket APIs │────▶│ PolymarketMonitor│────▶│   SQLite    │
└─────────────────┘     └──────────────────┘     └─────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │   Telegram   │
                        └──────────────┘
```

### Proposed Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                        Configuration                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ config.yaml │  │    .env     │  │ Dashboard Runtime Config│  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Engine                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ API Client   │  │ Trade        │  │ Wallet Tracker     │     │
│  │ (with retry) │  │ Analyzer     │  │ (manual + auto)    │     │
│  └──────────────┘  └──────────────┘  └────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    SQLite Database                        │   │
│  │  - suspicious_trades (with indexes)                       │   │
│  │  - markets_cache                                          │   │
│  │  - wallet_analysis                                        │   │
│  │  - monitored_wallets (NEW)                               │   │
│  │  - alert_history (NEW)                                    │   │
│  │  - categories_config (NEW)                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Notification Service                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Telegram   │  │    Slack     │  │   (Future)   │          │
│  │   Notifier   │  │   Notifier   │  │   Discord    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Streamlit Dashboard                          │   │
│  │  - Real-time monitoring                                   │   │
│  │  - Manual wallet management                               │   │
│  │  - Configuration UI                                       │   │
│  │  - Analytics & Reports                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation Phases

### Phase 1: Foundation & Bug Fixes (Priority: Critical)
**Goal**: Fix critical issues and establish proper foundations

| Task | Description | Complexity |
|------|-------------|------------|
| 1.1 | Fix wallet age detection using Polygonscan API | Medium |
| 1.2 | Add configuration file system (YAML) | Low |
| 1.3 | Fix database connection handling (context managers) | Low |
| 1.4 | Add API retry logic with exponential backoff | Medium |
| 1.5 | Add database indexes for performance | Low |
| 1.6 | Create requirements.txt | Low |

### Phase 2: Manual Wallet Monitoring (Priority: High)
**Goal**: Enable tracking specific wallets of interest

| Task | Description | Complexity |
|------|-------------|------------|
| 2.1 | Create `monitored_wallets` database table | Low |
| 2.2 | Add wallet CRUD operations to monitor class | Medium |
| 2.3 | Modify scan logic to include monitored wallets | Medium |
| 2.4 | Add dashboard UI for wallet management | Medium |
| 2.5 | Add CLI commands for wallet management | Low |

### Phase 3: Notification System Enhancement (Priority: High)
**Goal**: Add Slack and improve alerting

| Task | Description | Complexity |
|------|-------------|------------|
| 3.1 | Create abstract Notifier base class | Low |
| 3.2 | Refactor Telegram notifier | Low |
| 3.3 | Implement Slack webhook notifier | Medium |
| 3.4 | Add alert templates (customizable messages) | Medium |
| 3.5 | Implement alert deduplication | Low |
| 3.6 | Add rate limiting for alerts | Low |
| 3.7 | Add dashboard UI for notification config | Medium |

### Phase 4: Category Customization (Priority: Medium)
**Goal**: Allow filtering by market categories

| Task | Description | Complexity |
|------|-------------|------------|
| 4.1 | Create category configuration schema | Low |
| 4.2 | Add category filtering to market fetch | Low |
| 4.3 | Implement per-category threshold overrides | Medium |
| 4.4 | Add dashboard UI for category management | Medium |
| 4.5 | Add custom keyword matching | Low |

### Phase 5: Advanced Features (Priority: Low)
**Goal**: Additional enhancements

| Task | Description | Complexity |
|------|-------------|------------|
| 5.1 | Add historical analysis reports | Medium |
| 5.2 | Implement wallet clustering (related wallets) | High |
| 5.3 | Add export functionality (CSV, JSON) | Low |
| 5.4 | Add Discord notifications | Low |
| 5.5 | Add email notifications | Medium |

---

## 5. Detailed Task Breakdown

### Phase 1: Foundation & Bug Fixes

#### Task 1.1: Fix Wallet Age Detection
**Current Problem**: `get_wallet_age_days()` returns `None` always

**Solution**: Use Polygonscan API to get first transaction timestamp

```python
# Proposed implementation approach
def get_wallet_age_days(self, wallet_address: str) -> Optional[int]:
    """Get wallet age using Polygonscan API"""
    url = "https://api.polygonscan.com/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": wallet_address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 1,  # Only need first tx
        "sort": "asc",
        "apikey": self.polygonscan_api_key
    }
    # ... implementation
```

**Files to modify**: `polymarket_monitor.py`
**New dependencies**: None (uses existing requests)
**Config needed**: `POLYGONSCAN_API_KEY`

---

#### Task 1.2: Configuration File System

**Create**: `config.yaml`

```yaml
# Detection Thresholds
detection:
  wallet_age_days: 30
  min_bet_size: 10000
  max_odds: 0.20

# Categories to Monitor
categories:
  enabled:
    - crypto
    - news
    - politics
    - sports
  custom_keywords: []

# API Configuration
api:
  polymarket_api_key: ""
  polygonscan_api_key: ""
  scan_interval_minutes: 5
  retry_attempts: 3
  retry_backoff_base: 2

# Notifications
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

# Monitored Wallets (can also be managed via dashboard)
monitored_wallets: []
```

**Create**: `config.py` - Configuration loader

```python
# Proposed structure
class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.load_config(config_path)
        self.load_env_overrides()
        self.validate()
```

---

#### Task 1.3: Fix Database Connection Handling

**Current Problem**:
```python
conn = sqlite3.connect(self.db_path)
# ... operations
conn.close()  # Not reached if exception occurs
```

**Solution**: Use context managers

```python
def cache_market(self, market_data: Dict) -> None:
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(...)
        conn.commit()
    # Connection automatically closed
```

**Files to modify**: `polymarket_monitor.py` (all database operations)

---

#### Task 1.4: API Retry Logic

**Create**: `api_client.py`

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class PolymarketAPIClient:
    def __init__(self, config: Config):
        self.session = requests.Session()
        self.config = config

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    def get_markets(self, active_only: bool = True) -> List[Dict]:
        # ... implementation with proper error handling
```

---

#### Task 1.5: Database Indexes

**Add to init_database()**:
```sql
CREATE INDEX IF NOT EXISTS idx_suspicious_wallet
    ON suspicious_trades(wallet_address);
CREATE INDEX IF NOT EXISTS idx_suspicious_detected
    ON suspicious_trades(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_suspicious_market
    ON suspicious_trades(market_id);
CREATE INDEX IF NOT EXISTS idx_wallet_analysis_address
    ON wallet_analysis(wallet_address);
```

---

### Phase 2: Manual Wallet Monitoring

#### Task 2.1: Database Table

```sql
CREATE TABLE IF NOT EXISTS monitored_wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT UNIQUE NOT NULL,
    label TEXT,
    notes TEXT,
    added_at TEXT NOT NULL,
    added_by TEXT DEFAULT 'manual',
    is_active INTEGER DEFAULT 1,
    bypass_thresholds INTEGER DEFAULT 1,
    alert_on_any_trade INTEGER DEFAULT 0,
    last_activity TEXT,
    total_trades_tracked INTEGER DEFAULT 0
);
```

#### Task 2.2: Wallet Management Methods

```python
class WalletTracker:
    def add_wallet(self, address: str, label: str = None,
                   notes: str = None, bypass_thresholds: bool = True) -> bool

    def remove_wallet(self, address: str) -> bool

    def update_wallet(self, address: str, **kwargs) -> bool

    def get_monitored_wallets(self, active_only: bool = True) -> List[Dict]

    def is_monitored(self, address: str) -> bool
```

#### Task 2.3: Modified Scan Logic

```python
def analyze_trade(self, trade: Dict, market_data: Dict,
                  current_odds: Dict) -> Optional[Dict]:
    wallet_address = trade.get("maker_address") or trade.get("taker_address")

    # Check if wallet is manually monitored
    if self.wallet_tracker.is_monitored(wallet_address):
        monitored_config = self.wallet_tracker.get_wallet_config(wallet_address)
        if monitored_config.get("bypass_thresholds"):
            # Track ALL trades from this wallet
            return self._create_suspicious_data(trade, market_data,
                                                current_odds, source="monitored")

    # Normal threshold-based detection
    # ... existing logic
```

---

### Phase 3: Notification System

#### Task 3.1-3.2: Notifier Base Class

```python
from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    @abstractmethod
    def send_alert(self, alert_data: Dict) -> bool:
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        pass

    def format_message(self, alert_data: Dict, template: str = None) -> str:
        # Common formatting logic
        pass

class TelegramNotifier(BaseNotifier):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_alert(self, alert_data: Dict) -> bool:
        # Existing telegram logic, refactored
        pass

class SlackNotifier(BaseNotifier):
    def __init__(self, webhook_url: str, channel: str = None):
        self.webhook_url = webhook_url
        self.channel = channel

    def send_alert(self, alert_data: Dict) -> bool:
        # Slack webhook implementation
        pass
```

#### Task 3.3: Slack Implementation

```python
class SlackNotifier(BaseNotifier):
    def send_alert(self, alert_data: Dict) -> bool:
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Suspicious Activity Detected"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Market:*\n{alert_data['market_question']}"},
                    {"type": "mrkdwn", "text": f"*Category:*\n{alert_data['market_category']}"},
                    {"type": "mrkdwn", "text": f"*Wallet:*\n`{alert_data['wallet_address'][:10]}...`"},
                    {"type": "mrkdwn", "text": f"*Bet Size:*\n${alert_data['bet_size']:,.2f}"},
                    {"type": "mrkdwn", "text": f"*Position:*\n{alert_data['outcome']}"},
                    {"type": "mrkdwn", "text": f"*Odds:*\n{alert_data['odds']*100:.1f}%"}
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View on Polygonscan"},
                        "url": f"https://polygonscan.com/address/{alert_data['wallet_address']}"
                    }
                ]
            }
        ]

        payload = {"blocks": blocks}
        if self.channel:
            payload["channel"] = self.channel

        response = requests.post(self.webhook_url, json=payload)
        return response.status_code == 200
```

#### Task 3.4: Alert Templates

```yaml
# In config.yaml
alert_templates:
  default: |
    🚨 *SUSPICIOUS ACTIVITY DETECTED*

    *Market:* {market_question}
    *Wallet:* `{wallet_address}`
    *Bet Size:* ${bet_size:,.2f}
    *Odds:* {odds_percent:.1f}%

  minimal: |
    🚨 ${bet_size:,.0f} on {outcome} @ {odds_percent:.0f}% - {market_question[:50]}

  monitored_wallet: |
    👀 *MONITORED WALLET ACTIVITY*

    *Wallet:* `{wallet_address}` ({wallet_label})
    *Market:* {market_question}
    *Bet:* ${bet_size:,.2f} on {outcome}
```

---

### Phase 4: Category Customization

#### Task 4.1: Category Schema

```yaml
categories:
  crypto:
    enabled: true
    keywords: ["bitcoin", "ethereum", "crypto", "cryptocurrency", "btc", "eth"]
    thresholds:  # Optional per-category overrides
      min_bet_size: 5000
      max_odds: 0.15

  sports:
    enabled: true
    keywords: ["nfl", "nba", "soccer", "football", "basketball", "tennis"]
    thresholds:
      min_bet_size: 20000

  politics:
    enabled: true
    keywords: ["election", "president", "congress", "senate", "politics"]

  news:
    enabled: true
    keywords: ["news", "breaking"]

  entertainment:
    enabled: false
    keywords: ["movie", "oscar", "grammy", "celebrity"]
```

#### Task 4.2: Category Filtering

```python
class CategoryManager:
    def __init__(self, config: Dict):
        self.categories = config.get("categories", {})

    def get_enabled_categories(self) -> List[str]:
        return [name for name, cfg in self.categories.items()
                if cfg.get("enabled", True)]

    def matches_category(self, market_tags: List[str], market_question: str) -> Optional[str]:
        """Returns matching category name or None"""
        for cat_name, cat_config in self.categories.items():
            if not cat_config.get("enabled", True):
                continue
            keywords = cat_config.get("keywords", [])
            # Check tags
            if any(kw.lower() in [t.lower() for t in market_tags] for kw in keywords):
                return cat_name
            # Check question text
            if any(kw.lower() in market_question.lower() for kw in keywords):
                return cat_name
        return None

    def get_thresholds(self, category: str) -> Dict:
        """Get category-specific thresholds or defaults"""
        cat_config = self.categories.get(category, {})
        return cat_config.get("thresholds", {})
```

---

## 6. Database Schema Changes

### New Tables

```sql
-- Monitored Wallets
CREATE TABLE IF NOT EXISTS monitored_wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT UNIQUE NOT NULL,
    label TEXT,
    notes TEXT,
    added_at TEXT NOT NULL,
    added_by TEXT DEFAULT 'manual',
    is_active INTEGER DEFAULT 1,
    bypass_thresholds INTEGER DEFAULT 1,
    alert_on_any_trade INTEGER DEFAULT 0,
    last_activity TEXT,
    total_trades_tracked INTEGER DEFAULT 0
);

-- Alert History (for deduplication and rate limiting)
CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,  -- 'telegram', 'slack', etc.
    sent_at TEXT NOT NULL,
    success INTEGER DEFAULT 1,
    error_message TEXT,
    UNIQUE(trade_id, alert_type)
);

-- Category Configuration (optional, can use config file)
CREATE TABLE IF NOT EXISTS category_config (
    category_name TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 1,
    keywords TEXT,  -- JSON array
    min_bet_size REAL,
    max_odds REAL,
    wallet_age_days INTEGER
);
```

### Modified Tables

```sql
-- Add source column to suspicious_trades
ALTER TABLE suspicious_trades ADD COLUMN detection_source TEXT DEFAULT 'automatic';
-- Values: 'automatic', 'monitored_wallet', 'manual'

-- Add category match column
ALTER TABLE suspicious_trades ADD COLUMN matched_category TEXT;
```

### Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_suspicious_wallet ON suspicious_trades(wallet_address);
CREATE INDEX IF NOT EXISTS idx_suspicious_detected ON suspicious_trades(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_suspicious_market ON suspicious_trades(market_id);
CREATE INDEX IF NOT EXISTS idx_monitored_address ON monitored_wallets(wallet_address);
CREATE INDEX IF NOT EXISTS idx_monitored_active ON monitored_wallets(is_active);
CREATE INDEX IF NOT EXISTS idx_alert_trade ON alert_history(trade_id);
```

---

## 7. API Design

### CLI Interface

```bash
# Wallet Management
polytracker wallet add <address> [--label "Whale 1"] [--notes "Suspicious activity"]
polytracker wallet remove <address>
polytracker wallet list [--active-only]
polytracker wallet update <address> --label "New Label"

# Scanning
polytracker scan [--once] [--interval 5]
polytracker scan --categories crypto,sports

# Configuration
polytracker config show
polytracker config set detection.min_bet_size 5000
polytracker config validate

# Alerts
polytracker alert test telegram
polytracker alert test slack
polytracker alert history [--limit 50]

# Reports
polytracker report daily [--date 2024-01-15]
polytracker export --format csv --output trades.csv
```

### Dashboard API Endpoints (if REST API added later)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/wallets` | List monitored wallets |
| POST | `/api/wallets` | Add wallet to monitor |
| DELETE | `/api/wallets/{address}` | Remove wallet |
| PATCH | `/api/wallets/{address}` | Update wallet config |
| GET | `/api/trades` | List suspicious trades |
| GET | `/api/stats` | Get summary statistics |
| POST | `/api/scan` | Trigger manual scan |
| GET | `/api/config` | Get current configuration |
| PATCH | `/api/config` | Update configuration |

---

## 8. Configuration System

### Priority Order (highest to lowest)
1. Environment variables (for secrets)
2. Runtime configuration (dashboard changes)
3. config.yaml file
4. Default values in code

### Environment Variables

```bash
# .env file
POLYMARKET_API_KEY=your_api_key
POLYGONSCAN_API_KEY=your_polygonscan_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
DATABASE_PATH=polymarket_monitor.db
```

### Configuration Validation

```python
class ConfigValidator:
    def validate(self, config: Dict) -> List[str]:
        errors = []

        # Detection thresholds
        if config["detection"]["min_bet_size"] < 0:
            errors.append("min_bet_size must be positive")
        if not 0 < config["detection"]["max_odds"] <= 1:
            errors.append("max_odds must be between 0 and 1")
        if config["detection"]["wallet_age_days"] < 1:
            errors.append("wallet_age_days must be at least 1")

        # Notifications
        if config["notifications"]["telegram"]["enabled"]:
            if not config["notifications"]["telegram"]["bot_token"]:
                errors.append("Telegram bot_token required when enabled")
            if not config["notifications"]["telegram"]["chat_id"]:
                errors.append("Telegram chat_id required when enabled")

        if config["notifications"]["slack"]["enabled"]:
            if not config["notifications"]["slack"]["webhook_url"]:
                errors.append("Slack webhook_url required when enabled")

        return errors
```

---

## 9. Testing Strategy

### Unit Tests

```
tests/
├── test_monitor.py
│   ├── test_analyze_trade()
│   ├── test_wallet_age_detection()
│   ├── test_threshold_checking()
│   └── test_database_operations()
├── test_notifiers.py
│   ├── test_telegram_send()
│   ├── test_slack_send()
│   └── test_rate_limiting()
├── test_wallet_tracker.py
│   ├── test_add_wallet()
│   ├── test_remove_wallet()
│   └── test_monitored_wallet_detection()
├── test_categories.py
│   ├── test_category_matching()
│   └── test_per_category_thresholds()
└── test_config.py
    ├── test_config_loading()
    ├── test_env_overrides()
    └── test_validation()
```

### Integration Tests

```python
class TestEndToEnd:
    def test_full_scan_cycle(self):
        """Test complete scan with detection and alerting"""
        pass

    def test_monitored_wallet_tracking(self):
        """Test that monitored wallets are tracked correctly"""
        pass

    def test_multi_channel_alerts(self):
        """Test alerts go to both Telegram and Slack"""
        pass
```

### Mock Strategy

- Mock Polymarket API responses
- Mock Polygonscan API responses
- Mock Telegram/Slack APIs
- Use in-memory SQLite for tests

---

## 10. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Polymarket API changes | Medium | High | Abstract API client, version detection |
| Polygonscan rate limits | High | Medium | Caching, API key, backoff |
| False positives | Medium | Medium | Tunable thresholds, manual review |
| Database corruption | Low | High | Regular backups, WAL mode |
| Notification failures | Medium | Medium | Retry logic, fallback channels |
| High volume of alerts | Medium | Low | Rate limiting, digest mode |

---

## File Structure After Implementation

```
PolyTracker/
├── polymarket_monitor.py      # Core monitor (refactored)
├── dashboard.py               # Streamlit UI (enhanced)
├── config.py                  # Configuration management
├── config.yaml                # Configuration file
├── api_client.py              # API client with retry
├── wallet_tracker.py          # Manual wallet management
├── notifiers/
│   ├── __init__.py
│   ├── base.py                # BaseNotifier ABC
│   ├── telegram.py            # TelegramNotifier
│   └── slack.py               # SlackNotifier
├── categories.py              # Category management
├── database.py                # Database operations
├── cli.py                     # CLI interface
├── requirements.txt           # Dependencies
├── .env.example               # Environment template
├── tests/
│   ├── __init__.py
│   ├── test_monitor.py
│   ├── test_notifiers.py
│   ├── test_wallet_tracker.py
│   └── conftest.py            # Pytest fixtures
├── docs/
│   ├── README.md
│   ├── CONFIGURATION.md
│   ├── API.md
│   └── DEPLOYMENT.md
└── README.md                  # Main documentation
```

---

## Next Steps

1. **Review this plan** and provide feedback
2. **Prioritize features** based on your needs
3. **Approve implementation** phase by phase
4. **Provide API keys** for Polygonscan (required for wallet age detection)

---

*Document Version: 1.0*
*Created: 2026-01-05*
*Author: Claude Code*
