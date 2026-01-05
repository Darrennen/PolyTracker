"""
Database abstraction layer for PolyTracker
Supports both SQLite (local) and PostgreSQL (cloud)
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Check if we're using PostgreSQL or SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # PostgreSQL (Railway/Cloud)
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_TYPE = "postgresql"
    logger.info("Using PostgreSQL database")
else:
    # SQLite (Local)
    import sqlite3
    DB_TYPE = "sqlite"
    logger.info("Using SQLite database")


class Database:
    """Database wrapper that works with both SQLite and PostgreSQL"""

    def __init__(self, db_path: str = "polymarket_monitor.db"):
        self.db_path = db_path
        self.database_url = DATABASE_URL
        self.db_type = DB_TYPE
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup"""
        conn = None
        try:
            if self.db_type == "postgresql":
                conn = psycopg2.connect(self.database_url)
            else:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_cursor(self, commit: bool = False):
        """Get database cursor with proper cleanup"""
        with self.get_connection() as conn:
            if self.db_type == "postgresql":
                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

    def init_database(self):
        """Initialize database tables"""
        # Use appropriate syntax for each database
        if self.db_type == "postgresql":
            auto_increment = "SERIAL PRIMARY KEY"
            text_type = "TEXT"
        else:
            auto_increment = "INTEGER PRIMARY KEY AUTOINCREMENT"
            text_type = "TEXT"

        queries = [
            # Suspicious trades table
            f"""
            CREATE TABLE IF NOT EXISTS suspicious_trades (
                id {auto_increment},
                trade_id {text_type} UNIQUE,
                wallet_address {text_type},
                market_id {text_type},
                market_question {text_type},
                market_category {text_type},
                bet_size REAL,
                outcome {text_type},
                odds REAL,
                timestamp {text_type},
                wallet_age_days INTEGER,
                detected_at {text_type},
                alerted INTEGER DEFAULT 0,
                detection_source {text_type} DEFAULT 'automatic'
            )
            """,

            # Markets cache table
            f"""
            CREATE TABLE IF NOT EXISTS markets_cache (
                market_id {text_type} PRIMARY KEY,
                question {text_type},
                category {text_type},
                active INTEGER,
                cached_at {text_type}
            )
            """,

            # Wallet analysis table
            f"""
            CREATE TABLE IF NOT EXISTS wallet_analysis (
                wallet_address {text_type} PRIMARY KEY,
                first_seen {text_type},
                total_bets INTEGER,
                total_volume REAL,
                suspicious_bets INTEGER,
                last_updated {text_type}
            )
            """,

            # Monitored wallets table (NEW)
            f"""
            CREATE TABLE IF NOT EXISTS monitored_wallets (
                id {auto_increment},
                wallet_address {text_type} UNIQUE NOT NULL,
                label {text_type},
                notes {text_type},
                added_at {text_type} NOT NULL,
                is_active INTEGER DEFAULT 1,
                bypass_thresholds INTEGER DEFAULT 1,
                last_activity {text_type},
                total_trades_tracked INTEGER DEFAULT 0
            )
            """,

            # Alert history table (NEW)
            f"""
            CREATE TABLE IF NOT EXISTS alert_history (
                id {auto_increment},
                trade_id {text_type} NOT NULL,
                alert_type {text_type} NOT NULL,
                sent_at {text_type} NOT NULL,
                success INTEGER DEFAULT 1,
                error_message {text_type}
            )
            """
        ]

        # Create indexes
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_suspicious_wallet ON suspicious_trades(wallet_address)",
            "CREATE INDEX IF NOT EXISTS idx_suspicious_detected ON suspicious_trades(detected_at)",
            "CREATE INDEX IF NOT EXISTS idx_suspicious_market ON suspicious_trades(market_id)",
            "CREATE INDEX IF NOT EXISTS idx_monitored_address ON monitored_wallets(wallet_address)",
            "CREATE INDEX IF NOT EXISTS idx_alert_trade ON alert_history(trade_id)"
        ]

        with self.get_cursor(commit=True) as cursor:
            for query in queries:
                try:
                    cursor.execute(query)
                except Exception as e:
                    logger.warning(f"Table may already exist: {e}")

            for query in index_queries:
                try:
                    cursor.execute(query)
                except Exception as e:
                    logger.warning(f"Index may already exist: {e}")

        logger.info("Database initialized successfully")

    # =========================================================================
    # SUSPICIOUS TRADES
    # =========================================================================

    def save_suspicious_trade(self, data: Dict) -> bool:
        """Save a suspicious trade to database"""
        try:
            with self.get_cursor(commit=True) as cursor:
                if self.db_type == "postgresql":
                    cursor.execute("""
                        INSERT INTO suspicious_trades
                        (trade_id, wallet_address, market_id, market_question, market_category,
                         bet_size, outcome, odds, timestamp, wallet_age_days, detected_at, detection_source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (trade_id) DO NOTHING
                    """, (
                        data["trade_id"], data["wallet_address"], data["market_id"],
                        data["market_question"], data["market_category"], data["bet_size"],
                        data["outcome"], data["odds"], data["timestamp"],
                        data.get("wallet_age_days"), datetime.now().isoformat(),
                        data.get("detection_source", "automatic")
                    ))
                else:
                    cursor.execute("""
                        INSERT OR IGNORE INTO suspicious_trades
                        (trade_id, wallet_address, market_id, market_question, market_category,
                         bet_size, outcome, odds, timestamp, wallet_age_days, detected_at, detection_source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data["trade_id"], data["wallet_address"], data["market_id"],
                        data["market_question"], data["market_category"], data["bet_size"],
                        data["outcome"], data["odds"], data["timestamp"],
                        data.get("wallet_age_days"), datetime.now().isoformat(),
                        data.get("detection_source", "automatic")
                    ))

                # Update wallet analysis
                self._update_wallet_analysis(cursor, data)

            return True
        except Exception as e:
            logger.error(f"Error saving suspicious trade: {e}")
            return False

    def _update_wallet_analysis(self, cursor, data: Dict):
        """Update wallet analysis table"""
        now = datetime.now().isoformat()
        wallet = data["wallet_address"]
        bet_size = data["bet_size"]

        if self.db_type == "postgresql":
            cursor.execute("""
                INSERT INTO wallet_analysis (wallet_address, first_seen, total_bets, total_volume, suspicious_bets, last_updated)
                VALUES (%s, %s, 1, %s, 1, %s)
                ON CONFLICT (wallet_address) DO UPDATE SET
                    total_bets = wallet_analysis.total_bets + 1,
                    total_volume = wallet_analysis.total_volume + %s,
                    suspicious_bets = wallet_analysis.suspicious_bets + 1,
                    last_updated = %s
            """, (wallet, now, bet_size, now, bet_size, now))
        else:
            cursor.execute("""
                INSERT INTO wallet_analysis (wallet_address, first_seen, total_bets, total_volume, suspicious_bets, last_updated)
                VALUES (?, ?, 1, ?, 1, ?)
                ON CONFLICT(wallet_address) DO UPDATE SET
                    total_bets = total_bets + 1,
                    total_volume = total_volume + ?,
                    suspicious_bets = suspicious_bets + 1,
                    last_updated = ?
            """, (wallet, now, bet_size, now, bet_size, now))

    def get_suspicious_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent suspicious trades"""
        try:
            with self.get_cursor() as cursor:
                placeholder = "%s" if self.db_type == "postgresql" else "?"
                cursor.execute(f"""
                    SELECT * FROM suspicious_trades
                    ORDER BY detected_at DESC
                    LIMIT {placeholder}
                """, (limit,))

                rows = cursor.fetchall()
                if self.db_type == "postgresql":
                    return [dict(row) for row in rows]
                else:
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching suspicious trades: {e}")
            return []

    def mark_trade_alerted(self, trade_id: str, alert_type: str = "telegram") -> bool:
        """Mark a trade as alerted"""
        try:
            with self.get_cursor(commit=True) as cursor:
                if self.db_type == "postgresql":
                    cursor.execute(
                        "UPDATE suspicious_trades SET alerted = 1 WHERE trade_id = %s",
                        (trade_id,)
                    )
                    cursor.execute("""
                        INSERT INTO alert_history (trade_id, alert_type, sent_at, success)
                        VALUES (%s, %s, %s, 1)
                    """, (trade_id, alert_type, datetime.now().isoformat()))
                else:
                    cursor.execute(
                        "UPDATE suspicious_trades SET alerted = 1 WHERE trade_id = ?",
                        (trade_id,)
                    )
                    cursor.execute("""
                        INSERT INTO alert_history (trade_id, alert_type, sent_at, success)
                        VALUES (?, ?, ?, 1)
                    """, (trade_id, alert_type, datetime.now().isoformat()))
            return True
        except Exception as e:
            logger.error(f"Error marking trade as alerted: {e}")
            return False

    def trade_exists(self, trade_id: str) -> bool:
        """Check if trade already exists in database"""
        try:
            with self.get_cursor() as cursor:
                placeholder = "%s" if self.db_type == "postgresql" else "?"
                cursor.execute(f"""
                    SELECT 1 FROM suspicious_trades WHERE trade_id = {placeholder}
                """, (trade_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking trade exists: {e}")
            return False

    # =========================================================================
    # WALLET ANALYSIS
    # =========================================================================

    def get_wallet_stats(self, wallet_address: str) -> Optional[Dict]:
        """Get statistics for a specific wallet"""
        try:
            with self.get_cursor() as cursor:
                placeholder = "%s" if self.db_type == "postgresql" else "?"

                cursor.execute(f"""
                    SELECT * FROM wallet_analysis WHERE wallet_address = {placeholder}
                """, (wallet_address,))

                row = cursor.fetchone()
                if not row:
                    return None

                stats = dict(row)

                # Get all trades for this wallet
                cursor.execute(f"""
                    SELECT * FROM suspicious_trades
                    WHERE wallet_address = {placeholder}
                    ORDER BY timestamp DESC
                """, (wallet_address,))

                trades = cursor.fetchall()
                stats["trades"] = [dict(t) for t in trades]

                return stats
        except Exception as e:
            logger.error(f"Error fetching wallet stats: {e}")
            return None

    # =========================================================================
    # MONITORED WALLETS
    # =========================================================================

    def add_monitored_wallet(self, wallet_address: str, label: str = None,
                             notes: str = None, bypass_thresholds: bool = True) -> bool:
        """Add a wallet to monitoring list"""
        try:
            with self.get_cursor(commit=True) as cursor:
                now = datetime.now().isoformat()
                if self.db_type == "postgresql":
                    cursor.execute("""
                        INSERT INTO monitored_wallets (wallet_address, label, notes, added_at, bypass_thresholds)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (wallet_address) DO UPDATE SET
                            label = EXCLUDED.label,
                            notes = EXCLUDED.notes,
                            is_active = 1,
                            bypass_thresholds = EXCLUDED.bypass_thresholds
                    """, (wallet_address, label, notes, now, 1 if bypass_thresholds else 0))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO monitored_wallets
                        (wallet_address, label, notes, added_at, bypass_thresholds, is_active)
                        VALUES (?, ?, ?, ?, ?, 1)
                    """, (wallet_address, label, notes, now, 1 if bypass_thresholds else 0))
            logger.info(f"Added monitored wallet: {wallet_address}")
            return True
        except Exception as e:
            logger.error(f"Error adding monitored wallet: {e}")
            return False

    def remove_monitored_wallet(self, wallet_address: str) -> bool:
        """Remove a wallet from monitoring (soft delete)"""
        try:
            with self.get_cursor(commit=True) as cursor:
                placeholder = "%s" if self.db_type == "postgresql" else "?"
                cursor.execute(f"""
                    UPDATE monitored_wallets SET is_active = 0
                    WHERE wallet_address = {placeholder}
                """, (wallet_address,))
            return True
        except Exception as e:
            logger.error(f"Error removing monitored wallet: {e}")
            return False

    def get_monitored_wallets(self, active_only: bool = True) -> List[Dict]:
        """Get list of monitored wallets"""
        try:
            with self.get_cursor() as cursor:
                if active_only:
                    cursor.execute("SELECT * FROM monitored_wallets WHERE is_active = 1")
                else:
                    cursor.execute("SELECT * FROM monitored_wallets")

                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching monitored wallets: {e}")
            return []

    def is_wallet_monitored(self, wallet_address: str) -> bool:
        """Check if a wallet is being monitored"""
        try:
            with self.get_cursor() as cursor:
                placeholder = "%s" if self.db_type == "postgresql" else "?"
                cursor.execute(f"""
                    SELECT 1 FROM monitored_wallets
                    WHERE wallet_address = {placeholder} AND is_active = 1
                """, (wallet_address,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking monitored wallet: {e}")
            return False

    # =========================================================================
    # MARKETS CACHE
    # =========================================================================

    def cache_market(self, market_data: Dict) -> bool:
        """Cache market data"""
        try:
            with self.get_cursor(commit=True) as cursor:
                now = datetime.now().isoformat()
                if self.db_type == "postgresql":
                    cursor.execute("""
                        INSERT INTO markets_cache (market_id, question, category, active, cached_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (market_id) DO UPDATE SET
                            question = EXCLUDED.question,
                            category = EXCLUDED.category,
                            active = EXCLUDED.active,
                            cached_at = EXCLUDED.cached_at
                    """, (
                        market_data["market_id"], market_data["question"],
                        market_data["category"], 1 if market_data.get("active", True) else 0, now
                    ))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO markets_cache (market_id, question, category, active, cached_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        market_data["market_id"], market_data["question"],
                        market_data["category"], 1 if market_data.get("active", True) else 0, now
                    ))
            return True
        except Exception as e:
            logger.error(f"Error caching market: {e}")
            return False
