#!/usr/bin/env python3
"""
Test script to analyze a specific wallet and see why it wasn't tracked
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from polymarket_monitor import PolymarketAPI, PolygonBlockscout, DetectionConfig
from datetime import datetime
import json

# The wallet to investigate
WALLET = "0x1abe1368601330a310162064e04d3c2628cb6497"

def main():
    print(f"\n{'='*80}")
    print(f"INVESTIGATING WALLET: {WALLET}")
    print(f"{'='*80}\n")

    # Initialize API and blockchain helpers
    api = PolymarketAPI()
    blockchain = PolygonBlockscout(polymarket_api=api)

    # User's filter config
    config = DetectionConfig(
        wallet_age_days=90,
        min_bet_size=5000,  # Default, user might have different
        max_odds=0.20,  # 20 cents
        check_wallet_age=True,
        check_bet_size=True,
        check_odds=True
    )

    print("🔍 FILTER CRITERIA:")
    print(f"  - Wallet Age: ≤ {config.wallet_age_days} days")
    print(f"  - Min Bet Size: ≥ ${config.min_bet_size:,.0f}")
    print(f"  - Max Price: ≤ {config.max_odds} ({config.max_odds*100}¢)")
    print()

    # 1. Check wallet age
    print("📅 WALLET AGE CHECK:")
    wallet_age = blockchain.get_wallet_age_days(WALLET)

    if wallet_age is None:
        print("  ❌ Could not determine wallet age (API failure)")
        print("  → With new fix: WOULD BE REJECTED")
    elif wallet_age > config.wallet_age_days:
        print(f"  ❌ Wallet is {wallet_age} days old (exceeds {config.wallet_age_days} day limit)")
        print("  → REJECTED: Too old")
    else:
        print(f"  ✅ Wallet is {wallet_age} days old (within {config.wallet_age_days} day limit)")
        print("  → PASSED wallet age check")
    print()

    # 2. Get recent activity
    print("📊 RECENT ACTIVITY:")
    activity = api.get_user_activity(
        user=WALLET,
        activity_type=["TRADE"],
        limit=50
    )

    if not activity:
        print("  ❌ No trades found for this wallet")
        print()
        return

    print(f"  Found {len(activity)} recent trades\n")

    # 3. Analyze each trade against filters
    print("🔎 ANALYZING TRADES AGAINST FILTERS:\n")

    suspicious_trades = []

    for i, trade in enumerate(activity[:10], 1):  # Check first 10
        price = float(trade.get('price', 0))
        size = float(trade.get('size', 0))
        usd_value = float(trade.get('usdcSize', 0) or (size * price))
        side = trade.get('side', 'BUY')
        timestamp = trade.get('timestamp', 0)
        title = trade.get('title', 'Unknown Market')[:50]

        print(f"Trade #{i}:")
        print(f"  Market: {title}")
        print(f"  Price: {price:.4f} ({price*100:.2f}¢)")
        print(f"  Size: {size:,.0f} shares")
        print(f"  USD Value: ${usd_value:,.2f}")
        print(f"  Side: {side}")
        print(f"  Timestamp: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")

        # Check filters
        passed_filters = []
        failed_filters = []

        # Price filter
        if price <= config.max_odds:
            passed_filters.append(f"✅ Price {price:.4f} ≤ {config.max_odds}")
        else:
            failed_filters.append(f"❌ Price {price:.4f} > {config.max_odds}")

        # Bet size filter
        if usd_value >= config.min_bet_size:
            passed_filters.append(f"✅ Bet ${usd_value:,.2f} ≥ ${config.min_bet_size:,.0f}")
        else:
            failed_filters.append(f"❌ Bet ${usd_value:,.2f} < ${config.min_bet_size:,.0f}")

        # Wallet age (already checked above)
        if wallet_age is not None and wallet_age <= config.wallet_age_days:
            passed_filters.append(f"✅ Wallet age {wallet_age} days ≤ {config.wallet_age_days}")
        elif wallet_age is None:
            failed_filters.append(f"❌ Wallet age unknown (would be rejected with new fix)")
        else:
            failed_filters.append(f"❌ Wallet age {wallet_age} days > {config.wallet_age_days}")

        print("\n  Filters:")
        for pf in passed_filters:
            print(f"    {pf}")
        for ff in failed_filters:
            print(f"    {ff}")

        if len(failed_filters) == 0:
            print("\n  🚨 SHOULD HAVE BEEN FLAGGED AS SUSPICIOUS!")
            suspicious_trades.append(trade)
        else:
            print(f"\n  ✓ Correctly filtered out ({len(failed_filters)} filter(s) failed)")

        print()

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY:")
    print(f"{'='*80}")
    print(f"Total trades analyzed: {min(len(activity), 10)}")
    print(f"Should have been flagged: {len(suspicious_trades)}")

    if len(suspicious_trades) > 0:
        print("\n⚠️  This wallet SHOULD have been tracked!")
        print("Possible reasons it wasn't:")
        print("  1. Wallet age verification failed (returned None) - FIXED NOW ✅")
        print("  2. usdcSize was not fetched from /activity endpoint - FIXED NOW ✅")
        print("  3. Your min_bet_size config is different from the default $5,000")
        print("  4. The trade occurred before the tracker was running")
        print("  5. Rate limiting or API errors during the scan")
    else:
        print("\n✅ This wallet was correctly NOT tracked")
        print("   It doesn't match your filter criteria")

    print()

if __name__ == "__main__":
    main()
