import requests
import sqlite3
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PolygonRPC:
    """Helper class to interact with Polygon blockchain"""
    
    def __init__(self, rpc_url: str = "https://polygon-rpc.com"):
        self.rpc_url = rpc_url
    
    def get_wallet_age_days(self, wallet_address: str) -> Optional[int]:
        """Get the age of a wallet in days"""
        try:
            # Get the first transaction of the wallet
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionCount",
                "params": [wallet_address, "earliest"],
                "id": 1
            }
            
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                # For simplicity, we'll use block number as proxy
                # In production, you'd want to get actual block timestamp
                current_time = datetime.now()
                
                # Get latest block to calculate approximate age
                # This is simplified - you'd want to fetch actual first tx timestamp
                latest_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 2
                }
                latest_response = requests.post(self.rpc_url, json=latest_payload, timeout=10)
                
                if latest_response.status_code == 200:
                    # Simplified calculation - assumes ~2 seconds per block on Polygon
                    # You should improve this with actual timestamp queries
                    return None  # Placeholder for actual implementation
                
            return None
        except Exception as e:
            logger.error(f"Error getting wallet age: {e}")
            return None


class PolymarketMonitor:
    """Main monitoring class for Polymarket suspicious activity"""
    
    BASE_URL = "https://clob.polymarket.com"
    GAMMA_URL = "https://gamma-api.polymarket.com"
    
    # Detection thresholds
    WALLET_AGE_DAYS = 30  # Less than 30 days
    MIN_BET_SIZE = 10000  # More than $10k
    MAX_ODDS = 0.20  # Less than 20% probability
    
    def __init__(self, db_path: str = "polymarket_monitor.db", telegram_token: str = None, telegram_chat_id: str = None, api_key: str = None):
        self.db_path = db_path
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.api_key = api_key
        self.polygon_rpc = PolygonRPC()
        self.init_database()
        
        # Setup API headers
        self.headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info("API key configured - using authenticated requests")
    
    def test_connection(self) -> Dict:
        """Test API connectivity and return diagnostics"""
        results = {
            "gamma_api": False,
            "clob_api": False,
            "error": None,
            "details": []
        }
        
        try:
            # Test Gamma API - events endpoint
            url = f"{self.GAMMA_URL}/events"
            params = {"active": "true", "closed": "false", "limit": 1}
            
            response = requests.get(url, params=params, timeout=10)
            results["gamma_api"] = response.status_code == 200
            results["gamma_status"] = response.status_code
            
            if response.status_code == 200:
                data = response.json()
                results["details"].append(f"Gamma API: Found {len(data)} events")
            else:
                results["error"] = f"Gamma API returned {response.status_code}: {response.text[:200]}"
            
            # Test CLOB API - use a sample token ID if available
            if response.status_code == 200 and len(data) > 0:
                # Try to get first market's token ID
                first_event = data[0]
                first_market = first_event.get("markets", [{}])[0]
                token_ids = first_market.get("clobTokenIds", [])
                
                if token_ids:
                    url2 = f"{self.BASE_URL}/price"
                    params2 = {"token_id": token_ids[0], "side": "buy"}
                    response2 = requests.get(url2, params=params2, timeout=10)
                    results["clob_api"] = response2.status_code == 200
                    results["clob_status"] = response2.status_code
                    
                    if response2.status_code == 200:
                        price_data = response2.json()
                        results["details"].append(f"CLOB API: Price fetch successful ({price_data.get('price', 'N/A')})")
                else:
                    results["details"].append("CLOB API: No token IDs to test")
            
        except Exception as e:
            results["error"] = str(e)
            logger.error(f"Connection test failed: {e}")
        
        return results
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
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
                odds REAL,
                timestamp TEXT,
                wallet_age_days INTEGER,
                detected_at TEXT,
                alerted INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS markets_cache (
                market_id TEXT PRIMARY KEY,
                question TEXT,
                category TEXT,
                active INTEGER,
                cached_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_analysis (
                wallet_address TEXT PRIMARY KEY,
                first_seen TEXT,
                total_bets INTEGER,
                total_volume REAL,
                suspicious_bets INTEGER,
                last_updated TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def get_markets(self, active_only: bool = True) -> List[Dict]:
        """Fetch markets from Polymarket using official API"""
        try:
            # Use the correct endpoint with proper parameters
            url = f"{self.GAMMA_URL}/events"
            params = {
                "active": "true" if active_only else "false",
                "closed": "false",  # Only get open markets
                "limit": 100  # Get more markets per request
            }
            
            logger.info(f"Fetching markets from {url} with params {params}")
            response = requests.get(url, params=params, timeout=30)
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                events = response.json()
                markets = []
                
                # Process events and extract markets
                for event in events:
                    # Get tags for filtering
                    tags = event.get("tags", [])
                    tag_labels = [tag.get("label", "").lower() for tag in tags]
                    
                    # Filter for News and Crypto categories
                    if any(cat in tag_labels for cat in ["news", "crypto", "cryptocurrency", "politics"]):
                        # Each event can have multiple markets
                        event_markets = event.get("markets", [])
                        
                        for market in event_markets:
                            market_data = {
                                "market_id": market.get("id"),
                                "question": market.get("question"),
                                "category": ", ".join([tag.get("label", "") for tag in tags]),
                                "active": market.get("active", True),
                                "clob_token_ids": market.get("clobTokenIds", [])
                            }
                            markets.append(market_data)
                            self.cache_market(market_data)
                
                logger.info(f"Fetched {len(markets)} markets in News/Crypto categories from {len(events)} events")
                return markets
            else:
                logger.error(f"Failed to fetch markets: {response.status_code} - {response.text[:500]}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching markets: {e}", exc_info=True)
            return []
    
    def cache_market(self, market_data: Dict):
        """Cache market data in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO markets_cache (market_id, question, category, active, cached_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                market_data["market_id"],
                market_data["question"],
                market_data["category"],
                1 if market_data["active"] else 0,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error caching market: {e}")
    
    def get_trades(self, market_id: str) -> List[Dict]:
        """Fetch recent trades for a specific market"""
        try:
            url = f"{self.BASE_URL}/trades"
            params = {"market": market_id}
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                trades = response.json()
                return trades
            else:
                logger.warning(f"Failed to fetch trades for market {market_id}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    def get_market_prices(self, market_id: str, clob_token_ids: List[str] = None) -> Dict:
        """Get current market prices/odds using CLOB API"""
        try:
            prices = {}
            
            # If we have clob token IDs, use them to get prices
            if clob_token_ids and len(clob_token_ids) >= 2:
                # Get price for YES token (index 0)
                url_yes = f"{self.BASE_URL}/price"
                params_yes = {
                    "token_id": clob_token_ids[0],
                    "side": "buy"
                }
                
                response_yes = requests.get(url_yes, params=params_yes, timeout=10)
                if response_yes.status_code == 200:
                    data_yes = response_yes.json()
                    prices["YES"] = float(data_yes.get("price", 0))
                
                # Get price for NO token (index 1)
                url_no = f"{self.BASE_URL}/price"
                params_no = {
                    "token_id": clob_token_ids[1],
                    "side": "buy"
                }
                
                response_no = requests.get(url_no, params=params_no, timeout=10)
                if response_no.status_code == 200:
                    data_no = response_no.json()
                    prices["NO"] = float(data_no.get("price", 0))
                
                logger.info(f"Fetched prices for market {market_id}: {prices}")
            else:
                # Fallback: try to get from Gamma API
                url = f"{self.GAMMA_URL}/markets/{market_id}"
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    # Parse outcome prices
                    outcomes_str = data.get("outcomes", "[]")
                    prices_str = data.get("outcomePrices", "[]")
                    
                    try:
                        import json
                        outcomes = json.loads(outcomes_str)
                        outcome_prices = json.loads(prices_str)
                        
                        # Map outcomes to prices
                        for i, outcome in enumerate(outcomes):
                            if i < len(outcome_prices):
                                prices[outcome] = float(outcome_prices[i])
                    except:
                        pass
            
            return prices
                
        except Exception as e:
            logger.error(f"Error fetching market prices: {e}")
            return {}
    
    def analyze_trade(self, trade: Dict, market_data: Dict, current_odds: Dict) -> Optional[Dict]:
        """Analyze a trade for suspicious patterns"""
        try:
            wallet_address = trade.get("maker_address") or trade.get("taker_address")
            if not wallet_address:
                return None
            
            # Get trade details
            size = float(trade.get("size", 0))
            price = float(trade.get("price", 0))
            bet_value = size * price
            
            outcome = trade.get("outcome")
            
            # Check if bet size meets threshold
            if bet_value < self.MIN_BET_SIZE:
                return None
            
            # Check if odds meet threshold (betting on unlikely outcome)
            odds = current_odds.get(outcome, 1.0)
            if odds > self.MAX_ODDS:
                return None
            
            # TODO: Get actual wallet age from blockchain
            # For now, we'll mark it as suspicious if we can't determine age
            wallet_age = self.polygon_rpc.get_wallet_age_days(wallet_address)
            
            # If we can't determine age or it's within threshold, flag it
            if wallet_age is None or wallet_age < self.WALLET_AGE_DAYS:
                suspicious_data = {
                    "trade_id": trade.get("id"),
                    "wallet_address": wallet_address,
                    "market_id": market_data["market_id"],
                    "market_question": market_data["question"],
                    "market_category": market_data["category"],
                    "bet_size": bet_value,
                    "outcome": outcome,
                    "odds": odds,
                    "timestamp": trade.get("timestamp"),
                    "wallet_age_days": wallet_age
                }
                
                return suspicious_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing trade: {e}")
            return None
    
    def save_suspicious_trade(self, suspicious_data: Dict):
        """Save suspicious trade to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO suspicious_trades 
                (trade_id, wallet_address, market_id, market_question, market_category,
                 bet_size, outcome, odds, timestamp, wallet_age_days, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                suspicious_data["trade_id"],
                suspicious_data["wallet_address"],
                suspicious_data["market_id"],
                suspicious_data["market_question"],
                suspicious_data["market_category"],
                suspicious_data["bet_size"],
                suspicious_data["outcome"],
                suspicious_data["odds"],
                suspicious_data["timestamp"],
                suspicious_data["wallet_age_days"],
                datetime.now().isoformat()
            ))
            
            # Update wallet analysis
            cursor.execute("""
                INSERT INTO wallet_analysis (wallet_address, first_seen, total_bets, total_volume, suspicious_bets, last_updated)
                VALUES (?, ?, 1, ?, 1, ?)
                ON CONFLICT(wallet_address) DO UPDATE SET
                    total_bets = total_bets + 1,
                    total_volume = total_volume + ?,
                    suspicious_bets = suspicious_bets + 1,
                    last_updated = ?
            """, (
                suspicious_data["wallet_address"],
                datetime.now().isoformat(),
                suspicious_data["bet_size"],
                datetime.now().isoformat(),
                suspicious_data["bet_size"],
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Saved suspicious trade: {suspicious_data['trade_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving suspicious trade: {e}")
            return False
    
    def send_telegram_alert(self, suspicious_data: Dict):
        """Send alert via Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        
        try:
            message = f"""
🚨 *SUSPICIOUS ACTIVITY DETECTED* 🚨

*Market:* {suspicious_data['market_question']}
*Category:* {suspicious_data['market_category']}

*Wallet:* `{suspicious_data['wallet_address']}`
*Wallet Age:* {suspicious_data['wallet_age_days'] or 'Unknown'} days

*Bet Details:*
• Size: ${suspicious_data['bet_size']:,.2f}
• Outcome: {suspicious_data['outcome']}
• Odds: {suspicious_data['odds']*100:.1f}%

*Time:* {suspicious_data['timestamp']}

[View on Polygonscan](https://polygonscan.com/address/{suspicious_data['wallet_address']})
            """
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                # Mark as alerted in database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE suspicious_trades SET alerted = 1 WHERE trade_id = ?",
                    (suspicious_data["trade_id"],)
                )
                conn.commit()
                conn.close()
                
                logger.info(f"Telegram alert sent for trade {suspicious_data['trade_id']}")
                return True
            else:
                logger.error(f"Failed to send Telegram alert: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    def scan_markets(self):
        """Main scanning function"""
        logger.info("Starting market scan...")
        
        markets = self.get_markets()
        
        for market in markets:
            try:
                market_id = market["market_id"]
                clob_token_ids = market.get("clob_token_ids", [])
                logger.info(f"Scanning market: {market['question']}")
                
                # Get current odds
                current_odds = self.get_market_prices(market_id, clob_token_ids)
                
                # Get recent trades
                trades = self.get_trades(market_id)
                
                for trade in trades:
                    suspicious_data = self.analyze_trade(trade, market, current_odds)
                    
                    if suspicious_data:
                        logger.warning(f"Suspicious trade detected: {suspicious_data}")
                        
                        # Save to database
                        if self.save_suspicious_trade(suspicious_data):
                            # Send alert if Telegram is configured
                            self.send_telegram_alert(suspicious_data)
                
                # Rate limiting - be nice to the API
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scanning market {market['market_id']}: {e}")
                continue
        
        logger.info("Market scan completed")
    
    def get_suspicious_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent suspicious trades from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM suspicious_trades 
                ORDER BY detected_at DESC 
                LIMIT ?
            """, (limit,))
            
            columns = [description[0] for description in cursor.description]
            trades = []
            
            for row in cursor.fetchall():
                trades.append(dict(zip(columns, row)))
            
            conn.close()
            return trades
            
        except Exception as e:
            logger.error(f"Error fetching suspicious trades: {e}")
            return []
    
    def get_wallet_stats(self, wallet_address: str) -> Optional[Dict]:
        """Get statistics for a specific wallet"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM wallet_analysis 
                WHERE wallet_address = ?
            """, (wallet_address,))
            
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                stats = dict(zip(columns, row))
                
                # Get all trades for this wallet
                cursor.execute("""
                    SELECT * FROM suspicious_trades 
                    WHERE wallet_address = ?
                    ORDER BY timestamp DESC
                """, (wallet_address,))
                
                trade_columns = [description[0] for description in cursor.description]
                trades = []
                for trade_row in cursor.fetchall():
                    trades.append(dict(zip(trade_columns, trade_row)))
                
                stats["trades"] = trades
                conn.close()
                return stats
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error fetching wallet stats: {e}")
            return None
    
    def run_continuous(self, interval_minutes: int = 10):
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


if __name__ == "__main__":
    # Example usage
    monitor = PolymarketMonitor()
    
    # Run a single scan
    monitor.scan_markets()
    
    # Or run continuous monitoring
    # monitor.run_continuous(interval_minutes=10)
