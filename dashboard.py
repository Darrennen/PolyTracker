"""
Polymarket Suspicious Wallet Monitor - Dashboard
Enhanced Streamlit UI with wallet tracking, configurable thresholds, and multi-channel alerts
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import time
import os
import json

# Import the monitor
from polymarket_monitor import PolymarketMonitor, DetectionConfig, AlertChannel

# Page configuration
st.set_page_config(
    page_title="Polymarket Sus Wallet Monitor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Main title styling */
    .main-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00d4ff, #7c3aed, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-family: 'JetBrains Mono', monospace;
        color: #94a3b8;
        text-align: center;
        font-size: 0.9rem;
        margin-bottom: 2rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(100, 116, 139, 0.3);
        border-radius: 12px;
        padding: 1.25rem;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        border-color: #7c3aed;
        box-shadow: 0 0 20px rgba(124, 58, 237, 0.2);
    }
    
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: #f1f5f9;
    }
    
    .metric-label {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Alert cards */
    .alert-critical {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(185, 28, 28, 0.1));
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .alert-warning {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(180, 83, 9, 0.1));
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .alert-info {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(29, 78, 216, 0.1));
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Wallet address styling */
    .wallet-address {
        font-family: 'JetBrains Mono', monospace;
        background: rgba(15, 23, 42, 0.8);
        color: #00d4ff;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-size: 0.85rem;
        border: 1px solid rgba(0, 212, 255, 0.3);
    }
    
    /* Position badges */
    .badge-yes {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 0.8rem;
    }
    
    .badge-no {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 0.8rem;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2e 0%, #0f0f1a 100%);
        border-right: 1px solid rgba(100, 116, 139, 0.2);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #6366f1);
        color: white;
        border: none;
        border-radius: 8px;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #8b5cf6, #818cf8);
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.4);
        transform: translateY(-2px);
    }
    
    /* Primary button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00d4ff, #0891b2);
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #22d3ee, #06b6d4);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(30, 41, 59, 0.5);
        padding: 0.5rem;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #94a3b8;
        border-radius: 8px;
        font-family: 'Space Grotesk', sans-serif;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #7c3aed, #6366f1);
        color: white;
    }
    
    /* Input styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(100, 116, 139, 0.3);
        color: #f1f5f9;
        font-family: 'JetBrains Mono', monospace;
        border-radius: 8px;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #7c3aed;
        box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.2);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.6);
        border-radius: 8px;
        font-family: 'Space Grotesk', sans-serif;
    }
    
    /* Data table */
    .stDataFrame {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Divider */
    hr {
        border-color: rgba(100, 116, 139, 0.2);
    }

    /* Fix Streamlit info/alert boxes text color for dark theme */
    .stAlert > div {
        color: #f1f5f9 !important;
    }

    .stAlert p, .stAlert li, .stAlert span {
        color: #f1f5f9 !important;
    }

    /* Make all text in main content area readable */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {
        color: #e2e8f0;
    }

    /* Risk level indicators */
    .risk-critical {
        color: #ef4444;
        font-weight: 700;
    }
    
    .risk-high {
        color: #f59e0b;
        font-weight: 600;
    }
    
    .risk-medium {
        color: #eab308;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(30, 41, 59, 0.5);
    }
    
    ::-webkit-scrollbar-thumb {
        background: #475569;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #64748b;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Session State Initialization
# ============================================================================

if 'monitor' not in st.session_state:
    st.session_state.monitor = None
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None
if 'selected_wallet' not in st.session_state:
    st.session_state.selected_wallet = None
if 'config' not in st.session_state:
    st.session_state.config = DetectionConfig()


# ============================================================================
# Sidebar Configuration
# ============================================================================

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # Database path
    db_path = st.text_input(
        "Database Path",
        value="polymarket_monitor.db",
        help="SQLite database file path"
    )
    
    st.divider()
    
    # -------------------------------------------------------------------------
    # API Configuration
    # -------------------------------------------------------------------------
    st.markdown("### 🔑 API Keys")
    
    with st.expander("Polymarket Builder API", expanded=False):
        api_key_enabled = st.checkbox(
            "Use Builder API Key",
            value=False,
            help="Higher rate limits with authenticated requests"
        )
        
        if api_key_enabled:
            api_key = st.text_input(
                "API Key",
                type="password",
                help="Get from Polymarket Builder dashboard"
            )
            if api_key:
                st.success("✓ API key set")
        else:
            api_key = None
    
    st.divider()
    
    # -------------------------------------------------------------------------
    # Detection Thresholds - THE KEY PART
    # -------------------------------------------------------------------------
    st.markdown("### 🎯 Detection Thresholds")
    
    st.markdown("##### 👛 Wallet Age")
    wallet_age_enabled = st.checkbox("Enable wallet age check", value=True)
    if wallet_age_enabled:
        wallet_age_days = st.slider(
            "Max wallet age (days)",
            min_value=1,
            max_value=90,
            value=14,
            help="Flag wallets created within this many days"
        )
        st.caption(f"🔍 Wallets < {wallet_age_days} days old will be flagged")
    else:
        wallet_age_days = 999999
    
    st.markdown("##### 💰 Bet Size")
    bet_size_enabled = st.checkbox("Enable bet size check", value=True)
    if bet_size_enabled:
        min_bet_size = st.number_input(
            "Minimum bet size (USD)",
            min_value=100,
            max_value=1000000,
            value=10000,
            step=1000,
            help="Only flag bets above this amount"
        )
        st.caption(f"🔍 Bets ≥ ${min_bet_size:,} will be analyzed")
    else:
        min_bet_size = 0
    
    st.markdown("##### 📉 Entry Price (Odds)")
    odds_enabled = st.checkbox("Enable low odds check", value=True)
    if odds_enabled:
        max_odds_cents = st.slider(
            "Max entry price (cents)",
            min_value=1,
            max_value=50,
            value=10,
            help="Flag bets where entry price is below this (e.g., 5 = 5 cents on the dollar)"
        )
        max_odds = max_odds_cents / 100
        st.caption(f"🔍 Bets at ≤ {max_odds_cents}¢ on the dollar will be flagged")
    else:
        max_odds = 1.0

    st.markdown("##### 🏷️ Category Filter")
    category_filter_enabled = st.checkbox("Enable category filter", value=False)

    # Initialize filter variables
    include_tag_ids = []
    exclude_tag_ids = []

    if category_filter_enabled:
        filter_mode = st.radio(
            "Filter mode",
            ["Exclude categories", "Include only"],
            help="Exclude: scan all EXCEPT selected. Include: scan ONLY selected."
        )

        # Common category options (tag IDs should match Polymarket API)
        # These will be dynamically populated when monitor is initialized
        category_options = {
            "🏈 Sports": "sports",
            "💰 Crypto": "crypto",
            "🏛️ Politics": "politics",
            "🎬 Entertainment": "entertainment",
            "📰 News": "news",
            "🔬 Science": "science",
            "💼 Business": "business"
        }

        selected_categories = st.multiselect(
            "Select categories",
            options=list(category_options.keys()),
            help="Choose categories to include or exclude"
        )

        # Store selected slugs for filtering
        selected_slugs = [category_options[cat] for cat in selected_categories]

        if filter_mode == "Exclude categories":
            st.caption(f"🚫 Will skip: {', '.join(selected_slugs) if selected_slugs else 'none'}")
            # These will be converted to tag IDs when scanning
            st.session_state['exclude_categories'] = selected_slugs
            st.session_state['include_categories'] = []
        else:
            st.caption(f"✅ Will only scan: {', '.join(selected_slugs) if selected_slugs else 'all'}")
            st.session_state['include_categories'] = selected_slugs
            st.session_state['exclude_categories'] = []
    else:
        st.session_state['exclude_categories'] = []
        st.session_state['include_categories'] = []

    st.divider()

    # -------------------------------------------------------------------------
    # Alert Configuration
    # -------------------------------------------------------------------------
    st.markdown("### 📣 Alerts")
    
    with st.expander("Telegram", expanded=False):
        telegram_enabled = st.checkbox("Enable Telegram alerts", value=False)
        
        if telegram_enabled:
            telegram_token = st.text_input(
                "Bot Token",
                type="password",
                help="Get from @BotFather on Telegram"
            )
            telegram_chat_id = st.text_input(
                "Chat ID",
                help="Your Telegram chat/channel ID"
            )
            
            if telegram_token and telegram_chat_id:
                if st.button("🧪 Test Telegram"):
                    try:
                        import requests
                        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                        payload = {
                            "chat_id": telegram_chat_id,
                            "text": "✅ Polymarket Monitor connected successfully!"
                        }
                        response = requests.post(url, json=payload, timeout=10)
                        if response.status_code == 200:
                            st.success("✓ Test message sent!")
                        else:
                            st.error(f"✗ Failed: {response.status_code}")
                    except Exception as e:
                        st.error(f"✗ Error: {e}")
        else:
            telegram_token = None
            telegram_chat_id = None
    
    with st.expander("Slack", expanded=False):
        slack_enabled = st.checkbox("Enable Slack alerts", value=False)
        
        if slack_enabled:
            slack_webhook = st.text_input(
                "Webhook URL",
                type="password",
                help="Slack incoming webhook URL"
            )
            
            if slack_webhook:
                if st.button("🧪 Test Slack"):
                    try:
                        import requests
                        response = requests.post(
                            slack_webhook,
                            json={"text": "✅ Polymarket Monitor connected!"},
                            timeout=10
                        )
                        if response.status_code == 200:
                            st.success("✓ Test message sent!")
                        else:
                            st.error(f"✗ Failed: {response.status_code}")
                    except Exception as e:
                        st.error(f"✗ Error: {e}")
        else:
            slack_webhook = None
    
    st.divider()
    
    # -------------------------------------------------------------------------
    # Initialize Monitor
    # -------------------------------------------------------------------------
    if st.button("🚀 Initialize Monitor", type="primary", use_container_width=True):
        # Get category filter settings from session state
        exclude_cats = st.session_state.get('exclude_categories', [])
        include_cats = st.session_state.get('include_categories', [])

        config = DetectionConfig(
            wallet_age_days=wallet_age_days,
            min_bet_size=min_bet_size,
            max_odds=max_odds,
            check_wallet_age=wallet_age_enabled,
            check_bet_size=bet_size_enabled,
            check_odds=odds_enabled,
            categories=include_cats if include_cats else exclude_cats  # For legacy text filtering
        )
        
        st.session_state.monitor = PolymarketMonitor(
            db_path=db_path,
            telegram_token=telegram_token if telegram_enabled else None,
            telegram_chat_id=telegram_chat_id if telegram_enabled else None,
            slack_webhook_url=slack_webhook if slack_enabled else None,
            api_key=api_key if api_key_enabled else None,
            config=config
        )
        st.session_state.config = config
        st.success("✓ Monitor initialized!")
        st.rerun()
    
    st.divider()
    
    # -------------------------------------------------------------------------
    # Scan Controls
    # -------------------------------------------------------------------------
    st.markdown("### 🔍 Scanning")
    
    scan_type = st.radio(
        "Scan Type",
        ["Quick (Recent Trades)", "Full (All Markets)", "Tracked Wallets"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if st.button("▶️ Run Scan Now", use_container_width=True):
        if st.session_state.monitor:
            with st.spinner("Scanning..."):
                if scan_type == "Quick (Recent Trades)":
                    stats = st.session_state.monitor.scan_recent_trades()
                elif scan_type == "Full (All Markets)":
                    # Pass category filters for full market scan
                    include_cats = st.session_state.get('include_categories', [])
                    exclude_cats = st.session_state.get('exclude_categories', [])
                    stats = st.session_state.monitor.scan_markets(
                        categories=include_cats if include_cats else None
                    )
                else:
                    stats = st.session_state.monitor.scan_tracked_wallets()

                st.session_state.last_scan_time = datetime.now()
                skipped = stats.get('events_skipped', 0)
                msg = f"✓ Found {stats.get('suspicious_found', 0)} suspicious"
                if skipped > 0:
                    msg += f" (skipped {skipped} events by filter)"
                st.success(msg)
                st.rerun()
        else:
            st.warning("Initialize monitor first")
    
    if st.session_state.last_scan_time:
        st.caption(f"Last scan: {st.session_state.last_scan_time.strftime('%H:%M:%S')}")
    
    # Active filters summary
    st.divider()
    st.markdown("### 📋 Active Filters")

    filters_active = []
    if wallet_age_enabled:
        filters_active.append(f"🕐 Age < {wallet_age_days}d")
    if bet_size_enabled:
        filters_active.append(f"💵 Bet ≥ ${min_bet_size:,}")
    if odds_enabled:
        filters_active.append(f"📉 Price ≤ {max_odds_cents}¢")

    # Show category filter status
    include_cats = st.session_state.get('include_categories', [])
    exclude_cats = st.session_state.get('exclude_categories', [])
    if include_cats:
        filters_active.append(f"🏷️ Only: {', '.join(include_cats)}")
    elif exclude_cats:
        filters_active.append(f"🚫 Skip: {', '.join(exclude_cats)}")

    if filters_active:
        for f in filters_active:
            st.caption(f"✓ {f}")
    else:
        st.caption("No filters active")


# ============================================================================
# Main Content
# ============================================================================

# Header
st.markdown('<h1 class="main-title">🎯 Polymarket Sus Wallet Monitor</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Real-time detection of suspicious betting patterns on Polymarket</p>', unsafe_allow_html=True)

# Check if monitor is initialized
if st.session_state.monitor is None:
    st.markdown("""
    <div class="alert-info">
        <h3>👋 Welcome!</h3>
        <p>Configure your detection thresholds in the sidebar and click <strong>Initialize Monitor</strong> to begin.</p>
        <br>
        <strong>What this monitors:</strong>
        <ul>
            <li>🕐 <strong>New wallets</strong> - Accounts created recently (configurable, default 14 days)</li>
            <li>💰 <strong>Large bets</strong> - High-value positions (configurable, default $10k+)</li>
            <li>📉 <strong>Low odds bets</strong> - Betting on unlikely outcomes (e.g., 5¢ on the dollar)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

monitor = st.session_state.monitor

# Get data
suspicious_trades = monitor.get_suspicious_trades(limit=1000)
dashboard_stats = monitor.get_dashboard_stats()

if suspicious_trades:
    df = pd.DataFrame(suspicious_trades)
    df['detected_at'] = pd.to_datetime(df['detected_at'])
    df['bet_size'] = df['bet_size'].astype(float)
    df['odds'] = df['odds'].astype(float)
    df['odds_cents'] = df['odds'] * 100  # Convert to cents for display
else:
    df = pd.DataFrame()


# ============================================================================
# Key Metrics
# ============================================================================

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Suspicious Trades</div>
        <div class="metric-value">{dashboard_stats.get('total_suspicious', 0):,}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Unique Wallets</div>
        <div class="metric-value">{dashboard_stats.get('unique_wallets', 0):,}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    volume = dashboard_stats.get('total_volume', 0)
    volume_display = f"${volume/1000:.0f}K" if volume >= 1000 else f"${volume:.0f}"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Volume</div>
        <div class="metric-value">{volume_display}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Tracked Wallets</div>
        <div class="metric-value">{dashboard_stats.get('tracked_wallets', 0):,}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Today's Alerts</div>
        <div class="metric-value">{dashboard_stats.get('today_suspicious', 0):,}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()


# ============================================================================
# Tabs
# ============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "🔍 Recent Activity",
    "👛 Wallet Tracker",
    "➕ Add Wallet",
    "📈 Statistics"
])


# ============================================================================
# TAB 1: Dashboard
# ============================================================================

with tab1:
    if df.empty:
        st.info("No suspicious activity detected yet. Run a scan to start monitoring.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            # Timeline chart
            st.markdown("#### 📅 Activity Timeline")
            df['date'] = df['detected_at'].dt.date
            daily_counts = df.groupby('date').size().reset_index(name='count')
            
            fig_timeline = go.Figure()
            fig_timeline.add_trace(go.Bar(
                x=daily_counts['date'],
                y=daily_counts['count'],
                marker_color='#7c3aed',
                marker_line_color='#a78bfa',
                marker_line_width=1
            ))
            fig_timeline.update_layout(
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                xaxis=dict(gridcolor='rgba(100,116,139,0.2)'),
                yaxis=dict(gridcolor='rgba(100,116,139,0.2)')
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        with col2:
            # Entry price distribution
            st.markdown("#### 📉 Entry Price Distribution")
            fig_odds = px.histogram(
                df,
                x='odds_cents',
                nbins=20,
                color_discrete_sequence=['#00d4ff']
            )
            fig_odds.update_layout(
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                xaxis_title="Entry Price (cents)",
                yaxis_title="Count",
                xaxis=dict(gridcolor='rgba(100,116,139,0.2)'),
                yaxis=dict(gridcolor='rgba(100,116,139,0.2)')
            )
            st.plotly_chart(fig_odds, use_container_width=True)
        
        # Top suspicious wallets
        st.markdown("#### 🔥 Top Suspicious Wallets")
        
        top_wallets = dashboard_stats.get('top_wallets', [])
        if top_wallets:
            wallet_df = pd.DataFrame(top_wallets)
            wallet_df['wallet_short'] = wallet_df['wallet'].apply(
                lambda x: f"{x[:8]}...{x[-6:]}"
            )
            wallet_df['volume_fmt'] = wallet_df['volume'].apply(
                lambda x: f"${x:,.0f}"
            )
            
            fig_wallets = px.bar(
                wallet_df.head(10),
                x='count',
                y='wallet_short',
                orientation='h',
                color='volume',
                color_continuous_scale='Viridis',
                hover_data={'wallet': True, 'volume_fmt': True}
            )
            fig_wallets.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                yaxis_title="",
                xaxis_title="Suspicious Trade Count",
                xaxis=dict(gridcolor='rgba(100,116,139,0.2)'),
                yaxis=dict(gridcolor='rgba(100,116,139,0.2)')
            )
            st.plotly_chart(fig_wallets, use_container_width=True)


# ============================================================================
# TAB 2: Recent Activity
# ============================================================================

with tab2:
    st.markdown("#### 🔍 Recent Suspicious Trades")
    
    if df.empty:
        st.info("No suspicious activity detected yet.")
    else:
        # Filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            filter_min_bet = st.number_input(
                "Min Bet Size ($)",
                value=0,
                step=1000,
                key="filter_min_bet"
            )
        
        with col2:
            filter_max_price = st.slider(
                "Max Entry Price (¢)",
                min_value=1,
                max_value=100,
                value=100,
                key="filter_max_price"
            )
        
        with col3:
            filter_position = st.selectbox(
                "Position",
                ["All", "YES", "NO"],
                key="filter_position"
            )
        
        with col4:
            filter_age = st.slider(
                "Max Wallet Age (days)",
                min_value=0,
                max_value=90,
                value=90,
                key="filter_age"
            )
        
        # Apply filters
        filtered_df = df.copy()
        filtered_df = filtered_df[filtered_df['bet_size'] >= filter_min_bet]
        filtered_df = filtered_df[filtered_df['odds_cents'] <= filter_max_price]
        
        if filter_position != "All":
            filtered_df = filtered_df[filtered_df['outcome'] == filter_position]
        
        if filter_age < 90:
            filtered_df = filtered_df[
                (filtered_df['wallet_age_days'].isna()) | 
                (filtered_df['wallet_age_days'] <= filter_age)
            ]
        
        st.caption(f"Showing {len(filtered_df)} trades")
        st.divider()
        
        # Display trades
        for idx, row in filtered_df.head(50).iterrows():
            # Determine risk level
            risk_class = "alert-info"
            risk_emoji = "⚠️"
            
            if row['wallet_age_days'] is not None and row['wallet_age_days'] < 7:
                risk_class = "alert-critical"
                risk_emoji = "🚨"
            elif row['odds_cents'] < 10:
                risk_class = "alert-critical"
                risk_emoji = "🚨"
            elif row['bet_size'] >= 50000:
                risk_class = "alert-warning"
                risk_emoji = "⚠️"
            
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"**{risk_emoji} {row['market_question'][:80]}...**")
                    st.caption(f"Category: {row['market_category']}")
                
                with col2:
                    if row['outcome'] == 'YES':
                        st.markdown('<span class="badge-yes">YES</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-no">NO</span>', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown("**Bet Size**")
                    st.markdown(f"${row['bet_size']:,.0f}")
                    potential = row['bet_size'] / row['odds'] if row['odds'] > 0 else 0
                    st.caption(f"Potential: ${potential:,.0f}")
                
                with col2:
                    st.markdown("**Entry Price**")
                    st.markdown(f"{row['odds_cents']:.1f}¢")
                    st.caption("on the dollar")
                
                with col3:
                    st.markdown("**Wallet**")
                    st.code(f"{row['wallet_address'][:10]}...{row['wallet_address'][-6:]}")
                    age_str = f"{row['wallet_age_days']}d" if row['wallet_age_days'] else "?"
                    st.caption(f"Age: {age_str}")
                
                with col4:
                    st.markdown("**Actions**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("📊", key=f"scan_{row['id']}", help="View on Polygonscan"):
                            st.markdown(f"[Open Polygonscan](https://polygonscan.com/address/{row['wallet_address']})")
                    with col_b:
                        if st.button("🔍", key=f"track_{row['id']}", help="Track this wallet"):
                            monitor.add_tracked_wallet(row['wallet_address'])
                            st.success("Added to tracking!")
                
                st.divider()


# ============================================================================
# TAB 3: Wallet Tracker
# ============================================================================

with tab3:
    st.markdown("#### 👛 Tracked Wallets")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_query = st.text_input(
            "🔍 Search wallets",
            placeholder="Enter wallet address or label...",
            key="wallet_search"
        )
    
    with col2:
        if st.button("🔄 Refresh", key="refresh_wallets"):
            st.rerun()
    
    # Get tracked wallets
    tracked_wallets = monitor.get_tracked_wallets()
    
    if search_query:
        # Search functionality
        search_results = monitor.search_wallets(search_query)
        
        if search_results:
            st.markdown(f"##### Found {len(search_results)} results")
            
            for result in search_results:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.code(result['wallet_address'])
                        st.caption(f"Source: {result['source']} | {result['info']}")
                    
                    with col2:
                        st.link_button(
                            "Polygonscan",
                            f"https://polygonscan.com/address/{result['wallet_address']}"
                        )
                    
                    with col3:
                        if st.button("Track", key=f"add_{result['wallet_address'][:8]}"):
                            monitor.add_tracked_wallet(result['wallet_address'])
                            st.success("Added!")
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No wallets found matching your search.")
    
    else:
        # Show all tracked wallets
        if tracked_wallets:
            st.markdown(f"##### Tracking {len(tracked_wallets)} wallets")
            
            for wallet in tracked_wallets:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{wallet.get('label', 'Unknown')}**")
                        st.code(wallet['wallet_address'])
                        st.caption(f"Added: {wallet['added_at'][:10]} | Alerts: {wallet.get('total_alerts', 0)}")
                    
                    with col2:
                        stats = monitor.get_wallet_stats(wallet['wallet_address'])
                        if stats:
                            st.metric("Volume", f"${stats.get('total_volume', 0):,.0f}")
                    
                    with col3:
                        st.link_button(
                            "📊 View",
                            f"https://polygonscan.com/address/{wallet['wallet_address']}"
                        )
                    
                    with col4:
                        if st.button("🗑️", key=f"del_{wallet['wallet_address'][:8]}"):
                            monitor.remove_tracked_wallet(wallet['wallet_address'])
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No wallets being tracked. Add wallets in the 'Add Wallet' tab.")


# ============================================================================
# TAB 4: Add Wallet
# ============================================================================

with tab4:
    st.markdown("#### ➕ Add Wallet to Track")
    st.markdown("Add wallets you want to monitor for suspicious activity.")
    
    with st.form("add_wallet_form"):
        wallet_address = st.text_input(
            "Wallet Address",
            placeholder="0x...",
            help="Polygon wallet address to track"
        )
        
        wallet_label = st.text_input(
            "Label (optional)",
            placeholder="e.g., 'Whale #1', 'Suspicious Actor'",
            help="A friendly name for this wallet"
        )
        
        wallet_reason = st.text_area(
            "Reason (optional)",
            placeholder="Why are you tracking this wallet?",
            help="Notes about why this wallet is being tracked"
        )
        
        submitted = st.form_submit_button("Add Wallet", type="primary")
        
        if submitted:
            if wallet_address:
                wallet_address = wallet_address.strip().lower()
                
                if wallet_address.startswith("0x") and len(wallet_address) == 42:
                    success = monitor.add_tracked_wallet(
                        wallet_address,
                        label=wallet_label if wallet_label else None,
                        reason=wallet_reason if wallet_reason else None
                    )
                    
                    if success:
                        st.success(f"✓ Added wallet: {wallet_address[:16]}...")
                        
                        # Try to get wallet info
                        age = monitor.blockchain.get_wallet_age_days(wallet_address)
                        if age is not None:
                            st.info(f"Wallet age: {age} days")
                    else:
                        st.error("Failed to add wallet")
                else:
                    st.error("Invalid wallet address. Must start with 0x and be 42 characters.")
            else:
                st.warning("Please enter a wallet address")
    
    st.divider()
    
    # Bulk add
    st.markdown("#### 📋 Bulk Add Wallets")
    
    bulk_wallets = st.text_area(
        "Paste wallet addresses (one per line)",
        placeholder="0x123...\n0x456...\n0x789...",
        height=150
    )
    
    if st.button("Add All", type="primary"):
        if bulk_wallets:
            addresses = [
                addr.strip().lower() 
                for addr in bulk_wallets.strip().split('\n') 
                if addr.strip()
            ]
            
            added = 0
            for addr in addresses:
                if addr.startswith("0x") and len(addr) == 42:
                    if monitor.add_tracked_wallet(addr):
                        added += 1
            
            st.success(f"Added {added}/{len(addresses)} wallets")


# ============================================================================
# TAB 5: Statistics
# ============================================================================

with tab5:
    st.markdown("#### 📈 Statistics & Insights")
    
    if df.empty:
        st.info("No data available. Run a scan to collect statistics.")
    else:
        # Position Analysis
        st.markdown("##### 🎯 Position Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        yes_bets = df[df['outcome'] == 'YES']
        no_bets = df[df['outcome'] == 'NO']
        
        with col1:
            st.metric("YES Positions", len(yes_bets))
            st.caption(f"Volume: ${yes_bets['bet_size'].sum():,.0f}")
        
        with col2:
            st.metric("NO Positions", len(no_bets))
            st.caption(f"Volume: ${no_bets['bet_size'].sum():,.0f}")
        
        with col3:
            yes_pct = (len(yes_bets) / len(df) * 100) if len(df) > 0 else 0
            st.metric("YES %", f"{yes_pct:.1f}%")
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 💰 Bet Size vs Entry Price")
            
            fig_scatter = px.scatter(
                df,
                x='odds_cents',
                y='bet_size',
                color='outcome',
                size='bet_size',
                color_discrete_map={'YES': '#10b981', 'NO': '#ef4444'},
                hover_data=['market_question']
            )
            fig_scatter.update_layout(
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                xaxis_title="Entry Price (cents)",
                yaxis_title="Bet Size ($)",
                xaxis=dict(gridcolor='rgba(100,116,139,0.2)'),
                yaxis=dict(gridcolor='rgba(100,116,139,0.2)')
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        with col2:
            st.markdown("##### 👛 Wallet Age Distribution")
            
            known_ages = df[df['wallet_age_days'].notna()]
            
            if len(known_ages) > 0:
                fig_age = px.histogram(
                    known_ages,
                    x='wallet_age_days',
                    nbins=20,
                    color_discrete_sequence=['#f59e0b']
                )
                fig_age.add_vline(x=7, line_dash="dash", line_color="#ef4444")
                fig_age.add_vline(x=14, line_dash="dash", line_color="#f59e0b")
                fig_age.update_layout(
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#94a3b8',
                    xaxis_title="Wallet Age (days)",
                    yaxis_title="Count",
                    xaxis=dict(gridcolor='rgba(100,116,139,0.2)'),
                    yaxis=dict(gridcolor='rgba(100,116,139,0.2)')
                )
                st.plotly_chart(fig_age, use_container_width=True)
            else:
                st.info("No wallet age data available")
        
        st.divider()
        
        # Summary stats
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 💵 Bet Size Stats")
            st.write(f"**Average:** ${df['bet_size'].mean():,.0f}")
            st.write(f"**Median:** ${df['bet_size'].median():,.0f}")
            st.write(f"**Max:** ${df['bet_size'].max():,.0f}")
            st.write(f"**Total:** ${df['bet_size'].sum():,.0f}")
        
        with col2:
            st.markdown("##### 📉 Entry Price Stats")
            st.write(f"**Average:** {df['odds_cents'].mean():.1f}¢")
            st.write(f"**Median:** {df['odds_cents'].median():.1f}¢")
            st.write(f"**Min:** {df['odds_cents'].min():.1f}¢")
            st.write(f"**Max:** {df['odds_cents'].max():.1f}¢")


# ============================================================================
# Footer
# ============================================================================

st.divider()
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.8rem;">
    🎯 Polymarket Sus Wallet Monitor | Built with Streamlit<br>
    Data stored locally in SQLite | Not financial advice
</div>
""", unsafe_allow_html=True)
