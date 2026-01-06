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

# Custom CSS for Cyber-Dark Enhanced UI
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Orbitron:wght@400;600;700;900&display=swap');

    /* ============================================
       CYBER-DARK THEME - Global Styles
       ============================================ */
    .stApp {
        background: #0a0e27;
        background-image:
            radial-gradient(at 0% 0%, rgba(16, 185, 129, 0.05) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(239, 68, 68, 0.05) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(59, 130, 246, 0.05) 0px, transparent 50%);
    }
    
    /* ============================================
       TITLE & BRANDING
       ============================================ */
    .main-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 2.5rem;
        font-weight: 900;
        background: linear-gradient(135deg, #10b981 0%, #3b82f6 50%, #ef4444 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 40px rgba(16, 185, 129, 0.3);
        letter-spacing: 2px;
    }

    .subtitle {
        font-family: 'JetBrains Mono', monospace;
        color: #64748b;
        text-align: center;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 3px;
    }

    /* ============================================
       METRIC CARDS - Cyber Style
       ============================================ */
    .metric-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.6));
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(20px);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(16, 185, 129, 0.1) 0%, transparent 70%);
        opacity: 0;
        transition: opacity 0.3s;
    }

    .metric-card:hover::after {
        opacity: 1;
    }

    .metric-card:hover {
        border-color: #10b981;
        box-shadow: 0 0 30px rgba(16, 185, 129, 0.3);
        transform: translateY(-4px);
    }

    .metric-value {
        font-family: 'Orbitron', monospace;
        font-size: 2.2rem;
        font-weight: 700;
        color: #10b981;
        text-shadow: 0 0 20px rgba(16, 185, 129, 0.5);
    }

    .metric-value-red {
        color: #ef4444;
        text-shadow: 0 0 20px rgba(239, 68, 68, 0.5);
    }

    .metric-label {
        font-family: 'JetBrains Mono', sans-serif;
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.1em;
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
    
    /* ============================================
       POSITION BADGES - Neon YES/NO
       ============================================ */
    .badge-yes {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 0.3rem 0.9rem;
        border-radius: 20px;
        font-family: 'Orbitron', monospace;
        font-weight: 700;
        font-size: 0.75rem;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .badge-no {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 0.3rem 0.9rem;
        border-radius: 20px;
        font-family: 'Orbitron', monospace;
        font-weight: 700;
        font-size: 0.75rem;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* ============================================
       SIDEBAR - Dark Cyber Theme
       ============================================ */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #0a0e27 100%);
        border-right: 2px solid rgba(16, 185, 129, 0.2);
        box-shadow: 4px 0 20px rgba(0, 0, 0, 0.5);
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
    
    /* ============================================
       RESPONSIVE DESIGN - Mobile & Desktop
       ============================================ */
    @media (max-width: 768px) {
        .main-title { font-size: 1.5rem !important; }
        .metric-value { font-size: 1.5rem !important; }
        .bento-grid { grid-template-columns: 1fr !important; }
        .ticker-tape { font-size: 0.75rem !important; }
    }

    /* ============================================
       TICKER TAPE - Live Market Feed
       ============================================ */
    .ticker-tape {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        border-bottom: 1px solid #10b981;
        padding: 0.5rem 0;
        overflow: hidden;
        position: relative;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.1);
    }

    .ticker-content {
        display: flex;
        animation: ticker-scroll 30s linear infinite;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
    }

    .ticker-item {
        padding: 0 2rem;
        white-space: nowrap;
        color: #94a3b8;
    }

    .ticker-item .market-name {
        color: #e2e8f0;
        font-weight: 600;
    }

    .ticker-item .price-up {
        color: #10b981;
    }

    .ticker-item .price-down {
        color: #ef4444;
    }

    @keyframes ticker-scroll {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }

    /* ============================================
       BENTO GRID - Modular Layout
       ============================================ */
    .bento-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }

    .bento-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(100, 116, 139, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(20px);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .bento-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #10b981, transparent);
        opacity: 0;
        transition: opacity 0.3s;
    }

    .bento-card:hover::before {
        opacity: 1;
    }

    .bento-card:hover {
        border-color: #10b981;
        box-shadow: 0 0 30px rgba(16, 185, 129, 0.15);
        transform: translateY(-2px);
    }

    /* ============================================
       WHALE WATCHER - Large Trade Alerts
       ============================================ */
    .whale-alert {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(185, 28, 28, 0.05));
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-left: 4px solid #ef4444;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.75rem 0;
        animation: pulse-red 2s ease-in-out infinite;
    }

    .whale-alert-mega {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(124, 58, 237, 0.05));
        border: 1px solid rgba(168, 85, 247, 0.3);
        border-left: 4px solid #a855f7;
        animation: pulse-purple 2s ease-in-out infinite;
    }

    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
        50% { box-shadow: 0 0 20px 5px rgba(239, 68, 68, 0.2); }
    }

    @keyframes pulse-purple {
        0%, 100% { box-shadow: 0 0 0 0 rgba(168, 85, 247, 0.4); }
        50% { box-shadow: 0 0 20px 5px rgba(168, 85, 247, 0.2); }
    }

    /* ============================================
       CATEGORY PILLS - Compact Design
       ============================================ */
    .category-pill {
        display: inline-block;
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(100, 116, 139, 0.3);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        margin: 0.25rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #94a3b8;
        transition: all 0.2s;
        cursor: pointer;
    }

    .category-pill:hover {
        border-color: #10b981;
        color: #10b981;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
    }

    .category-pill-active {
        background: linear-gradient(135deg, #10b981, #059669);
        border-color: #10b981;
        color: white;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
    }

    /* ============================================
       SPARKLINES - Mini Charts
       ============================================ */
    .sparkline-container {
        height: 40px;
        width: 100%;
        position: relative;
    }

    .sparkline {
        stroke: #10b981;
        stroke-width: 2;
        fill: none;
    }

    .sparkline-down {
        stroke: #ef4444;
    }

    /* ============================================
       LIVE UPDATE PULSE
       ============================================ */
    .live-pulse {
        animation: pulse-glow 2s ease-in-out infinite;
    }

    @keyframes pulse-glow {
        0%, 100% {
            opacity: 1;
            transform: scale(1);
        }
        50% {
            opacity: 0.7;
            transform: scale(1.02);
        }
    }

    .live-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #10b981;
        border-radius: 50%;
        margin-right: 0.5rem;
        animation: blink 1s ease-in-out infinite;
    }

    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }

    /* ============================================
       SCROLLBAR STYLING
       ============================================ */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(15, 23, 42, 0.5);
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
if 'selected_categories' not in st.session_state:
    # Default categories similar to Polymarket
    st.session_state.selected_categories = ["Politics", "Crypto", "Sports", "Finance"]
if 'auto_refresh_enabled' not in st.session_state:
    st.session_state.auto_refresh_enabled = False
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = datetime.now()
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 60
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'auth_page' not in st.session_state:
    st.session_state.auth_page = "login"  # "login" or "signup"


# ============================================================================
# Authentication Gate
# ============================================================================

def show_login_page():
    """Display login form"""
    st.markdown('<h1 class="main-title">🎯 Polymarket Sus Wallet Monitor</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Please login to continue</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 🔐 Login")

        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login", use_container_width=True, type="primary")

            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    # Initialize temporary monitor just for authentication
                    temp_monitor = PolymarketMonitor(db_path="polymarket_monitor.db")
                    success, user_data = temp_monitor.authenticate_user(username, password)

                    if success:
                        st.session_state.authenticated = True
                        st.session_state.current_user = user_data
                        st.success(f"Welcome back, {user_data['username']}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid username or password")

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("Don't have an account?")
        with col_b:
            if st.button("Sign Up", use_container_width=True):
                st.session_state.auth_page = "signup"
                st.rerun()


def show_signup_page():
    """Display signup form"""
    st.markdown('<h1 class="main-title">🎯 Polymarket Sus Wallet Monitor</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Create your account</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 📝 Sign Up")

        with st.form("signup_form"):
            username = st.text_input("Username (min 3 characters)", key="signup_username")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password (min 6 characters)", type="password", key="signup_password")
            password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")
            submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")

            if submit:
                if not username or not email or not password or not password_confirm:
                    st.error("Please fill in all fields")
                elif password != password_confirm:
                    st.error("Passwords do not match")
                else:
                    # Initialize temporary monitor just for user creation
                    temp_monitor = PolymarketMonitor(db_path="polymarket_monitor.db")
                    success, message = temp_monitor.create_user(username, email, password)

                    if success:
                        st.success(message)
                        st.info("Please login with your new account")
                        time.sleep(1)
                        st.session_state.auth_page = "login"
                        st.rerun()
                    else:
                        st.error(message)

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("Already have an account?")
        with col_b:
            if st.button("Login", use_container_width=True):
                st.session_state.auth_page = "login"
                st.rerun()


# Check authentication status
if not st.session_state.authenticated:
    if st.session_state.auth_page == "login":
        show_login_page()
    else:
        show_signup_page()
    st.stop()


# ============================================================================
# Sidebar Configuration
# ============================================================================

with st.sidebar:
    # User info and logout
    st.markdown(f"### 👤 {st.session_state.current_user['username']}")
    st.caption(f"📧 {st.session_state.current_user['email']}")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.session_state.monitor = None
        st.success("Logged out successfully")
        time.sleep(0.5)
        st.rerun()

    st.divider()

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
        config = DetectionConfig(
            wallet_age_days=wallet_age_days,
            min_bet_size=min_bet_size,
            max_odds=max_odds,
            check_wallet_age=wallet_age_enabled,
            check_bet_size=bet_size_enabled,
            check_odds=odds_enabled
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
                    # Pass selected categories to scan
                    categories = st.session_state.selected_categories if st.session_state.selected_categories else None
                    stats = st.session_state.monitor.scan_markets(categories=categories)
                else:
                    stats = st.session_state.monitor.scan_tracked_wallets()
                
                st.session_state.last_scan_time = datetime.now()
                st.success(f"✓ Found {stats.get('suspicious_found', 0)} suspicious")
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
    
    if filters_active:
        for f in filters_active:
            st.caption(f"✓ {f}")
    else:
        st.caption("No filters active")

    # Auto-refresh settings
    st.divider()
    st.markdown("### 🔄 Auto-Refresh")

    auto_refresh = st.checkbox(
        "Enable auto-refresh",
        value=st.session_state.auto_refresh_enabled,
        help="Automatically refresh dashboard every 60 seconds"
    )
    st.session_state.auto_refresh_enabled = auto_refresh

    if auto_refresh:
        refresh_interval = st.slider(
            "Refresh interval (seconds)",
            min_value=30,
            max_value=300,
            value=st.session_state.refresh_interval,
            step=30,
            help="How often to refresh the dashboard"
        )
        st.session_state.refresh_interval = refresh_interval
        st.caption(f"⏱️ Refreshing every {refresh_interval}s")

    # Market filter
    st.divider()
    st.markdown("### 🎯 Market Filter")

    # Get tracked markets for filtering
    if 'monitor' in st.session_state and st.session_state.monitor:
        tracked_markets = st.session_state.monitor.get_tracked_markets()

        if tracked_markets:
            market_options = ["All Markets"] + [
                f"{m['question'][:40]}..." if len(m['question']) > 40 else m['question']
                for m in tracked_markets
            ]
            selected_market = st.selectbox(
                "Filter by market",
                market_options,
                key="market_filter"
            )

            if selected_market != "All Markets":
                idx = market_options.index(selected_market) - 1
                st.caption(f"🎯 Tracking: {tracked_markets[idx]['question'][:30]}...")
        else:
            st.caption("No markets tracked yet")
            st.caption("Add markets in Market Tracker tab")


# ============================================================================
# Main Content
# ============================================================================

# ============================================================================
# TICKER TAPE - Live Market Feed
# ============================================================================
st.markdown('''
<div class="ticker-tape">
    <div class="ticker-content">
        <div class="ticker-item">
            <span class="live-indicator"></span>
            <span class="market-name">LIVE FEED</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Politics</span> •
            <span class="price-up">↑ $2.3M Vol</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Crypto</span> •
            <span class="price-down">↓ $1.8M Vol</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Sports</span> •
            <span class="price-up">↑ $945K Vol</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Finance</span> •
            <span class="price-up">↑ $1.2M Vol</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Elections</span> •
            <span class="price-up">↑ $5.7M Vol</span>
        </div>
        <!-- Duplicate for seamless scroll -->
        <div class="ticker-item">
            <span class="live-indicator"></span>
            <span class="market-name">LIVE FEED</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Politics</span> •
            <span class="price-up">↑ $2.3M Vol</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Crypto</span> •
            <span class="price-down">↓ $1.8M Vol</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Sports</span> •
            <span class="price-up">↑ $945K Vol</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Finance</span> •
            <span class="price-up">↑ $1.2M Vol</span>
        </div>
        <div class="ticker-item">
            <span class="market-name">Elections</span> •
            <span class="price-up">↑ $5.7M Vol</span>
        </div>
    </div>
</div>
''', unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-title">⚡ WHALE WATCHER</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Suspicious Activity Detection System</p>', unsafe_allow_html=True)

# ============================================================================
# Auto-Refresh Logic
# ============================================================================
if st.session_state.auto_refresh_enabled:
    # Check how much time has passed since last refresh
    time_since_refresh = (datetime.now() - st.session_state.last_refresh_time).total_seconds()

    # Get refresh interval from session state
    refresh_interval = st.session_state.refresh_interval

    # Show countdown timer
    time_remaining = max(0, refresh_interval - int(time_since_refresh))

    if time_remaining > 0:
        # Display countdown
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            st.caption(f"🔄 Next refresh in {time_remaining}s")

    # Trigger refresh if interval has passed
    if time_since_refresh >= refresh_interval:
        st.session_state.last_refresh_time = datetime.now()
        time.sleep(0.1)  # Small delay to ensure UI updates
        st.rerun()

    # Use st.empty() to create a placeholder that will trigger rerun
    # This makes the countdown actually count down
    time.sleep(1)
    st.rerun()

# ============================================================================
# Category Selection (Polymarket-style) - Always visible
# ============================================================================

# ============================================================================
# COMPACT CATEGORY SELECTOR
# ============================================================================

# All available Polymarket categories
ALL_CATEGORIES = [
    "Politics", "Crypto", "Sports", "Finance", "Geopolitics",
    "Earnings", "Tech", "Culture", "World", "Economy",
    "Climate & Science", "Elections", "AI", "Business", "Pop Culture"
]

# Use expander for collapsible category selection
with st.expander("📂 MARKET CATEGORIES", expanded=False):
    st.caption("Select categories to monitor")

    # Create compact 3-column layout for better mobile support
    cols = st.columns(3)
    for idx, category in enumerate(ALL_CATEGORIES):
        col_idx = idx % 3
        with cols[col_idx]:
            is_selected = category in st.session_state.selected_categories

            if st.button(
                f"{'✓ ' if is_selected else ''}{category}",
                key=f"cat_{category}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                # Toggle category selection
                if is_selected:
                    st.session_state.selected_categories.remove(category)
                else:
                    st.session_state.selected_categories.append(category)
                st.rerun()

# Show active categories as compact badges
if st.session_state.selected_categories:
    st.markdown(f"**Active:** {' · '.join(st.session_state.selected_categories)}")
else:
    st.warning("⚠️ All categories monitored")

st.divider()

# Check if monitor is initialized
if st.session_state.monitor is None:
    with st.expander("👋 WELCOME - Get Started", expanded=True):
        st.markdown("""
        Configure your detection thresholds in the sidebar and click **Initialize Monitor** to begin.

        **What this monitors:**
        - 🕐 **New wallets** - Accounts created recently (configurable)
        - 💰 **Large bets** - High-value positions ($10k+)
        - 📉 **Low odds bets** - Betting on unlikely outcomes
        """)
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

    # Apply category filter if categories are selected
    if st.session_state.selected_categories:
        # Build category keywords mapping
        category_keywords = {
            "Politics": ["trump", "biden", "election", "president", "senate", "congress", "politics", "vote", "poll"],
            "Sports": ["nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball", "baseball", "sports", "game", "playoff"],
            "Crypto": ["bitcoin", "crypto", "btc", "eth", "ethereum", "blockchain", "defi", "nft"],
            "Finance": ["stock", "market", "fed", "interest", "economy", "dow", "s&p", "nasdaq", "trading"],
            "Tech": ["tech", "apple", "google", "amazon", "microsoft", "ai", "software"],
            "Culture": ["culture", "music", "movie", "celebrity", "entertainment"],
            "Pop Culture": ["pop", "celebrity", "kardashian", "taylor", "beyonce"],
            "Geopolitics": ["china", "russia", "ukraine", "war", "nato", "conflict", "israel", "gaza"],
            "World": ["global", "international", "world", "country"],
            "Economy": ["gdp", "inflation", "recession", "unemployment", "economic"],
            "Climate & Science": ["climate", "science", "weather", "temperature", "carbon", "research"],
            "Elections": ["election", "vote", "ballot", "primary", "caucus"],
            "AI": ["ai", "artificial intelligence", "chatgpt", "openai", "llm"],
            "Business": ["business", "company", "ceo", "earnings", "profit"],
            "Earnings": ["earnings", "revenue", "profit", "quarterly", "q1", "q2", "q3", "q4"]
        }

        # Filter to only show trades matching selected categories
        def matches_category(row):
            market_text = (str(row.get('market_question', '')) + ' ' + str(row.get('market_category', ''))).lower()
            for category in st.session_state.selected_categories:
                keywords = category_keywords.get(category, [category.lower()])
                if any(keyword in market_text for keyword in keywords):
                    return True
            return False

        df = df[df.apply(matches_category, axis=1)]
else:
    df = pd.DataFrame()

# Show category filter status
if st.session_state.selected_categories:
    st.info(f"🔍 Filtering by categories: **{', '.join(st.session_state.selected_categories)}** ({len(df)} trades match)")

# ============================================================================
# WHALE WATCHER - Large Trade Alerts
# ============================================================================
if not df.empty:
    whale_threshold = 50000  # $50k+
    whale_trades = df[df['bet_size'] >= whale_threshold].sort_values('detected_at', ascending=False).head(5)

    if not whale_trades.empty:
        st.markdown("### 🐋 WHALE ALERTS")
        for _, trade in whale_trades.iterrows():
            alert_class = "whale-alert-mega" if trade['bet_size'] >= 100000 else "whale-alert"
            outcome_badge = "badge-yes" if trade['outcome'] == "YES" else "badge-no"

            st.markdown(f'''
            <div class="{alert_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 200px;">
                        <div style="font-size: 1.2rem; font-weight: 700; color: #ef4444; font-family: 'Orbitron', monospace; text-shadow: 0 0 15px rgba(239, 68, 68, 0.5);">
                            ${trade['bet_size']:,.0f}
                        </div>
                        <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.25rem;">
                            {trade['market_question'][:60]}...
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span class="{outcome_badge}">{trade['outcome']}</span>
                        <div style="color: #64748b; font-size: 0.75rem; margin-top: 0.25rem; font-family: 'JetBrains Mono', monospace;">
                            {trade['wallet_address'][:10]}...{trade['wallet_address'][-6:]}
                        </div>
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

        st.divider()

# ============================================================================
# Key Metrics - Bento Grid Layout
# ============================================================================

# Use bento-grid for responsive metrics
st.markdown('<div class="bento-grid">', unsafe_allow_html=True)

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
        <div class="metric-value metric-value-red">{dashboard_stats.get('today_suspicious', 0):,}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close bento-grid

st.divider()


# ============================================================================
# Tabs - Enhanced Navigation
# ============================================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "⚡ DASHBOARD",
    "🔴 LIVE ACTIVITY",
    "📍 WALLET TRACKER",
    "🎯 MARKET TRACKER",
    "➕ ADD WALLET",
    "📊 STATISTICS"
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
                marker_color='#10b981',
                marker_line_color='#059669',
                marker_line_width=2
            ))
            fig_timeline.update_layout(
                height=300,
                paper_bgcolor='rgba(10, 14, 39, 0.5)',
                plot_bgcolor='rgba(15, 23, 42, 0.5)',
                font_color='#94a3b8',
                xaxis=dict(gridcolor='rgba(16, 185, 129, 0.1)'),
                yaxis=dict(gridcolor='rgba(16, 185, 129, 0.1)')
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        with col2:
            # Entry price distribution
            st.markdown("#### 📉 Entry Price Distribution")
            fig_odds = px.histogram(
                df,
                x='odds_cents',
                nbins=20,
                color_discrete_sequence=['#ef4444']
            )
            fig_odds.update_layout(
                height=300,
                paper_bgcolor='rgba(10, 14, 39, 0.5)',
                plot_bgcolor='rgba(15, 23, 42, 0.5)',
                font_color='#94a3b8',
                xaxis_title="Entry Price (cents)",
                yaxis_title="Count",
                xaxis=dict(gridcolor='rgba(239, 68, 68, 0.1)'),
                yaxis=dict(gridcolor='rgba(239, 68, 68, 0.1)')
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
# TAB 2: LIVE ACTIVITY - Redesigned
# ============================================================================

with tab2:
    st.markdown("### 🔴 LIVE SUSPICIOUS ACTIVITY")

    if df.empty:
        st.info("No suspicious activity detected yet. Run a scan to start monitoring.")
    else:
        # Enhanced Filters with Cyber Theme
        st.markdown("#### FILTERS")
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

        # Apply market filter from sidebar
        if 'market_filter' in st.session_state and st.session_state.market_filter != "All Markets":
            tracked_markets = monitor.get_tracked_markets()
            if tracked_markets:
                market_options = [
                    f"{m['question'][:40]}..." if len(m['question']) > 40 else m['question']
                    for m in tracked_markets
                ]
                try:
                    idx = market_options.index(st.session_state.market_filter)
                    selected_market_id = tracked_markets[idx]['market_id']
                    filtered_df = filtered_df[filtered_df['market_id'] == selected_market_id]
                except (ValueError, IndexError):
                    pass  # Market filter not found, show all

        st.markdown(f"**Showing {len(filtered_df)} trades**")
        st.divider()

        # Display trades in Bento Card Style
        for idx, row in filtered_df.head(50).iterrows():
            # Determine alert class based on risk
            alert_class = "bento-card"
            risk_indicator = ""

            if row['wallet_age_days'] is not None and row['wallet_age_days'] < 7:
                alert_class = "whale-alert"
                risk_indicator = "🔴 HIGH RISK"
            elif row['odds_cents'] < 10:
                alert_class = "whale-alert"
                risk_indicator = "🔴 LOW ODDS"
            elif row['bet_size'] >= 50000:
                alert_class = "whale-alert-mega"
                risk_indicator = "🟣 WHALE"

            # Create bento card for each trade
            st.markdown(f"""
            <div class="{alert_class}" style="margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="font-size: 1.1rem; font-weight: 700; color: #e2e8f0; font-family: 'Orbitron', sans-serif; flex: 1; margin-right: 1rem;">
                        {row['market_question'][:100]}
                    </div>
                    <span class="{'badge-yes' if row['outcome'] == 'YES' else 'badge-no'}">{row['outcome']}</span>
                </div>
                {f'<div style="color: #ef4444; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem;">{risk_indicator}</div>' if risk_indicator else ''}
                <div style="color: #64748b; font-size: 0.8rem; font-family: JetBrains Mono, monospace;">
                    Category: {row['market_category']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Trade details in columns
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown("**BET SIZE**")
                st.markdown(f"<div style='font-size: 1.3rem; font-weight: 700; color: #10b981; font-family: \"Orbitron\", monospace;'>${row['bet_size']:,.0f}</div>", unsafe_allow_html=True)
                potential = row['bet_size'] / row['odds'] if row['odds'] > 0 else 0
                st.caption(f"Potential: ${potential:,.0f}")

            with col2:
                st.markdown("**ENTRY PRICE**")
                price_color = "#ef4444" if row['odds_cents'] < 10 else "#10b981"
                st.markdown(f"<div style='font-size: 1.3rem; font-weight: 700; color: {price_color}; font-family: \"Orbitron\", monospace;'>{row['odds_cents']:.1f}¢</div>", unsafe_allow_html=True)
                st.caption("on the dollar")

            with col3:
                st.markdown("**WALLET**")
                st.code(row['wallet_address'], language=None)
                if row['wallet_age_days'] is not None:
                    age_color = "#ef4444" if row['wallet_age_days'] < 7 else "#64748b"
                    st.markdown(f"<div style='color: {age_color}; font-weight: 600;'>Age: {row['wallet_age_days']}d</div>", unsafe_allow_html=True)
                else:
                    st.caption("Age: Unknown", help="Could not determine wallet age")

            with col4:
                st.markdown("**ACTIONS**")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.link_button(
                        "📊",
                        f"https://polymarket.com/profile/{row['wallet_address']}",
                        help="View Polymarket profile",
                        use_container_width=True
                    )
                with col_b:
                    if st.button("🔍", key=f"track_{row['id']}", help="Track this wallet", use_container_width=True):
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
                            "📊 Profile",
                            f"https://polymarket.com/profile/{result['wallet_address']}"
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
                            "📊 Profile",
                            f"https://polymarket.com/profile/{wallet['wallet_address']}"
                        )
                    
                    with col4:
                        if st.button("🗑️", key=f"del_{wallet['wallet_address'][:8]}"):
                            monitor.remove_tracked_wallet(wallet['wallet_address'])
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No wallets being tracked. Add wallets in the 'Add Wallet' tab.")


# ============================================================================
# TAB 4: Market Tracker
# ============================================================================

with tab4:
    st.markdown("#### 🎯 Market Tracker")
    st.markdown("Browse and track specific Polymarket markets to monitor for suspicious activity.")

    # Get tracked markets
    tracked_markets = monitor.get_tracked_markets()

    col1, col2 = st.columns([2, 1])

    with col1:
        search_mode = st.radio(
            "Search for markets",
            ["Browse Active Markets", "Search by ID"],
            horizontal=True
        )

    with col2:
        if st.button("🔄 Refresh", key="refresh_markets"):
            st.rerun()

    st.divider()

    if search_mode == "Browse Active Markets":
        # Show active category selection
        if st.session_state.selected_categories:
            st.info(f"📂 Filtering by selected categories: {', '.join(st.session_state.selected_categories)}")
        else:
            st.warning("⚠️ No categories selected - showing all markets")

        # Fetch active markets from API
        with st.spinner("Loading markets..."):
            events = monitor.api.get_events(active=True, limit=100)

        if events:
            # Filter events by selected categories first
            filtered_events = []
            for event in events:
                # Extract event tags
                event_tags = []
                raw_tags = event.get("tags", [])
                for t in raw_tags:
                    if isinstance(t, str):
                        event_tags.append(t)
                    elif isinstance(t, dict):
                        tag_str = t.get('label') or t.get('name') or t.get('slug')
                        if tag_str:
                            event_tags.append(tag_str)

                # Check if event matches selected categories
                if st.session_state.selected_categories:
                    if any(cat in event_tags for cat in st.session_state.selected_categories):
                        filtered_events.append(event)
                else:
                    # No categories selected, show all
                    filtered_events.append(event)

            st.markdown(f"##### Found {len(filtered_events)} matching events")

            # Additional category filter within results
            all_categories = set()
            for event in filtered_events:
                raw_tags = event.get("tags", [])
                for t in raw_tags:
                    if isinstance(t, str):
                        all_categories.add(t)
                    elif isinstance(t, dict):
                        tag_str = t.get('label') or t.get('name') or t.get('slug')
                        if tag_str:
                            all_categories.add(tag_str)

            additional_filter = st.multiselect(
                "Further filter within results",
                sorted(list(all_categories)),
                default=[],
                help="Narrow down results within your selected categories"
            )

            st.divider()

            # Display markets
            markets_shown = 0
            for event in filtered_events:
                if markets_shown >= 20:  # Limit display
                    st.info(f"Showing first 20 markets. {len(filtered_events) - 20} more available.")
                    break

                markets = event.get("markets", [])
                if not markets:
                    continue

                # Apply additional filter if set
                if additional_filter:
                    event_tags = []
                    raw_tags = event.get("tags", [])
                    for t in raw_tags:
                        if isinstance(t, str):
                            event_tags.append(t)
                        elif isinstance(t, dict):
                            tag_str = t.get('label') or t.get('name') or t.get('slug')
                            if tag_str:
                                event_tags.append(tag_str)

                    if not any(cat in event_tags for cat in additional_filter):
                        continue

                for market in markets:
                    market_id = market.get("conditionId") or market.get("id")
                    if not market_id:
                        continue

                    question = market.get("question") or event.get("title", "Unknown")

                    # Get market tags - handle both string and dict tags
                    raw_tags = event.get("tags", [])
                    tag_strings = []
                    for t in raw_tags[:3]:  # Take first 3 tags
                        if isinstance(t, str):
                            tag_strings.append(t)
                        elif isinstance(t, dict):
                            tag_str = t.get('label') or t.get('name') or t.get('slug')
                            if tag_str:
                                tag_strings.append(tag_str)
                    event_tags_str = ", ".join(tag_strings)

                    with st.container():
                        col1, col2, col3 = st.columns([4, 1, 1])

                        with col1:
                            is_tracked = monitor.is_tracked_market(market_id)
                            icon = "✅ " if is_tracked else ""
                            st.markdown(f"**{icon}{question[:80]}{'...' if len(question) > 80 else ''}**")
                            st.caption(f"ID: {market_id[:16]}... | Category: {event_tags_str or 'General'}")

                        with col2:
                            st.link_button(
                                "🔗 View",
                                f"https://polymarket.com/event/{event.get('slug', market_id)}",
                                use_container_width=True
                            )

                        with col3:
                            if is_tracked:
                                if st.button("❌ Untrack", key=f"untrack_{market_id[:8]}", use_container_width=True):
                                    monitor.remove_tracked_market(market_id)
                                    st.success("Removed!")
                                    st.rerun()
                            else:
                                if st.button("➕ Track", key=f"track_mkt_{market_id[:8]}", use_container_width=True):
                                    monitor.add_tracked_market(
                                        market_id=market_id,
                                        question=question,
                                        category=event_tags_str or "General",
                                        end_date=event.get("endDate")
                                    )
                                    st.success("Added!")
                                    st.rerun()

                        st.divider()
                        markets_shown += 1
        else:
            st.warning("No active markets found")

    else:  # Search by ID
        market_id = st.text_input(
            "Market/Condition ID",
            placeholder="Enter market condition ID...",
            help="The unique identifier for the market"
        )

        if market_id and st.button("🔍 Search"):
            with st.spinner("Searching..."):
                market_data = monitor.api.get_market_by_id(market_id)

            if market_data:
                st.success("Market found!")

                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**Question:** {market_data.get('question', 'Unknown')}")
                    st.caption(f"ID: {market_id}")

                with col2:
                    if monitor.is_tracked_market(market_id):
                        if st.button("❌ Untrack", key="untrack_search"):
                            monitor.remove_tracked_market(market_id)
                            st.success("Removed!")
                            st.rerun()
                    else:
                        if st.button("➕ Track", key="track_search"):
                            monitor.add_tracked_market(
                                market_id=market_id,
                                question=market_data.get('question'),
                                category=market_data.get('tags', ['General'])[0] if market_data.get('tags') else 'General'
                            )
                            st.success("Added to tracking!")
                            st.rerun()
            else:
                st.error("Market not found")

    st.divider()

    # Show tracked markets
    st.markdown("#### 📌 Currently Tracking")

    if tracked_markets:
        st.markdown(f"##### {len(tracked_markets)} markets")

        for market in tracked_markets:
            with st.container():
                col1, col2, col3 = st.columns([4, 1, 1])

                with col1:
                    st.markdown(f"**{market.get('question', 'Unknown')}**")
                    st.caption(f"Category: {market.get('category', 'Unknown')} | Added: {market['added_at'][:10]}")

                with col2:
                    # Get trade count for this market
                    conn = monitor.db_path
                    import sqlite3
                    db = sqlite3.connect(conn)
                    cursor = db.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) FROM suspicious_trades WHERE market_id = ?",
                        (market['market_id'],)
                    )
                    count = cursor.fetchone()[0]
                    db.close()

                    st.metric("Alerts", count)

                with col3:
                    if st.button("🗑️ Remove", key=f"remove_{market['market_id'][:8]}"):
                        monitor.remove_tracked_market(market['market_id'])
                        st.rerun()

                st.divider()
    else:
        st.info("No markets being tracked. Browse markets above to start tracking.")


# ============================================================================
# TAB 5: Add Wallet
# ============================================================================

with tab5:
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
                            st.warning("Could not determine wallet age (may have minimal on-chain activity)")
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
# TAB 6: Statistics
# ============================================================================

with tab6:
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
