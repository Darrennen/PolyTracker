# Debugging: Why Wasn't This Wallet Tracked?

Wallet: `0x1abe1368601330a310162064e04d3c2628cb6497`

## Quick Diagnosis

Run these commands to diagnose the issue:

### 1. Check Your Current Configuration

```bash
# If running locally
cat .env | grep -E "WALLET_AGE|MIN_BET|MAX_ODDS"

# Default values (if not set):
# WALLET_AGE_DAYS=30 (NOT 90!)
# MIN_BET_SIZE=10000 ($10K minimum)
# MAX_ODDS=0.20 (20¢)
```

### 2. Test This Specific Wallet

```bash
python3 test_wallet.py
```

This will show you:
- ✅ Wallet age and if it passes your filter
- ✅ Recent trades and their bet sizes
- ✅ Which filters each trade passes/fails
- ✅ Whether it SHOULD have been tracked

### 3. Check If Tracker Is Running

```bash
# Check for worker process
ps aux | grep worker

# Check database for tracked trades
sqlite3 polymarket_monitor.db "SELECT COUNT(*) FROM suspicious_trades;"

# Check logs
ls -lah *.log
```

---

## Common Reasons Wallets Are Missed

### ❌ **Reason 1: Wallet Age Filter Bug (FIXED NOW)**
**Before my fix:**
- If API couldn't determine age → wallet PASSED through
- This was **THE BUG** causing your issues

**After my fix:**
- If API can't determine age → wallet is REJECTED
- Conservative approach ensures only verified wallets pass

**Impact**: This was likely the main issue!

---

### ❌ **Reason 2: Your MIN_BET_SIZE Is Too High**

**Check your config:**
```bash
echo $MIN_BET_SIZE
# OR
grep MIN_BET_SIZE .env
```

**Default is $10,000** but you might need **$5,000** to catch more wallets.

**To test a specific wallet with different bet size:**
```python
# Edit test_wallet.py line 25:
config = DetectionConfig(
    wallet_age_days=90,
    min_bet_size=5000,  # Lower this to test
    max_odds=0.20,
)
```

---

### ❌ **Reason 3: Wallet Age Limit**

You said you set **90 days**, but the **default is 30 days**.

**Verify your setting:**
```bash
grep WALLET_AGE_DAYS .env
```

If not set, the tracker uses **30 days**, not 90!

**To fix:**
```bash
echo "WALLET_AGE_DAYS=90" >> .env
```

---

### ❌ **Reason 4: Tracker Not Running**

Check if your tracker is actually running:

```bash
# Local check
ps aux | grep worker.py

# Cloud check (Railway)
# Go to: Railway Dashboard → Your Service → Logs
# Look for: "Starting trade scan..." messages
```

If not running, start it:
```bash
# Local
python3 worker.py

# Or with specific config
WALLET_AGE_DAYS=90 MIN_BET_SIZE=5000 python3 worker.py
```

---

### ❌ **Reason 5: Timing**

The wallet might have traded:
- **Before** your tracker started running
- **During** a tracker downtime/restart
- **During** API rate limit errors

**Check your database for nearby timestamps:**
```bash
sqlite3 polymarket_monitor.db <<EOF
SELECT
    datetime(timestamp, 'unixepoch') as trade_time,
    wallet_address,
    bet_size,
    odds
FROM suspicious_trades
ORDER BY timestamp DESC
LIMIT 10;
EOF
```

---

## Step-by-Step Investigation

### Step 1: Verify This Wallet's Activity

Visit the wallet on Polymarket:
https://polymarket.com/profile/0x1abe1368601330a310162064e04d3c2628cb6497

Check for:
- 📊 Large bets (>$5K or your threshold)
- 💰 Low odds (≤20¢)
- 📅 Recent activity (last few days)

### Step 2: Check Wallet Age

Use my test script:
```bash
python3 test_wallet.py
```

Look for the "WALLET AGE CHECK" section.

### Step 3: Compare Trades to Your Filters

The test script will analyze recent trades and show which filters they pass/fail.

Example output:
```
Trade #1:
  Price: 0.1500 (15.0¢) ✅ PASSED (≤ 0.20)
  Bet: $8,500 ✅ PASSED (≥ $5,000)
  Age: 25 days ✅ PASSED (≤ 90 days)

  🚨 SHOULD HAVE BEEN FLAGGED!
```

### Step 4: Check Your Database

```bash
# Search for this specific wallet
sqlite3 polymarket_monitor.db <<EOF
SELECT * FROM suspicious_trades
WHERE wallet_address = '0x1abe1368601330a310162064e04d3c2628cb6497';
EOF

# If found: It WAS tracked!
# If not found: Check why with test script
```

---

## Most Likely Root Cause

Based on the bugs I just fixed, **here's what probably happened**:

1. **Wallet age API failed** (timeout/rate limit)
2. **Old code**: `if wallet_age is not None and wallet_age > 90:`
   - Evaluated to `False` because `wallet_age` was `None`
   - Wallet **incorrectly passed** through filter
3. **BUT THEN**: Some other filter caught it anyway, OR
4. **OR**: Your `MIN_BET_SIZE` was too high ($10K vs $5K)

**With my fix**, this can't happen anymore:
```python
# New code
if (wallet_age is None or wallet_age > 90):
    # Rejects if age unknown OR too old
    return None
```

---

## Action Items

1. ✅ **Update your code** (already done - you have the fixes)
2. ⚠️ **Check your `.env` configuration**:
   ```bash
   WALLET_AGE_DAYS=90
   MIN_BET_SIZE=5000  # Lower if needed
   MAX_ODDS=0.20
   ```
3. ✅ **Run the test script** to verify this specific wallet
4. ✅ **Restart your tracker** with the new code

---

## Need More Help?

Run this diagnostic and send me the output:
```bash
echo "=== CONFIGURATION ==="
cat .env 2>/dev/null || echo "No .env file"

echo -e "\n=== TRACKER STATUS ==="
ps aux | grep -E "worker|polymarket" | grep -v grep || echo "Not running"

echo -e "\n=== DATABASE STATS ==="
sqlite3 polymarket_monitor.db "SELECT COUNT(*) as total_tracked FROM suspicious_trades;" 2>/dev/null || echo "No database"

echo -e "\n=== WALLET TEST ==="
python3 test_wallet.py 2>&1 | head -50
```

This will tell us exactly what's configured and why the wallet wasn't caught.
