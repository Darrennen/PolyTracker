"""
Polymarket Suspicious Wallet Monitor
Enhanced version using official Polymarket APIs:
- Data API (data-api.polymarket.com) - trades, activity, positions
- Gamma API (gamma-api.polymarket.com) - market metadata
- CLOB API (clob.polymarket.com) - orderbook/pricing
"""

import requests
import sqlite3
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import secrets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertChannel(Enum):
    TELEGRAM = "telegram"
    SLACK = "slack"


@dataclass
class DetectionConfig:
    """Configuration for suspicious activity detection"""
    wallet_age_days: int = 14  # Flag wallets newer than X days
    min_bet_size: float = 5000  # Minimum bet size in USD (CASH)
    max_odds: float = 0.10  # Flag bets on outcomes with odds below X (e.g., 10 cents)
    check_wallet_age: bool = True
    check_bet_size: bool = True
    check_odds: bool = True
    categories: List[str] = field(default_factory=lambda: ["news", "crypto", "politics"])


class PolymarketAPI:
    """
    Polymarket API client using official endpoints:
    - Data API: https://data-api.polymarket.com
    - Gamma API: https://gamma-api.polymarket.com  
    - CLOB API: https://clob.polymarket.com
    """
    
    DATA_API = "https://data-api.polymarket.com"
    GAMMA_API = "https://gamma-api.polymarket.com"
    CLOB_API = "https://clob.polymarket.com"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    # =========================================================================
    # Data API - Trades, Activity, Positions
    # =========================================================================
    
    def get_trades(
        self,
        user: str = None,
        market: str = None,
        event_id: int = None,
        side: str = None,
        filter_type: str = "CASH",  # CASH or TOKENS
        filter_amount: float = None,  # Min amount filter
        limit: int = 100,
        offset: int = 0,
        taker_only: bool = True
    ) -> List[Dict]:
        """
        Get trades from Data API
        
        Endpoint: GET https://data-api.polymarket.com/trades
        
        Response fields:
        - proxyWallet: User address
        - side: BUY or SELL
        - size: Number of shares
        - price: Price per share (0-1)
        - timestamp: Unix timestamp
        - outcome: YES or NO
        - title: Market title
        - transactionHash: Tx hash
        """
        try:
            url = f"{self.DATA_API}/trades"
            params = {
                "limit": min(limit, 10000),
                "offset": offset,
                "takerOnly": str(taker_only).lower()
            }
            
            if user:
                params["user"] = user
            if market:
                params["market"] = market
            if event_id:
                params["eventId"] = event_id
            if side:
                params["side"] = side
            if filter_type and filter_amount is not None:
                params["filterType"] = filter_type
                params["filterAmount"] = filter_amount
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Data API trades error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    def get_user_activity(
        self,
        user: str,
        market: str = None,
        activity_type: List[str] = None,  # TRADE, SPLIT, MERGE, REDEEM, REWARD
        side: str = None,
        start: int = None,
        end: int = None,
        sort_by: str = "TIMESTAMP",
        sort_direction: str = "DESC",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get user activity from Data API
        
        Endpoint: GET https://data-api.polymarket.com/activity
        
        Response fields:
        - proxyWallet: User address
        - type: TRADE, SPLIT, MERGE, REDEEM, REWARD, CONVERSION
        - size: Token amount
        - usdcSize: USD value
        - price: Entry price
        - side: BUY or SELL
        - outcome: YES or NO
        - timestamp: Unix timestamp
        """
        try:
            url = f"{self.DATA_API}/activity"
            params = {
                "user": user,
                "limit": min(limit, 500),
                "offset": offset,
                "sortBy": sort_by,
                "sortDirection": sort_direction
            }
            
            if market:
                params["market"] = market
            if activity_type:
                params["type"] = ",".join(activity_type)
            if side:
                params["side"] = side
            if start:
                params["start"] = start
            if end:
                params["end"] = end
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Data API activity error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching activity: {e}")
            return []
    
    def get_user_positions(self, user: str) -> List[Dict]:
        """
        Get current positions for a user
        
        Endpoint: GET https://data-api.polymarket.com/positions
        """
        try:
            url = f"{self.DATA_API}/positions"
            params = {"user": user}
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    # =========================================================================
    # Gamma API - Market Metadata
    # =========================================================================
    
    def get_events(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 50,
        offset: int = 0,
        order: str = "id",
        ascending: bool = False
    ) -> List[Dict]:
        """
        Get events (which contain markets) from Gamma API
        
        Endpoint: GET https://gamma-api.polymarket.com/events
        """
        try:
            url = f"{self.GAMMA_API}/events"
            params = {
                "limit": limit,
                "offset": offset,
                "order": order,
                "ascending": str(ascending).lower(),
                "closed": str(closed).lower()
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Gamma API events error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []
    
    def get_markets(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
        tag_id: int = None
    ) -> List[Dict]:
        """
        Get markets from Gamma API
        
        Endpoint: GET https://gamma-api.polymarket.com/markets
        """
        try:
            url = f"{self.GAMMA_API}/markets"
            params = {
                "limit": limit,
                "offset": offset,
                "closed": str(closed).lower()
            }
            
            if tag_id:
                params["tag_id"] = tag_id
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Gamma API markets error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    def get_market_by_id(self, condition_id: str) -> Optional[Dict]:
        """Get single market by condition ID"""
        try:
            url = f"{self.GAMMA_API}/markets/{condition_id}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"Error fetching market {condition_id}: {e}")
            return None
    
    # =========================================================================
    # CLOB API - Orderbook/Pricing
    # =========================================================================
    
    def get_market_prices(self, token_id: str) -> Dict:
        """
        Get current prices from CLOB API
        
        Endpoint: GET https://clob.polymarket.com/price
        """
        try:
            url = f"{self.CLOB_API}/price"
            params = {"token_id": token_id}
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return {}
    
    def get_orderbook(self, token_id: str) -> Dict:
        """Get orderbook from CLOB API"""
        try:
            url = f"{self.CLOB_API}/book"
            params = {"token_id": token_id}
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return {}


class PolygonBlockscout:
    """Helper class to get wallet creation date using Blockscout API"""

    def __init__(self, polymarket_api=None):
        self.base_url = "https://polygon.blockscout.com/api/v2"
        self.polymarket_api = polymarket_api
        self.age_cache = {}  # Cache wallet ages to reduce API calls

    def get_wallet_first_tx_timestamp(self, wallet_address: str) -> Optional[datetime]:
        """Get the timestamp of the first transaction for a wallet"""
        try:
            logger.debug(f"Fetching first tx for {wallet_address[:16]}...")

            # Get first outgoing transaction
            url = f"{self.base_url}/addresses/{wallet_address}/transactions"
            params = {"filter": "from", "sort": "asc", "limit": 1}

            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                if items:
                    first_tx = items[0]
                    timestamp_str = first_tx.get("timestamp")
                    if timestamp_str:
                        logger.debug(f"Found first tx timestamp: {timestamp_str}")
                        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            elif response.status_code == 429:
                logger.warning(f"Blockscout rate limit hit for {wallet_address[:16]}")
            else:
                logger.warning(f"Blockscout API returned {response.status_code} for {wallet_address[:16]}")

            # Fallback: check internal transactions
            url = f"{self.base_url}/addresses/{wallet_address}/internal-transactions"
            params = {"sort": "asc", "limit": 1}

            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                if items:
                    first_tx = items[0]
                    timestamp_str = first_tx.get("timestamp")
                    if timestamp_str:
                        logger.debug(f"Found first internal tx timestamp: {timestamp_str}")
                        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            logger.debug(f"No transactions found for {wallet_address[:16]}")
            return None

        except Exception as e:
            logger.error(f"Error getting wallet first tx for {wallet_address[:16]}: {e}")
            return None

    def get_wallet_age_from_polymarket(self, wallet_address: str) -> Optional[int]:
        """
        Fallback method: Use Polymarket API to get wallet's first activity
        This checks when the wallet first traded on Polymarket
        """
        if not self.polymarket_api:
            return None

        try:
            logger.debug(f"Trying Polymarket API for wallet age of {wallet_address[:16]}...")

            # Get user's activity sorted by timestamp ascending
            activity = self.polymarket_api.get_user_activity(
                user=wallet_address,
                sort_by="TIMESTAMP",
                sort_direction="ASC",
                limit=1
            )

            if activity and len(activity) > 0:
                first_activity = activity[0]
                timestamp = first_activity.get("timestamp")

                if timestamp:
                    # Timestamp is Unix epoch
                    first_activity_time = datetime.fromtimestamp(timestamp)
                    now = datetime.now()
                    age = now - first_activity_time
                    logger.info(f"Wallet {wallet_address[:16]} first Polymarket activity: {age.days} days ago")
                    return age.days

            logger.debug(f"No Polymarket activity found for {wallet_address[:16]}")
            return None

        except Exception as e:
            logger.error(f"Error getting Polymarket activity age for {wallet_address[:16]}: {e}")
            return None

    def get_wallet_age_days(self, wallet_address: str) -> Optional[int]:
        """
        Get the age of a wallet in days

        Tries multiple methods:
        1. Check cache
        2. Blockscout API (Polygon blockchain)
        3. Polymarket API (first trade activity)
        """
        wallet_address = wallet_address.lower()

        # Check cache first
        if wallet_address in self.age_cache:
            logger.debug(f"Using cached age for {wallet_address[:16]}")
            return self.age_cache[wallet_address]

        # Try Blockscout first
        first_tx_time = self.get_wallet_first_tx_timestamp(wallet_address)

        if first_tx_time:
            now = datetime.now(first_tx_time.tzinfo)
            age = now - first_tx_time
            age_days = age.days
            logger.info(f"Wallet {wallet_address[:16]} age from Blockscout: {age_days} days")
            self.age_cache[wallet_address] = age_days
            return age_days

        # Fallback to Polymarket API
        logger.info(f"Blockscout failed for {wallet_address[:16]}, trying Polymarket API...")
        age_days = self.get_wallet_age_from_polymarket(wallet_address)

        if age_days is not None:
            self.age_cache[wallet_address] = age_days
            return age_days

        logger.warning(f"Could not determine age for wallet {wallet_address[:16]}")
        return None


class AlertManager:
    """Manages alerts to Telegram and Slack"""
    
    def __init__(
        self,
        telegram_token: str = None,
        telegram_chat_id: str = None,
        slack_webhook_url: str = None
    ):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.slack_webhook_url = slack_webhook_url
    
    def send_telegram_alert(self, message: str) -> bool:
        """Send alert via Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def send_slack_alert(self, message: str) -> bool:
        """Send alert via Slack"""
        if not self.slack_webhook_url:
            return False
        
        try:
            response = requests.post(
                self.slack_webhook_url,
                json={"text": message},
                timeout=10
            )
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return False
    
    def format_alert(self, trade: Dict, channel: AlertChannel) -> str:
        """Format trade alert message"""
        wallet = trade.get('wallet_address', trade.get('proxyWallet', 'Unknown'))
        wallet_short = f"{wallet[:10]}...{wallet[-8:]}"
        wallet_age = trade.get('wallet_age_days')
        wallet_age_str = f"{wallet_age} days" if wallet_age is not None else "Unknown"
        
        # Calculate USD value
        size = float(trade.get('size', 0))
        price = float(trade.get('price', 0))
        usd_value = trade.get('usdcSize') or trade.get('bet_size') or (size * price)
        
        # Risk indicators
        risks = []
        if wallet_age is not None and wallet_age < 7:
            risks.append("🔴 VERY NEW WALLET")
        elif wallet_age is not None and wallet_age < 14:
            risks.append("🟠 NEW WALLET")
        
        if price < 0.05:
            risks.append("🔴 VERY LOW ODDS (<5¢)")
        elif price < 0.10:
            risks.append("🟠 LOW ODDS (<10¢)")
        
        if usd_value >= 50000:
            risks.append("🔴 WHALE BET (>$50k)")
        elif usd_value >= 25000:
            risks.append("🟠 LARGE BET (>$25k)")
        
        risk_str = " | ".join(risks) if risks else "⚠️ Suspicious Pattern"
        
        market_title = trade.get('title', trade.get('market_question', 'Unknown Market'))[:100]
        outcome = trade.get('outcome', 'Unknown')
        side = trade.get('side', 'Unknown')
        
        if channel == AlertChannel.TELEGRAM:
            return f"""
🚨 *SUSPICIOUS TRADE DETECTED* 🚨

{risk_str}

*Market:* {market_title}
*Position:* {outcome} ({side})

*Wallet:* `{wallet}`
*Age:* {wallet_age_str}

*Trade Details:*
• Size: *${usd_value:,.2f}*
• Entry: *{price*100:.1f}¢* on the dollar
• Shares: *{size:,.0f}*

[View on Polygonscan](https://polygonscan.com/address/{wallet})
            """
        else:
            return f"""
:rotating_light: *SUSPICIOUS TRADE DETECTED*

{risk_str}

*Market:* {market_title}
*Position:* {outcome} ({side})
*Wallet:* `{wallet}` (Age: {wallet_age_str})
*Value:* ${usd_value:,.2f} at {price*100:.1f}¢

<https://polygonscan.com/address/{wallet}|View on Polygonscan>
            """
    
    def send_alert(self, trade: Dict, channels: List[AlertChannel] = None) -> Dict[str, bool]:
        """Send alert to specified channels"""
        if channels is None:
            channels = []
            if self.telegram_token:
                channels.append(AlertChannel.TELEGRAM)
            if self.slack_webhook_url:
                channels.append(AlertChannel.SLACK)
        
        results = {}
        for channel in channels:
            message = self.format_alert(trade, channel)
            if channel == AlertChannel.TELEGRAM:
                results["telegram"] = self.send_telegram_alert(message)
            elif channel == AlertChannel.SLACK:
                results["slack"] = self.send_slack_alert(message)
        
        return results


class PolymarketMonitor:
    """Main monitoring class for Polymarket suspicious activity"""
    
    def __init__(
        self,
        db_path: str = "polymarket_monitor.db",
        telegram_token: str = None,
        telegram_chat_id: str = None,
        slack_webhook_url: str = None,
        api_key: str = None,
        config: DetectionConfig = None
    ):
        self.db_path = db_path
        self.config = config or DetectionConfig()

        # Initialize API client
        self.api = PolymarketAPI(api_key=api_key)
        # Pass API to blockchain helper for fallback wallet age detection
        self.blockchain = PolygonBlockscout(polymarket_api=self.api)
        self.alert_manager = AlertManager(
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
            slack_webhook_url=slack_webhook_url
        )

        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Suspicious trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suspicious_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE,
                wallet_address TEXT,
                market_id TEXT,
                market_question TEXT,
                market_category TEXT,
                bet_size REAL,
                outcome TEXT,
                side TEXT,
                odds REAL,
                shares REAL,
                timestamp TEXT,
                transaction_hash TEXT,
                wallet_age_days INTEGER,
                detected_at TEXT,
                alerted INTEGER DEFAULT 0,
                alert_channels TEXT,
                risk_score INTEGER DEFAULT 0,
                risk_level TEXT DEFAULT 'LOW'
            )
        """)
        
        # Tracked wallets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_wallets (
                wallet_address TEXT PRIMARY KEY,
                label TEXT,
                added_at TEXT,
                reason TEXT,
                active INTEGER DEFAULT 1,
                total_alerts INTEGER DEFAULT 0,
                last_activity TEXT
            )
        """)

        # Users table for authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Wallet analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_analysis (
                wallet_address TEXT PRIMARY KEY,
                first_seen TEXT,
                wallet_created_at TEXT,
                total_bets INTEGER DEFAULT 0,
                total_volume REAL DEFAULT 0,
                suspicious_bets INTEGER DEFAULT 0,
                last_updated TEXT
            )
        """)
        
        # Markets cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS markets_cache (
                market_id TEXT PRIMARY KEY,
                question TEXT,
                category TEXT,
                active INTEGER,
                cached_at TEXT
            )
        """)
        
        # Scan history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT,
                completed_at TEXT,
                markets_scanned INTEGER,
                trades_analyzed INTEGER,
                suspicious_found INTEGER,
                status TEXT
            )
        """)

        # Tracked markets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_markets (
                market_id TEXT PRIMARY KEY,
                question TEXT,
                category TEXT,
                end_date TEXT,
                added_at TEXT,
                active INTEGER DEFAULT 1,
                total_alerts INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Database initialized")

    # =========================================================================
    # User Authentication Methods
    # =========================================================================

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${pwd_hash}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, pwd_hash = password_hash.split('$')
            return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
        except:
            return False

    def create_user(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """
        Create a new user
        Returns: (success, message)
        """
        try:
            # Validate inputs
            if len(username) < 3:
                return False, "Username must be at least 3 characters"
            if len(password) < 6:
                return False, "Password must be at least 6 characters"
            if '@' not in email:
                return False, "Invalid email address"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if username or email already exists
            cursor.execute(
                "SELECT username, email FROM users WHERE username = ? OR email = ?",
                (username, email)
            )
            existing = cursor.fetchone()

            if existing:
                conn.close()
                if existing[0] == username:
                    return False, "Username already exists"
                else:
                    return False, "Email already registered"

            # Create user
            password_hash = self.hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, created_at, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (username, email, password_hash, datetime.now().isoformat()))

            conn.commit()
            conn.close()
            logger.info(f"User created: {username}")
            return True, "Account created successfully!"

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, f"Error: {str(e)}"

    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate user credentials
        Returns: (success, user_data)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, username, email, password_hash, is_active
                FROM users
                WHERE username = ?
            """, (username,))

            row = cursor.fetchone()

            if not row:
                conn.close()
                return False, None

            user_id, username, email, password_hash, is_active = row

            if not is_active:
                conn.close()
                return False, None

            if not self.verify_password(password, password_hash):
                conn.close()
                return False, None

            # Update last login
            cursor.execute("""
                UPDATE users
                SET last_login = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), user_id))

            conn.commit()
            conn.close()

            user_data = {
                "id": user_id,
                "username": username,
                "email": email
            }

            logger.info(f"User authenticated: {username}")
            return True, user_data

        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return False, None

    # =========================================================================
    # Wallet Tracking Methods
    # =========================================================================

    def add_tracked_wallet(
        self,
        wallet_address: str,
        label: str = None,
        reason: str = None
    ) -> bool:
        """Add wallet to tracking list"""
        try:
            wallet_address = wallet_address.lower().strip()
            
            if not wallet_address.startswith("0x") or len(wallet_address) != 42:
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO tracked_wallets 
                (wallet_address, label, added_at, reason, active)
                VALUES (?, ?, ?, ?, 1)
            """, (
                wallet_address,
                label or f"Wallet {wallet_address[:8]}",
                datetime.now().isoformat(),
                reason or "Manually added"
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error adding tracked wallet: {e}")
            return False
    
    def remove_tracked_wallet(self, wallet_address: str) -> bool:
        """Remove wallet from tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM tracked_wallets WHERE wallet_address = ?",
                (wallet_address.lower(),)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error removing wallet: {e}")
            return False
    
    def get_tracked_wallets(self, active_only: bool = True) -> List[Dict]:
        """Get all tracked wallets"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if active_only:
                cursor.execute("SELECT * FROM tracked_wallets WHERE active = 1")
            else:
                cursor.execute("SELECT * FROM tracked_wallets")
            
            columns = [d[0] for d in cursor.description]
            wallets = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.close()
            return wallets
            
        except Exception as e:
            logger.error(f"Error fetching tracked wallets: {e}")
            return []
    
    def search_wallets(self, query: str) -> List[Dict]:
        """Search wallets by address or label"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            search_term = f"%{query}%"
            cursor.execute("""
                SELECT DISTINCT wallet_address, 'tracked' as source, label as info
                FROM tracked_wallets 
                WHERE wallet_address LIKE ? OR label LIKE ?
                UNION
                SELECT DISTINCT wallet_address, 'suspicious' as source, 
                       CAST(suspicious_bets AS TEXT) || ' suspicious bets' as info
                FROM wallet_analysis 
                WHERE wallet_address LIKE ?
            """, (search_term, search_term, search_term))
            
            columns = ['wallet_address', 'source', 'info']
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error searching wallets: {e}")
            return []
    
    def is_tracked_wallet(self, wallet_address: str) -> bool:
        """Check if wallet is being tracked"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM tracked_wallets WHERE wallet_address = ? AND active = 1",
                (wallet_address.lower(),)
            )
            result = cursor.fetchone() is not None
            conn.close()
            return result
        except:
            return False

    def add_tracked_market(
        self,
        market_id: str,
        question: str = None,
        category: str = None,
        end_date: str = None
    ) -> bool:
        """Add market to tracking list"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO tracked_markets
                (market_id, question, category, end_date, added_at, active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                market_id,
                question or f"Market {market_id[:8]}...",
                category or "Unknown",
                end_date,
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error adding tracked market: {e}")
            return False

    def remove_tracked_market(self, market_id: str) -> bool:
        """Remove market from tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM tracked_markets WHERE market_id = ?",
                (market_id,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error removing market: {e}")
            return False

    def get_tracked_markets(self, active_only: bool = True) -> List[Dict]:
        """Get all tracked markets"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if active_only:
                cursor.execute("SELECT * FROM tracked_markets WHERE active = 1")
            else:
                cursor.execute("SELECT * FROM tracked_markets")

            columns = [d[0] for d in cursor.description]
            markets = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.close()
            return markets

        except Exception as e:
            logger.error(f"Error fetching tracked markets: {e}")
            return []

    def is_tracked_market(self, market_id: str) -> bool:
        """Check if market is being tracked"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM tracked_markets WHERE market_id = ? AND active = 1",
                (market_id,)
            )
            result = cursor.fetchone() is not None
            conn.close()
            return result
        except:
            return False

    def calculate_risk_score(self, trade_data: Dict, wallet_age: Optional[int]) -> Tuple[int, str]:
        """
        Calculate risk score for a trade based on multiple factors

        Returns: (risk_score, risk_level)
        - risk_score: 0-100 integer
        - risk_level: CRITICAL, HIGH, MEDIUM, LOW
        """
        score = 0

        # Factor 1: Wallet Age (max 40 points)
        if wallet_age is not None:
            if wallet_age <= 1:
                score += 40  # Brand new wallet
            elif wallet_age <= 3:
                score += 35
            elif wallet_age <= 7:
                score += 30
            elif wallet_age <= 14:
                score += 20
            elif wallet_age <= 30:
                score += 10

        # Factor 2: Bet Size (max 30 points)
        bet_size = trade_data.get('bet_size', 0)
        if bet_size >= 100000:
            score += 30  # $100k+
        elif bet_size >= 50000:
            score += 25  # $50k+
        elif bet_size >= 25000:
            score += 20  # $25k+
        elif bet_size >= 10000:
            score += 15  # $10k+
        elif bet_size >= 5000:
            score += 10  # $5k+

        # Factor 3: Entry Price/Odds (max 30 points)
        odds = trade_data.get('odds', 1.0)
        odds_cents = odds * 100
        if odds_cents <= 2:
            score += 30  # 2¢ or less - extremely unlikely
        elif odds_cents <= 5:
            score += 25  # 2-5¢
        elif odds_cents <= 10:
            score += 20  # 5-10¢
        elif odds_cents <= 15:
            score += 15  # 10-15¢
        elif odds_cents <= 20:
            score += 10  # 15-20¢

        # Factor 4: Check for rapid trading (velocity)
        # Get recent trades from this wallet
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check trades in last hour
            current_time = datetime.now()
            one_hour_ago = (current_time - timedelta(hours=1)).isoformat()

            cursor.execute("""
                SELECT COUNT(*) FROM suspicious_trades
                WHERE wallet_address = ? AND detected_at > ?
            """, (trade_data['wallet_address'], one_hour_ago))

            recent_count = cursor.fetchone()[0]
            conn.close()

            # Velocity scoring
            if recent_count >= 10:
                score += 20  # 10+ trades in an hour
            elif recent_count >= 5:
                score += 15  # 5-9 trades
            elif recent_count >= 3:
                score += 10  # 3-4 trades

        except Exception as e:
            logger.warning(f"Could not check velocity: {e}")

        # Determine risk level
        if score >= 80:
            risk_level = "CRITICAL"
        elif score >= 60:
            risk_level = "HIGH"
        elif score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return score, risk_level

    def analyze_trade(self, trade: Dict) -> Optional[Dict]:
        """
        Analyze a trade for suspicious patterns
        
        Trade object from Data API has:
        - proxyWallet: user address
        - side: BUY or SELL  
        - size: number of shares
        - price: price per share (0-1)
        - outcome: YES or NO
        - title: market title
        - timestamp: unix timestamp
        - transactionHash: tx hash
        - conditionId: market ID
        """
        try:
            wallet = trade.get('proxyWallet', '').lower()
            if not wallet:
                return None
            
            # Calculate USD value
            size = float(trade.get('size', 0))
            price = float(trade.get('price', 0))
            usd_value = size * price  # This is approximate; actual is size for buys
            
            # For BUY orders, the cost is size * price
            # For market buys at low prices, the USD spent is the number of shares * entry price
            side = trade.get('side', 'BUY')
            
            # Check bet size threshold
            if self.config.check_bet_size and usd_value < self.config.min_bet_size:
                return None
            
            # Check entry price (odds) - flag low-price bets
            if self.config.check_odds and price > self.config.max_odds:
                return None
            
            # Check wallet age
            wallet_age = None
            if self.config.check_wallet_age:
                wallet_age = self.blockchain.get_wallet_age_days(wallet)
                
                # If we can determine age and it's older than threshold, skip
                # Unless it's a tracked wallet
                if wallet_age is not None and wallet_age > self.config.wallet_age_days:
                    if not self.is_tracked_wallet(wallet):
                        return None
            
            # Parse outcome field - Polymarket API may return different formats
            outcome_raw = trade.get('outcome', '')
            outcome = outcome_raw

            # Handle different outcome formats from API
            if isinstance(outcome_raw, str):
                outcome = outcome_raw.upper()  # Normalize to uppercase
            elif isinstance(outcome_raw, (int, float)):
                # Some APIs return 0/1 or token index
                outcome = "YES" if int(outcome_raw) == 0 else "NO"

            # If still empty or invalid, try to infer from other fields
            if not outcome or outcome not in ['YES', 'NO']:
                # Log for debugging
                logger.warning(f"Unknown outcome format: {outcome_raw} for trade {trade.get('transactionHash', 'unknown')[:16]}")
                outcome = "YES"  # Default to YES if unknown

            # Build trade data for risk scoring
            trade_data_for_scoring = {
                "wallet_address": wallet,
                "bet_size": usd_value,
                "odds": price,
                "outcome": outcome,
                "side": side
            }

            # Calculate risk score
            risk_score, risk_level = self.calculate_risk_score(trade_data_for_scoring, wallet_age)

            # Build suspicious trade data
            return {
                "trade_id": trade.get('transactionHash', f"{wallet}_{trade.get('timestamp', '')}"),
                "wallet_address": wallet,
                "market_id": trade.get('conditionId', ''),
                "market_question": trade.get('title', ''),
                "market_category": trade.get('eventSlug', ''),
                "bet_size": usd_value,
                "outcome": outcome,
                "side": side,
                "odds": price,
                "shares": size,
                "timestamp": trade.get('timestamp'),
                "transaction_hash": trade.get('transactionHash'),
                "wallet_age_days": wallet_age,
                "risk_score": risk_score,
                "risk_level": risk_level,
                # Include original trade data for reference
                "proxyWallet": wallet,
                "title": trade.get('title'),
                "price": price,
                "size": size,
                "outcome_raw": str(outcome_raw)  # Store raw value for debugging
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trade: {e}")
            return None
    
    def save_suspicious_trade(self, trade_data: Dict) -> bool:
        """Save suspicious trade to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO suspicious_trades
                (trade_id, wallet_address, market_id, market_question, market_category,
                 bet_size, outcome, side, odds, shares, timestamp, transaction_hash,
                 wallet_age_days, detected_at, risk_score, risk_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data["trade_id"],
                trade_data["wallet_address"],
                trade_data["market_id"],
                trade_data["market_question"],
                trade_data["market_category"],
                trade_data["bet_size"],
                trade_data["outcome"],
                trade_data["side"],
                trade_data["odds"],
                trade_data["shares"],
                trade_data["timestamp"],
                trade_data.get("transaction_hash"),
                trade_data["wallet_age_days"],
                datetime.now().isoformat(),
                trade_data.get("risk_score", 0),
                trade_data.get("risk_level", "LOW")
            ))
            
            # Update wallet analysis
            cursor.execute("""
                INSERT INTO wallet_analysis 
                (wallet_address, first_seen, total_bets, total_volume, suspicious_bets, last_updated)
                VALUES (?, ?, 1, ?, 1, ?)
                ON CONFLICT(wallet_address) DO UPDATE SET
                    total_bets = total_bets + 1,
                    total_volume = total_volume + ?,
                    suspicious_bets = suspicious_bets + 1,
                    last_updated = ?
            """, (
                trade_data["wallet_address"],
                datetime.now().isoformat(),
                trade_data["bet_size"],
                datetime.now().isoformat(),
                trade_data["bet_size"],
                datetime.now().isoformat()
            ))
            
            # Update tracked wallet if applicable
            cursor.execute("""
                UPDATE tracked_wallets 
                SET total_alerts = total_alerts + 1, last_activity = ?
                WHERE wallet_address = ?
            """, (datetime.now().isoformat(), trade_data["wallet_address"]))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            return False
    
    def scan_recent_trades(self, min_amount: float = None) -> Dict:
        """
        Scan recent trades using the Data API
        
        Uses filterType=CASH and filterAmount to get trades above threshold
        """
        logger.info("Starting trade scan...")
        
        stats = {
            "trades_analyzed": 0,
            "suspicious_found": 0,
            "alerts_sent": 0
        }
        
        try:
            # Use the configured minimum or provided override
            filter_amount = min_amount or self.config.min_bet_size
            
            # Fetch trades above the threshold
            trades = self.api.get_trades(
                filter_type="CASH",
                filter_amount=filter_amount,
                limit=500,
                taker_only=True
            )
            
            stats["trades_analyzed"] = len(trades)
            logger.info(f"Fetched {len(trades)} trades above ${filter_amount:,.0f}")
            
            for trade in trades:
                suspicious_data = self.analyze_trade(trade)
                
                if suspicious_data:
                    stats["suspicious_found"] += 1
                    logger.warning(f"Suspicious: {suspicious_data['wallet_address'][:16]}... ${suspicious_data['bet_size']:,.0f}")
                    
                    if self.save_suspicious_trade(suspicious_data):
                        results = self.alert_manager.send_alert(suspicious_data)
                        if any(results.values()):
                            stats["alerts_sent"] += 1
                            
                            # Update alert status
                            try:
                                conn = sqlite3.connect(self.db_path)
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE suspicious_trades 
                                    SET alerted = 1, alert_channels = ?
                                    WHERE trade_id = ?
                                """, (
                                    ",".join(k for k, v in results.items() if v),
                                    suspicious_data["trade_id"]
                                ))
                                conn.commit()
                                conn.close()
                            except:
                                pass
            
            # Log scan
            self._log_scan(stats)
            
            logger.info(f"Scan complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return stats
    
    def scan_tracked_wallets(self) -> Dict:
        """Scan activity for all tracked wallets"""
        logger.info("Scanning tracked wallets...")
        
        stats = {
            "wallets_checked": 0,
            "trades_found": 0,
            "suspicious_found": 0
        }
        
        tracked = self.get_tracked_wallets()
        
        for wallet_info in tracked:
            wallet = wallet_info['wallet_address']
            stats["wallets_checked"] += 1
            
            try:
                # Get recent activity for this wallet
                activity = self.api.get_user_activity(
                    user=wallet,
                    activity_type=["TRADE"],
                    limit=50
                )
                
                stats["trades_found"] += len(activity)
                
                for trade in activity:
                    # Add proxyWallet if not present
                    if 'proxyWallet' not in trade:
                        trade['proxyWallet'] = wallet
                    
                    suspicious_data = self.analyze_trade(trade)
                    
                    if suspicious_data:
                        stats["suspicious_found"] += 1
                        self.save_suspicious_trade(suspicious_data)
                        self.alert_manager.send_alert(suspicious_data)
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error scanning wallet {wallet[:16]}: {e}")
                continue
        
        logger.info(f"Tracked wallet scan complete: {stats}")
        return stats
    
    def scan_markets(self, categories: List[str] = None) -> Dict:
        """
        Full scan: fetch markets, then get trades for each
        This is slower but more comprehensive
        """
        logger.info("Starting full market scan...")
        
        stats = {
            "markets_scanned": 0,
            "trades_analyzed": 0,
            "suspicious_found": 0,
            "alerts_sent": 0
        }
        
        try:
            # Get active events
            events = self.api.get_events(active=True, limit=100)
            
            for event in events:
                markets = event.get("markets", [])

                # Tags can be strings or dicts - handle both cases
                raw_tags = event.get("tags", [])
                tags = []
                for t in raw_tags:
                    if isinstance(t, str):
                        tags.append(t.lower())
                    elif isinstance(t, dict):
                        # If tag is a dict, try to get the 'label' or 'name' field
                        tag_str = t.get('label') or t.get('name') or t.get('slug') or ''
                        if tag_str:
                            tags.append(tag_str.lower())

                # Filter by categories if specified
                if categories:
                    if not any(cat.lower() in tags for cat in categories):
                        continue
                
                for market in markets:
                    condition_id = market.get("conditionId") or market.get("id")
                    if not condition_id:
                        continue
                    
                    stats["markets_scanned"] += 1
                    
                    # Get trades for this market
                    trades = self.api.get_trades(
                        market=condition_id,
                        filter_type="CASH",
                        filter_amount=self.config.min_bet_size,
                        limit=100
                    )
                    
                    stats["trades_analyzed"] += len(trades)
                    
                    for trade in trades:
                        suspicious_data = self.analyze_trade(trade)
                        
                        if suspicious_data:
                            stats["suspicious_found"] += 1
                            
                            if self.save_suspicious_trade(suspicious_data):
                                results = self.alert_manager.send_alert(suspicious_data)
                                if any(results.values()):
                                    stats["alerts_sent"] += 1
                    
                    time.sleep(1)  # Rate limiting
            
            self._log_scan(stats)
            logger.info(f"Full scan complete: {stats}")
            return stats
            
        except Exception as e:
            import traceback
            logger.error(f"Full scan error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return stats
    
    def _log_scan(self, stats: Dict):
        """Log scan to history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO scan_history 
                (started_at, completed_at, markets_scanned, trades_analyzed, 
                 suspicious_found, status)
                VALUES (?, ?, ?, ?, ?, 'completed')
            """, (
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                stats.get("markets_scanned", 0),
                stats.get("trades_analyzed", 0),
                stats.get("suspicious_found", 0)
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging scan: {e}")
    
    def get_suspicious_trades(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get suspicious trades from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM suspicious_trades 
                ORDER BY detected_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            columns = [d[0] for d in cursor.description]
            trades = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.close()
            return trades
            
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    def get_wallet_stats(self, wallet_address: str) -> Optional[Dict]:
        """Get stats for a wallet"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM wallet_analysis WHERE wallet_address = ?",
                (wallet_address.lower(),)
            )
            row = cursor.fetchone()
            
            if row:
                columns = [d[0] for d in cursor.description]
                stats = dict(zip(columns, row))
                
                # Get trades
                cursor.execute("""
                    SELECT * FROM suspicious_trades 
                    WHERE wallet_address = ?
                    ORDER BY timestamp DESC
                """, (wallet_address.lower(),))
                
                trade_cols = [d[0] for d in cursor.description]
                stats["trades"] = [dict(zip(trade_cols, r)) for r in cursor.fetchall()]
                
                # Check if tracked
                cursor.execute(
                    "SELECT * FROM tracked_wallets WHERE wallet_address = ?",
                    (wallet_address.lower(),)
                )
                tracked = cursor.fetchone()
                stats["is_tracked"] = tracked is not None
                
                conn.close()
                return stats
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error fetching wallet stats: {e}")
            return None
    
    def get_dashboard_stats(self) -> Dict:
        """Get aggregate stats for dashboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM suspicious_trades")
            stats["total_suspicious"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT wallet_address) FROM suspicious_trades")
            stats["unique_wallets"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COALESCE(SUM(bet_size), 0) FROM suspicious_trades")
            stats["total_volume"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM suspicious_trades WHERE alerted = 1")
            stats["alerts_sent"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tracked_wallets WHERE active = 1")
            stats["tracked_wallets"] = cursor.fetchone()[0]
            
            today = datetime.now().date().isoformat()
            cursor.execute(
                "SELECT COUNT(*) FROM suspicious_trades WHERE DATE(detected_at) = ?",
                (today,)
            )
            stats["today_suspicious"] = cursor.fetchone()[0]
            
            # Weekly trend
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("""
                SELECT DATE(detected_at) as date, COUNT(*) as count
                FROM suspicious_trades 
                WHERE detected_at >= ?
                GROUP BY DATE(detected_at)
                ORDER BY date
            """, (week_ago,))
            stats["weekly_trend"] = [
                {"date": row[0], "count": row[1]} 
                for row in cursor.fetchall()
            ]
            
            # Top wallets
            cursor.execute("""
                SELECT wallet_address, COUNT(*) as count, SUM(bet_size) as volume
                FROM suspicious_trades
                GROUP BY wallet_address
                ORDER BY count DESC
                LIMIT 10
            """)
            stats["top_wallets"] = [
                {"wallet": row[0], "count": row[1], "volume": row[2]}
                for row in cursor.fetchall()
            ]
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return {}
    
    def run_continuous(self, interval_minutes: int = 5):
        """Run continuous monitoring"""
        logger.info(f"Starting continuous monitoring (interval: {interval_minutes} min)")
        
        while True:
            try:
                # Quick scan of recent large trades
                self.scan_recent_trades()
                
                # Scan tracked wallets
                self.scan_tracked_wallets()
                
                logger.info(f"Sleeping {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Stopped by user")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)


if __name__ == "__main__":
    # Example usage
    config = DetectionConfig(
        wallet_age_days=14,
        min_bet_size=10000,
        max_odds=0.10
    )
    
    monitor = PolymarketMonitor(config=config)
    
    # Quick scan of recent trades
    monitor.scan_recent_trades()
