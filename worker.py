"""
PolyTracker Worker - 24/7 Monitoring Service
Deploy this on Railway for continuous monitoring.
"""

import os
import sys
import logging
from polymarket_monitor import PolymarketMonitor

# Configure logging for cloud
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    """Main worker entry point"""

    # Log startup info
    logger.info("=" * 50)
    logger.info("PolyTracker Worker Starting")
    logger.info("=" * 50)

    # Check required environment variables
    required_vars = []
    optional_vars = {
        "DATABASE_URL": "PostgreSQL connection",
        "POLYGONSCAN_API_KEY": "Wallet age detection",
        "TELEGRAM_BOT_TOKEN": "Telegram alerts",
        "TELEGRAM_CHAT_ID": "Telegram alerts",
        "SLACK_WEBHOOK_URL": "Slack alerts",
        "POLYMARKET_API_KEY": "Higher rate limits"
    }

    logger.info("Environment configuration:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            masked = value[:4] + "..." + value[-4:] if len(value) > 10 else "***"
            logger.info(f"  ✓ {var}: {masked} ({description})")
        else:
            logger.warning(f"  ✗ {var}: Not set ({description})")

    # Get configuration from environment
    scan_interval = int(os.getenv("SCAN_INTERVAL_MINUTES", 5))
    categories = os.getenv("CATEGORIES", "news,crypto,cryptocurrency,politics,sports")
    categories_list = [c.strip() for c in categories.split(",")]

    logger.info(f"Scan interval: {scan_interval} minutes")
    logger.info(f"Categories: {categories_list}")

    # Check for at least one notification method
    has_telegram = os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")
    has_slack = os.getenv("SLACK_WEBHOOK_URL")

    if not has_telegram and not has_slack:
        logger.warning("⚠️ No notification method configured!")
        logger.warning("Set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID or SLACK_WEBHOOK_URL")
        logger.warning("Continuing without alerts...")

    # Initialize monitor
    try:
        monitor = PolymarketMonitor(categories=categories_list)
        logger.info("Monitor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize monitor: {e}")
        sys.exit(1)

    # Start continuous monitoring
    logger.info("=" * 50)
    logger.info("Starting continuous monitoring...")
    logger.info("=" * 50)

    monitor.run_continuous(interval_minutes=scan_interval)


if __name__ == "__main__":
    main()
