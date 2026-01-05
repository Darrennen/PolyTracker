"""
PolyTracker - Polymarket Suspicious Activity Monitor
Detects suspicious betting patterns on Polymarket prediction markets.
"""

import requests
import time
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database layer
from database import Database


class PolygonRPC:
    """Helper class to get wallet age from Polygonscan"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("POLYGONSCAN_API_KEY")
        self.base_url = "https://api.polygonscan.com/api"

    def get_wallet_age_days(self, wallet_address: str) -> Optional[int]:
        """Get the age of a wallet in days using Polygonscan API"""
        if not self.api_key:
            logger.warning("No Polygonscan API key - wallet age detection disabled")
            return None

        try:
            params = {
                "module": "account",
                "action": "txlist",
                "address": wallet_address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 1,  # Only need first transaction
                "sort": "asc",
                "apikey": self.api_key
            }

            response = requests.get(self.base_url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "1" and data.get("result"):
                    first_tx = data["result"][0]
                    first_tx_time = int(first_tx.get("timeStamp", 0))
                    if first_tx_time > 0:
                        wallet_created = datetime.fromtimestamp(first_tx_time)
                        age_days = (datetime.now() - wallet_created).days
                        return age_days

            return None

        except Exception as e:
            logger.error(f"Error getting wallet age: {e}")
            return None


class NotificationManager:
    """Handles sending alerts via Telegram and Slack"""

    def __init__(self, telegram_token: str = None, telegram_chat_id: str = None,
                 slack_webhook_url: str = None):
        self.telegram_token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    def send_telegram(self, data: Dict) -> bool:
        """Send alert via Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            return False

        try:
            message = f"""
🚨 *SUSPICIOUS ACTIVITY DETECTED* 🚨

*Market:* {data['market_question'][:100]}
*Category:* {data['market_category']}

*Wallet:* `{data['wallet_address']}`
*Wallet Age:* {data.get('wallet_age_days') or 'Unknown'} days

*Bet Details:*
• Size: ${data['bet_size']:,.2f}
• Outcome: {data['outcome']}
• Odds: {data['odds']*100:.1f}%

[View on Polygonscan](https://polygonscan.com/address/{data['wallet_address']})
            """

            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Telegram alert sent for trade {data.get('trade_id')}")
                return True
            else:
                logger.error(f"Telegram error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False

    def send_slack(self, data: Dict) -> bool:
        """Send alert via Slack webhook"""
        if not self.slack_webhook_url:
            return False

        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Suspicious Activity Detected",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Market:*\n{data['market_question'][:50]}..."},
                        {"type": "mrkdwn", "text": f"*Category:*\n{data['market_category']}"},
                        {"type": "mrkdwn", "text": f"*Wallet:*\n`{data['wallet_address'][:10]}...`"},
                        {"type": "mrkdwn", "text": f"*Wallet Age:*\n{data.get('wallet_age_days') or 'Unknown'} days"},
                        {"type": "mrkdwn", "text": f"*Bet Size:*\n${data['bet_size']:,.2f}"},
                        {"type": "mrkdwn", "text": f"*Position:*\n{data['outcome']} @ {data['odds']*100:.1f}%"}
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View on Polygonscan"},
                            "url": f"https://polygonscan.com/address/{data['wallet_address']}"
                        }
                    ]
                }
            ]

            payload = {"blocks": blocks}
            response = requests.post(self.slack_webhook_url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"Slack alert sent for trade {data.get('trade_id')}")
                return True
            else:
                logger.error(f"Slack error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
            return False

    def send_alert(self, data: Dict) -> Dict[str, bool]:
        """Send alerts to all configured channels"""
        results = {}
        results["telegram"] = self.send_telegram(data)
        results["slack"] = self.send_slack(data)
        return results


class PolymarketMonitor:
    """Main monitoring class for Polymarket suspicious activity"""

    BASE_URL = "https://clob.polymarket.com"
    GAMMA_URL = "https://gamma-api.polymarket.com"

    # Default detection thresholds (can be overridden)
    WALLET_AGE_DAYS = int(os.getenv("WALLET_AGE_DAYS", 30))
    MIN_BET_SIZE = float(os.getenv("MIN_BET_SIZE", 10000))
    MAX_ODDS = float(os.getenv("MAX_ODDS", 0.20))

    # Categories to monitor
    DEFAULT_CATEGORIES = ["news", "crypto", "cryptocurrency", "politics", "sports"]

    def __init__(self, db_path: str = "polymarket_monitor.db",
                 telegram_token: str = None, telegram_chat_id: str = None,
                 slack_webhook_url: str = None, api_key: str = None,
                 categories: List[str] = None):

        # Database
        self.db = Database(db_path)

        # API configuration
        self.api_key = api_key or os.getenv("POLYMARKET_API_KEY")
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info("API key configured - using authenticated requests")

        # Wallet age checker
        self.polygon_rpc = PolygonRPC()

        # Notifications
        self.notifications = NotificationManager(
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
            slack_webhook_url=slack_webhook_url
        )

        # Categories to monitor
        self.categories = categories or self.DEFAULT_CATEGORIES

        logger.info(f"Monitor initialized - Thresholds: age<{self.WALLET_AGE_DAYS}d, "
                    f"bet>${self.MIN_BET_SIZE:,}, odds<{self.MAX_ODDS*100}%")

    def get_markets(self, active_only: bool = True) -> List[Dict]:
        """Fetch markets from Polymarket"""
        try:
            url = f"{self.GAMMA_URL}/events"
            params = {"active": "true"} if active_only else {}

            response = self._make_request("GET", url, params=params)

            if response and response.status_code == 200:
                data = response.json()
                markets = []

                for event in data:
                    markets_list = event.get("markets", [])
                    for market in markets_list:
                        tags = [tag.lower() for tag in event.get("tags", [])]
                        if any(cat in tags for cat in self.categories):
                            market_data = {
                                "market_id": market.get("id"),
                                "question": market.get("question"),
                                "category": ", ".join(event.get("tags", [])),
                                "active": market.get("active", True)
                            }
                            markets.append(market_data)
                            self.db.cache_market(market_data)

                logger.info(f"Fetched {len(markets)} markets in monitored categories")
                return markets

            return []

        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []

    def get_trades(self, market_id: str) -> List[Dict]:
        """Fetch recent trades for a specific market"""
        try:
            url = f"{self.BASE_URL}/trades"
            params = {"market": market_id}

            response = self._make_request("GET", url, params=params)

            if response and response.status_code == 200:
                return response.json()

            return []

        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []

    def get_market_prices(self, market_id: str) -> Dict:
        """Get current market prices/odds"""
        try:
            url = f"{self.GAMMA_URL}/markets/{market_id}"

            response = self._make_request("GET", url)

            if response and response.status_code == 200:
                data = response.json()
                tokens = data.get("tokens", [])
                prices = {}

                for token in tokens:
                    outcome = token.get("outcome")
                    price = float(token.get("price", 0))
                    prices[outcome] = price

                return prices

            return {}

        except Exception as e:
            logger.error(f"Error fetching market prices: {e}")
            return {}

    def _make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retry logic"""
        max_retries = 3
        backoff = 2

        for attempt in range(max_retries):
            try:
                kwargs.setdefault("headers", self.headers)
                kwargs.setdefault("timeout", 30)

                if method == "GET":
                    response = requests.get(url, **kwargs)
                else:
                    response = requests.post(url, **kwargs)

                if response.status_code == 429:  # Rate limited
                    wait_time = backoff ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                return response

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff ** attempt)

        return None

    def analyze_trade(self, trade: Dict, market_data: Dict, current_odds: Dict) -> Optional[Dict]:
        """Analyze a trade for suspicious patterns"""
        try:
            wallet_address = trade.get("maker_address") or trade.get("taker_address")
            if not wallet_address:
                return None

            trade_id = trade.get("id")

            # Skip if already processed
            if self.db.trade_exists(trade_id):
                return None

            # Get trade details
            size = float(trade.get("size", 0))
            price = float(trade.get("price", 0))
            bet_value = size * price
            outcome = trade.get("outcome")

            # Check if wallet is monitored (bypass thresholds)
            is_monitored = self.db.is_wallet_monitored(wallet_address)

            if not is_monitored:
                # Apply normal threshold checks
                if bet_value < self.MIN_BET_SIZE:
                    return None

                odds = current_odds.get(outcome, 1.0)
                if odds > self.MAX_ODDS:
                    return None
            else:
                odds = current_odds.get(outcome, 1.0)

            # Get wallet age
            wallet_age = self.polygon_rpc.get_wallet_age_days(wallet_address)

            # Determine if suspicious
            is_suspicious = False
            detection_source = "automatic"

            if is_monitored:
                is_suspicious = True
                detection_source = "monitored_wallet"
            elif wallet_age is None or wallet_age < self.WALLET_AGE_DAYS:
                is_suspicious = True
                detection_source = "automatic"

            if is_suspicious:
                return {
                    "trade_id": trade_id,
                    "wallet_address": wallet_address,
                    "market_id": market_data["market_id"],
                    "market_question": market_data["question"],
                    "market_category": market_data["category"],
                    "bet_size": bet_value,
                    "outcome": outcome,
                    "odds": odds,
                    "timestamp": trade.get("timestamp"),
                    "wallet_age_days": wallet_age,
                    "detection_source": detection_source
                }

            return None

        except Exception as e:
            logger.error(f"Error analyzing trade: {e}")
            return None

    def scan_markets(self) -> int:
        """Main scanning function. Returns number of suspicious trades found."""
        logger.info("Starting market scan...")
        suspicious_count = 0

        markets = self.get_markets()

        for market in markets:
            try:
                market_id = market["market_id"]
                logger.debug(f"Scanning market: {market['question'][:50]}...")

                # Get current odds
                current_odds = self.get_market_prices(market_id)
                if not current_odds:
                    continue

                # Get recent trades
                trades = self.get_trades(market_id)

                for trade in trades:
                    suspicious_data = self.analyze_trade(trade, market, current_odds)

                    if suspicious_data:
                        logger.warning(f"Suspicious trade: ${suspicious_data['bet_size']:,.0f} "
                                       f"on {suspicious_data['outcome']} @ {suspicious_data['odds']*100:.1f}%")

                        # Save to database
                        if self.db.save_suspicious_trade(suspicious_data):
                            suspicious_count += 1

                            # Send alerts
                            results = self.notifications.send_alert(suspicious_data)

                            # Mark as alerted if any notification succeeded
                            if any(results.values()):
                                self.db.mark_trade_alerted(
                                    suspicious_data["trade_id"],
                                    ", ".join(k for k, v in results.items() if v)
                                )

                # Rate limiting
                time.sleep(2)

            except Exception as e:
                logger.error(f"Error scanning market {market.get('market_id')}: {e}")
                continue

        logger.info(f"Scan completed. Found {suspicious_count} suspicious trades.")
        return suspicious_count

    def run_continuous(self, interval_minutes: int = 5):
        """Run continuous monitoring"""
        logger.info(f"Starting continuous monitoring (interval: {interval_minutes} minutes)")

        while True:
            try:
                self.scan_markets()
                logger.info(f"Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)

            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

    # =========================================================================
    # Helper methods for external access
    # =========================================================================

    def get_suspicious_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent suspicious trades from database"""
        return self.db.get_suspicious_trades(limit)

    def get_wallet_stats(self, wallet_address: str) -> Optional[Dict]:
        """Get statistics for a specific wallet"""
        return self.db.get_wallet_stats(wallet_address)

    def add_monitored_wallet(self, wallet_address: str, label: str = None,
                             notes: str = None) -> bool:
        """Add a wallet to monitoring list"""
        return self.db.add_monitored_wallet(wallet_address, label, notes)

    def remove_monitored_wallet(self, wallet_address: str) -> bool:
        """Remove a wallet from monitoring list"""
        return self.db.remove_monitored_wallet(wallet_address)

    def get_monitored_wallets(self) -> List[Dict]:
        """Get list of monitored wallets"""
        return self.db.get_monitored_wallets()


if __name__ == "__main__":
    # Example usage
    monitor = PolymarketMonitor()

    # Run a single scan
    monitor.scan_markets()

    # Or run continuous monitoring
    # monitor.run_continuous(interval_minutes=5)
