import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
from polymarket_monitor import PolymarketMonitor
import time
import os

# Page configuration
st.set_page_config(
    page_title="Polymarket Suspicious Activity Monitor",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .suspicious-alert {
        background-color: #ff4b4b;
        color: white;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .wallet-address {
        font-family: monospace;
        background-color: #f0f2f6;
        padding: 5px;
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'monitor' not in st.session_state:
    st.session_state.monitor = None
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None
if 'telegram_enabled' not in st.session_state:
    st.session_state.telegram_enabled = False

# Sidebar configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # Database path
    db_path = st.text_input("Database Path", value="polymarket_monitor.db")
    
    # API Key configuration
    st.divider()
    st.subheader("🔑 Polymarket API")
    
    api_key_enabled = st.checkbox("Use API Key (Recommended)", value=False, help="Builder API key for higher rate limits")
    if api_key_enabled:
        api_key = st.text_input(
            "Builder API Key", 
            type="password",
            help="Get from Polymarket Builder dashboard"
        )
        if api_key:
            st.success("✅ API key configured")
        else:
            st.warning("⚠️ Enter your API key above")
    else:
        api_key = None
        st.info("💡 Using public API (rate limited)")
    
    st.divider()
    
    # Detection thresholds
    st.subheader("🎯 Detection Filters")
    
    st.markdown("**Wallet Age**")
    wallet_age_enabled = st.checkbox("Check Wallet Age", value=True)
    if wallet_age_enabled:
        wallet_age_days = st.number_input("Max Wallet Age (days)", min_value=1, max_value=365, value=30, step=1)
    else:
        wallet_age_days = 999999  # Effectively disabled
    
    st.markdown("**Bet Size**")
    bet_size_enabled = st.checkbox("Check Bet Size", value=True)
    if bet_size_enabled:
        min_bet_size = st.number_input("Min Bet Size ($)", min_value=0, max_value=1000000, value=10000, step=1000)
    else:
        min_bet_size = 0  # Effectively disabled
    
    st.markdown("**Market Odds**")
    odds_enabled = st.checkbox("Check Market Odds", value=True)
    if odds_enabled:
        max_odds = st.number_input("Max Odds (%)", min_value=1, max_value=100, value=20, step=1) / 100
    else:
        max_odds = 1.0  # Effectively disabled
    
    st.markdown("**Position Type**")
    position_filter_enabled = st.checkbox("Filter by Position (YES/NO)", value=False)
    if position_filter_enabled:
        position_filter = st.selectbox("Show only:", ["YES", "NO", "Both"])
    else:
        position_filter = "Both"
    
    st.divider()
    
    # Settings Management
    st.subheader("💾 Settings Management")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Current Settings", use_container_width=True):
            settings = {
                'wallet_age_enabled': wallet_age_enabled,
                'wallet_age_days': wallet_age_days if wallet_age_enabled else 30,
                'bet_size_enabled': bet_size_enabled,
                'min_bet_size': min_bet_size if bet_size_enabled else 10000,
                'odds_enabled': odds_enabled,
                'max_odds': max_odds if odds_enabled else 0.20,
                'position_filter': position_filter if position_filter_enabled else "Both"
            }
            st.session_state.saved_settings = settings
            st.success("✅ Settings saved!")
    
    with col2:
        if st.button("Reset to Defaults", use_container_width=True):
            st.session_state.saved_settings = None
            st.info("ℹ️ Reload page to reset")
    
    # Display current filter summary
    st.markdown("### 📋 Active Filters:")
    if wallet_age_enabled:
        st.caption(f"✅ Wallet age < {wallet_age_days} days")
    else:
        st.caption("❌ Wallet age: Disabled")
    
    if bet_size_enabled:
        st.caption(f"✅ Bet size > ${min_bet_size:,}")
    else:
        st.caption("❌ Bet size: Disabled")
    
    if odds_enabled:
        st.caption(f"✅ Odds < {max_odds*100:.0f}%")
    else:
        st.caption("❌ Odds: Disabled")
    
    if position_filter_enabled:
        st.caption(f"✅ Position: {position_filter}")
    else:
        st.caption("❌ Position filter: Disabled")
    
    st.divider()
    
    # Telegram configuration
    st.subheader("📱 Telegram Alerts")
    telegram_enabled = st.checkbox("Enable Telegram Alerts", value=st.session_state.telegram_enabled)
    
    if telegram_enabled:
        telegram_token = st.text_input("Bot Token", type="password", help="Get from @BotFather")
        telegram_chat_id = st.text_input("Chat ID", help="Your Telegram chat ID")
        
        if st.button("Test Telegram Connection"):
            if telegram_token and telegram_chat_id:
                try:
                    import requests
                    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                    payload = {
                        "chat_id": telegram_chat_id,
                        "text": "🎉 Telegram connection successful! You will receive alerts here."
                    }
                    response = requests.post(url, json=payload)
                    if response.status_code == 200:
                        st.success("✅ Telegram test successful!")
                        st.session_state.telegram_enabled = True
                    else:
                        st.error("❌ Failed to send test message")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
            else:
                st.warning("Please enter both Bot Token and Chat ID")
    else:
        telegram_token = None
        telegram_chat_id = None
    
    st.divider()
    
    # Initialize/Update monitor
    if st.button("🔄 Initialize Monitor", type="primary"):
        st.session_state.monitor = PolymarketMonitor(
            db_path=db_path,
            telegram_token=telegram_token if telegram_enabled else None,
            telegram_chat_id=telegram_chat_id if telegram_enabled else None,
            api_key=api_key if api_key_enabled else None
        )
        # Update thresholds
        st.session_state.monitor.WALLET_AGE_DAYS = wallet_age_days
        st.session_state.monitor.MIN_BET_SIZE = min_bet_size
        st.session_state.monitor.MAX_ODDS = max_odds
        st.success("✅ Monitor initialized!")
        if api_key:
            st.info("🚀 Using authenticated API - better rate limits!")
    
    st.divider()
    
    # Connection Test
    st.subheader("🔌 Connection Test")
    if st.button("Test API Connection", use_container_width=True):
        if st.session_state.monitor:
            with st.spinner("Testing connection..."):
                test_results = st.session_state.monitor.test_connection()
                
                if test_results.get("gamma_api"):
                    st.success(f"✅ Gamma API: OK (Status {test_results.get('gamma_status')})")
                else:
                    st.error(f"❌ Gamma API: Failed (Status {test_results.get('gamma_status')})")
                
                if test_results.get("clob_api"):
                    st.success(f"✅ CLOB API: OK (Status {test_results.get('clob_status')})")
                else:
                    if test_results.get("clob_status"):
                        st.warning(f"⚠️ CLOB API: Status {test_results.get('clob_status')}")
                    else:
                        st.info("ℹ️ CLOB API: Not tested")
                
                # Show details
                if test_results.get("details"):
                    for detail in test_results["details"]:
                        st.caption(detail)
                
                if test_results.get("error"):
                    st.error(f"Error: {test_results['error']}")
                    
                # Show fix suggestions
                if not test_results.get("gamma_api"):
                    st.warning("💡 Gamma API failed. This is the main data source. Check:")
                    st.caption("• Internet connection")
                    st.caption("• Polymarket API status")
                    st.caption("• Try again in a few minutes")
        else:
            st.warning("Initialize monitor first")
    
    st.divider()
    
    # Scan controls
    st.subheader("🔍 Scanning")
    auto_refresh = st.checkbox("Auto Refresh (30s)", value=False)
    
    if st.button("🚀 Run Scan Now", type="primary"):
        if st.session_state.monitor:
            with st.spinner("Scanning markets..."):
                st.session_state.monitor.scan_markets()
                st.session_state.last_scan_time = datetime.now()
                st.success("✅ Scan completed!")
                st.rerun()
        else:
            st.warning("Please initialize monitor first")
    
    if st.session_state.last_scan_time:
        st.caption(f"Last scan: {st.session_state.last_scan_time.strftime('%Y-%m-%d %H:%M:%S')}")

# Main content
st.title("🚨 Polymarket Suspicious Activity Monitor")
st.markdown("Real-time detection of suspicious betting patterns on Polymarket")

# Check if monitor is initialized
if st.session_state.monitor is None:
    st.warning("⚠️ Please initialize the monitor in the sidebar to begin")
    st.info("""
    **Quick Start:**
    1. Click '🔄 Initialize Monitor' in the sidebar
    2. Configure your detection thresholds
    3. Optionally set up Telegram alerts
    4. Click '🚀 Run Scan Now' to start detecting
    """)
    st.stop()

# Get data from database
monitor = st.session_state.monitor
suspicious_trades = monitor.get_suspicious_trades(limit=1000)

# Convert to DataFrame
if suspicious_trades:
    df = pd.DataFrame(suspicious_trades)
    df['detected_at'] = pd.to_datetime(df['detected_at'])
    df['bet_size'] = df['bet_size'].astype(float)
    df['odds'] = df['odds'].astype(float) * 100  # Convert to percentage
else:
    df = pd.DataFrame()

# Key Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_suspicious = len(df) if not df.empty else 0
    st.metric("🔍 Total Suspicious Trades", total_suspicious)

with col2:
    unique_wallets = df['wallet_address'].nunique() if not df.empty else 0
    st.metric("👛 Unique Wallets", unique_wallets)

with col3:
    total_volume = df['bet_size'].sum() if not df.empty else 0
    st.metric("💰 Total Volume", f"${total_volume:,.0f}")

with col4:
    alerted = df['alerted'].sum() if not df.empty else 0
    st.metric("📱 Alerts Sent", alerted)

st.divider()

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔍 Recent Activity", "👛 Wallet Analysis", "📈 Statistics"])

with tab1:
    if df.empty:
        st.info("No suspicious activity detected yet. Run a scan to start monitoring.")
    else:
        # Time series of suspicious bets
        st.subheader("Suspicious Activity Over Time")
        
        # Group by date
        df['date'] = df['detected_at'].dt.date
        daily_counts = df.groupby('date').size().reset_index(name='count')
        daily_volume = df.groupby('date')['bet_size'].sum().reset_index(name='volume')
        
        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Bar(
            x=daily_counts['date'],
            y=daily_counts['count'],
            name='Suspicious Trades',
            marker_color='#ff4b4b'
        ))
        fig_timeline.update_layout(
            title="Daily Suspicious Trades",
            xaxis_title="Date",
            yaxis_title="Count",
            height=300
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Top markets with suspicious activity
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Markets by Activity")
            market_counts = df['market_question'].value_counts().head(10)
            fig_markets = px.bar(
                x=market_counts.values,
                y=market_counts.index,
                orientation='h',
                labels={'x': 'Suspicious Trades', 'y': 'Market'},
                color=market_counts.values,
                color_continuous_scale='Reds'
            )
            fig_markets.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_markets, use_container_width=True)
        
        with col2:
            st.subheader("Bet Size Distribution")
            fig_size = px.histogram(
                df,
                x='bet_size',
                nbins=30,
                labels={'bet_size': 'Bet Size ($)', 'count': 'Frequency'},
                color_discrete_sequence=['#ff4b4b']
            )
            fig_size.update_layout(height=400)
            st.plotly_chart(fig_size, use_container_width=True)

with tab2:
    st.subheader("🔍 Recent Suspicious Activity")
    
    if df.empty:
        st.info("No suspicious activity detected yet. Run a scan to start monitoring.")
    else:
        # Advanced Filters
        st.markdown("### 🎛️ Filter Results")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            min_size_filter = st.number_input("Min Bet Size ($)", value=0, step=1000, key="filter_bet_size")
        with col2:
            max_odds_filter = st.slider("Max Odds %", 0, 100, 100, key="filter_odds")
        with col3:
            position_type_filter = st.selectbox("Position", ["All", "YES", "NO"], key="filter_position")
        with col4:
            show_alerted_only = st.checkbox("Alerted Only", value=False, key="filter_alerted")
        
        # Apply filters
        filtered_df = df[df['bet_size'] >= min_size_filter]
        filtered_df = filtered_df[filtered_df['odds'] <= max_odds_filter]
        if position_type_filter != "All":
            filtered_df = filtered_df[filtered_df['outcome'] == position_type_filter]
        if show_alerted_only:
            filtered_df = filtered_df[filtered_df['alerted'] == 1]
        
        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Filtered Results", len(filtered_df))
        with col2:
            yes_count = len(filtered_df[filtered_df['outcome'] == 'YES'])
            st.metric("YES Positions", yes_count)
        with col3:
            no_count = len(filtered_df[filtered_df['outcome'] == 'NO'])
            st.metric("NO Positions", no_count)
        with col4:
            avg_bet = filtered_df['bet_size'].mean() if len(filtered_df) > 0 else 0
            st.metric("Avg Bet Size", f"${avg_bet:,.0f}")
        
        st.divider()
        
        # Display recent trades
        st.markdown(f"### 📋 Showing {len(filtered_df)} suspicious trades")
        
        for idx, row in filtered_df.head(50).iterrows():
            with st.container():
                # Header row
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{row['market_question']}**")
                with col2:
                    # Position badge
                    if row['outcome'] == 'YES':
                        st.markdown("🟢 **YES Position**")
                    else:
                        st.markdown("🔴 **NO Position**")
                
                st.caption(f"📂 Category: {row['market_category']}")
                
                # Details row
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown("**💰 Bet Details**")
                    st.write(f"Size: **${row['bet_size']:,.0f}**")
                    st.write(f"Odds: **{row['odds']:.1f}%**")
                    # Calculate potential profit
                    potential_profit = (row['bet_size'] / (row['odds']/100)) - row['bet_size']
                    st.caption(f"Potential Profit: ${potential_profit:,.0f}")
                
                with col2:
                    st.markdown("**👛 Wallet Info**")
                    st.code(f"{row['wallet_address'][:8]}...{row['wallet_address'][-6:]}", language=None)
                    wallet_age_text = f"{row['wallet_age_days']} days old" if row['wallet_age_days'] else "Age unknown"
                    
                    # Color code wallet age
                    if row['wallet_age_days'] and row['wallet_age_days'] < 7:
                        st.error(f"🚨 {wallet_age_text}")
                    elif row['wallet_age_days'] and row['wallet_age_days'] < 30:
                        st.warning(f"⚠️ {wallet_age_text}")
                    else:
                        st.info(f"ℹ️ {wallet_age_text}")
                
                with col3:
                    st.markdown("**⏰ Timing**")
                    st.write(f"Detected: {row['detected_at'].strftime('%m/%d %H:%M')}")
                    if row['timestamp']:
                        st.caption(f"Trade: {row['timestamp']}")
                
                with col4:
                    st.markdown("**🔔 Status**")
                    if row['alerted'] == 1:
                        st.success("✅ Alerted")
                    else:
                        st.warning("⏳ Pending")
                    
                    # Alert button for pending
                    if row['alerted'] == 0 and telegram_enabled:
                        if st.button("Send Alert Now", key=f"alert_{row['id']}"):
                            suspicious_data = row.to_dict()
                            if monitor.send_telegram_alert(suspicious_data):
                                st.success("Alert sent!")
                                st.rerun()
                
                # Action buttons
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                with col1:
                    if st.button("🔍 Deep Analysis", key=f"analyze_{row['id']}", use_container_width=True):
                        st.session_state.selected_wallet = row['wallet_address']
                        st.rerun()
                with col2:
                    polygonscan_url = f"https://polygonscan.com/address/{row['wallet_address']}"
                    st.link_button("📊 Polygonscan", polygonscan_url, use_container_width=True)
                with col3:
                    arkham_url = f"https://platform.arkhamintelligence.com/explorer/address/{row['wallet_address']}"
                    st.link_button("🔎 Arkham", arkham_url, use_container_width=True)
                with col4:
                    # Copy wallet address
                    if st.button("📋 Copy Address", key=f"copy_{row['id']}", use_container_width=True):
                        st.code(row['wallet_address'], language=None)
                
                st.divider()

with tab3:
    st.subheader("👛 Wallet Deep Dive")
    
    # Quick Wallet Lookup Tool
    st.markdown("### 🔎 Quick Wallet Lookup")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        manual_wallet = st.text_input(
            "Enter Wallet Address to Check",
            placeholder="0x1234...",
            help="Paste any Polygon wallet address to analyze"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        lookup_button = st.button("🔍 Lookup", type="primary", use_container_width=True)
    
    if lookup_button and manual_wallet:
        if manual_wallet.startswith("0x") and len(manual_wallet) == 42:
            with st.spinner("Checking wallet..."):
                # Check if wallet exists in our database
                wallet_stats = monitor.get_wallet_stats(manual_wallet)
                
                if wallet_stats:
                    st.success(f"✅ Found in database!")
                else:
                    st.info("ℹ️ Wallet not in database. Checking blockchain...")
                    # You could add live blockchain lookup here
                
                # Display wallet info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Wallet Address", "")
                    st.code(manual_wallet, language=None)
                with col2:
                    polygonscan_url = f"https://polygonscan.com/address/{manual_wallet}"
                    st.link_button("📊 View on Polygonscan", polygonscan_url, use_container_width=True)
                with col3:
                    arkham_url = f"https://platform.arkhamintelligence.com/explorer/address/{manual_wallet}"
                    st.link_button("🔎 View on Arkham", arkham_url, use_container_width=True)
        else:
            st.error("❌ Invalid wallet address. Must start with 0x and be 42 characters long.")
    
    st.divider()
    
    # Wallet selector from database
    st.markdown("### 📊 Database Analysis")
    
    if not df.empty:
        unique_wallets_list = df['wallet_address'].unique().tolist()
        
        # Check if we have a selected wallet from previous tab
        default_wallet = None
        if 'selected_wallet' in st.session_state and st.session_state.selected_wallet in unique_wallets_list:
            default_idx = unique_wallets_list.index(st.session_state.selected_wallet)
            default_wallet = unique_wallets_list[default_idx]
        
        selected_wallet = st.selectbox(
            "Select Wallet from Database",
            unique_wallets_list,
            index=unique_wallets_list.index(default_wallet) if default_wallet else 0,
            format_func=lambda x: f"{x[:10]}...{x[-8:]}"
        )
        
        if selected_wallet:
            # Get wallet stats
            wallet_stats = monitor.get_wallet_stats(selected_wallet)
            
            if wallet_stats:
                # Display comprehensive stats
                st.markdown("#### 📈 Wallet Statistics")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("Total Bets", wallet_stats['total_bets'])
                with col2:
                    st.metric("Total Volume", f"${wallet_stats['total_volume']:,.0f}")
                with col3:
                    st.metric("Suspicious Bets", wallet_stats['suspicious_bets'])
                with col4:
                    st.metric("First Seen", wallet_stats['first_seen'][:10])
                with col5:
                    # Calculate days active
                    first_seen = pd.to_datetime(wallet_stats['first_seen'])
                    last_updated = pd.to_datetime(wallet_stats['last_updated'])
                    days_active = (last_updated - first_seen).days
                    st.metric("Days Active", days_active)
                
                st.divider()
                
                # Wallet trades breakdown
                st.markdown("#### 📋 Trade Breakdown")
                
                wallet_trades = wallet_stats['trades']
                if wallet_trades:
                    trades_df = pd.DataFrame(wallet_trades)
                    
                    # Position analysis
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        yes_trades = len(trades_df[trades_df['outcome'] == 'YES'])
                        no_trades = len(trades_df[trades_df['outcome'] == 'NO'])
                        
                        st.markdown("**Position Distribution**")
                        fig_positions = go.Figure(data=[
                            go.Pie(
                                labels=['YES', 'NO'],
                                values=[yes_trades, no_trades],
                                marker=dict(colors=['#00cc00', '#ff4444']),
                                hole=0.3
                            )
                        ])
                        fig_positions.update_layout(height=250)
                        st.plotly_chart(fig_positions, use_container_width=True)
                    
                    with col2:
                        st.markdown("**Bet Size Summary**")
                        st.write(f"**Average:** ${trades_df['bet_size'].mean():,.0f}")
                        st.write(f"**Median:** ${trades_df['bet_size'].median():,.0f}")
                        st.write(f"**Largest:** ${trades_df['bet_size'].max():,.0f}")
                        st.write(f"**Smallest:** ${trades_df['bet_size'].min():,.0f}")
                        st.write(f"**Total:** ${trades_df['bet_size'].sum():,.0f}")
                    
                    st.divider()
                    
                    # Detailed trades table
                    st.markdown("#### 🗂️ All Suspicious Trades")
                    
                    # Add position colors to display
                    display_df = trades_df[[
                        'market_question', 'outcome', 'bet_size', 'odds', 
                        'timestamp', 'alerted'
                    ]].copy()
                    
                    # Format columns
                    display_df['bet_size'] = display_df['bet_size'].apply(lambda x: f"${x:,.0f}")
                    display_df['odds'] = display_df['odds'].apply(lambda x: f"{x:.1f}%")
                    display_df['alerted'] = display_df['alerted'].apply(lambda x: '✅ Yes' if x == 1 else '⏳ No')
                    
                    # Rename columns for display
                    display_df.columns = ['Market', 'Position', 'Bet Size', 'Odds', 'Time', 'Alerted']
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Position": st.column_config.TextColumn(
                                "Position",
                                help="YES or NO position"
                            )
                        }
                    )
                    
                    st.divider()
                    
                    # Timeline chart
                    st.markdown("#### 📅 Betting Timeline")
                    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
                    
                    # Create color mapping for positions
                    trades_df['color'] = trades_df['outcome'].map({'YES': 'green', 'NO': 'red'})
                    
                    fig_timeline = px.scatter(
                        trades_df,
                        x='timestamp',
                        y='bet_size',
                        color='outcome',
                        size='bet_size',
                        hover_data=['market_question', 'odds'],
                        title="Wallet Betting Activity Over Time",
                        labels={'bet_size': 'Bet Size ($)', 'timestamp': 'Date'},
                        color_discrete_map={'YES': '#00cc00', 'NO': '#ff4444'}
                    )
                    fig_timeline.update_layout(height=400)
                    st.plotly_chart(fig_timeline, use_container_width=True)
                
                st.divider()
                
                # External links
                st.markdown("#### 🔗 External Analysis")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    polygonscan_url = f"https://polygonscan.com/address/{selected_wallet}"
                    st.link_button("📊 Polygonscan (Full History)", polygonscan_url, use_container_width=True)
                
                with col2:
                    arkham_url = f"https://platform.arkhamintelligence.com/explorer/address/{selected_wallet}"
                    st.link_button("🔎 Arkham Intelligence", arkham_url, use_container_width=True)
                
                with col3:
                    # Copy full wallet address
                    st.code(selected_wallet, language=None)
    else:
        st.info("No wallets to analyze yet. Run a scan to detect suspicious activity.")

with tab4:
    st.subheader("📈 Statistics & Insights")
    
    if df.empty:
        st.info("No data available yet. Run a scan to start collecting statistics.")
    else:
        # Position Overview
        st.markdown("### 🎯 Position Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        yes_bets = df[df['outcome'] == 'YES']
        no_bets = df[df['outcome'] == 'NO']
        
        with col1:
            st.metric("Total YES Positions", len(yes_bets))
            st.caption(f"Total Volume: ${yes_bets['bet_size'].sum():,.0f}")
            st.caption(f"Avg Bet: ${yes_bets['bet_size'].mean():,.0f}" if len(yes_bets) > 0 else "N/A")
        
        with col2:
            st.metric("Total NO Positions", len(no_bets))
            st.caption(f"Total Volume: ${no_bets['bet_size'].sum():,.0f}")
            st.caption(f"Avg Bet: ${no_bets['bet_size'].mean():,.0f}" if len(no_bets) > 0 else "N/A")
        
        with col3:
            yes_pct = (len(yes_bets) / len(df) * 100) if len(df) > 0 else 0
            st.metric("YES Preference", f"{yes_pct:.1f}%")
            st.caption("Percentage of bets on YES")
        
        st.divider()
        
        # Wallet Age Distribution
        st.markdown("### 👛 Wallet Age Distribution")
        
        # Filter out unknown ages
        known_ages = df[df['wallet_age_days'].notna()]
        
        if len(known_ages) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_age_hist = px.histogram(
                    known_ages,
                    x='wallet_age_days',
                    nbins=20,
                    title="Wallet Age Distribution (Days)",
                    labels={'wallet_age_days': 'Wallet Age (Days)', 'count': 'Frequency'},
                    color_discrete_sequence=['#ff4b4b']
                )
                fig_age_hist.add_vline(x=7, line_dash="dash", line_color="orange", 
                                      annotation_text="7 days")
                fig_age_hist.add_vline(x=30, line_dash="dash", line_color="red",
                                      annotation_text="30 days")
                st.plotly_chart(fig_age_hist, use_container_width=True)
            
            with col2:
                # Age categories
                very_fresh = len(known_ages[known_ages['wallet_age_days'] < 7])
                fresh = len(known_ages[(known_ages['wallet_age_days'] >= 7) & (known_ages['wallet_age_days'] < 30)])
                older = len(known_ages[known_ages['wallet_age_days'] >= 30])
                
                age_categories = pd.DataFrame({
                    'Category': ['< 7 days\n(Very Fresh)', '7-30 days\n(Fresh)', '> 30 days\n(Older)'],
                    'Count': [very_fresh, fresh, older]
                })
                
                fig_age_cat = px.bar(
                    age_categories,
                    x='Category',
                    y='Count',
                    title="Wallet Age Categories",
                    color='Count',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_age_cat, use_container_width=True)
        else:
            st.warning("No wallet age data available yet.")
        
        st.divider()
        
        # Summary statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 Bet Size Statistics")
            st.write(f"**Mean:** ${df['bet_size'].mean():,.0f}")
            st.write(f"**Median:** ${df['bet_size'].median():,.0f}")
            st.write(f"**Min:** ${df['bet_size'].min():,.0f}")
            st.write(f"**Max:** ${df['bet_size'].max():,.0f}")
            st.write(f"**Total Volume:** ${df['bet_size'].sum():,.0f}")
        
        with col2:
            st.markdown("### 🎲 Odds Statistics")
            st.write(f"**Mean:** {df['odds'].mean():.2f}%")
            st.write(f"**Median:** {df['odds'].median():.2f}%")
            st.write(f"**Min:** {df['odds'].min():.2f}%")
            st.write(f"**Max:** {df['odds'].max():.2f}%")
            st.write(f"**Avg for YES:** {yes_bets['odds'].mean():.2f}%" if len(yes_bets) > 0 else "N/A")
            st.write(f"**Avg for NO:** {no_bets['odds'].mean():.2f}%" if len(no_bets) > 0 else "N/A")
        
        st.divider()
        
        # Category breakdown
        st.markdown("### 📂 Activity by Category")
        category_stats = df['market_category'].value_counts()
        
        fig_categories = px.pie(
            values=category_stats.values,
            names=category_stats.index,
            title="Suspicious Bets by Market Category",
            hole=0.3
        )
        st.plotly_chart(fig_categories, use_container_width=True)
        
        st.divider()
        
        # Outcome vs Bet Size
        st.markdown("### 📊 Position vs Bet Size Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            outcome_counts = df['outcome'].value_counts()
            fig_outcomes = px.bar(
                x=outcome_counts.index,
                y=outcome_counts.values,
                labels={'x': 'Position', 'y': 'Number of Bets'},
                title="Bets by Position Type",
                color=outcome_counts.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_outcomes, use_container_width=True)
        
        with col2:
            # Average bet size by outcome
            avg_by_outcome = df.groupby('outcome')['bet_size'].mean()
            fig_avg = px.bar(
                x=avg_by_outcome.index,
                y=avg_by_outcome.values,
                labels={'x': 'Position', 'y': 'Avg Bet Size ($)'},
                title="Average Bet Size by Position",
                color=avg_by_outcome.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_avg, use_container_width=True)
        
        st.divider()
        
        # Advanced: Bet size vs Odds correlation
        st.markdown("### 🔬 Bet Size vs Odds Correlation")
        
        fig_scatter = px.scatter(
            df,
            x='odds',
            y='bet_size',
            color='outcome',
            size='bet_size',
            hover_data=['market_question', 'wallet_address'],
            title="Relationship Between Bet Size and Market Odds",
            labels={'odds': 'Market Odds (%)', 'bet_size': 'Bet Size ($)'},
            color_discrete_map={'YES': '#00cc00', 'NO': '#ff4444'}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        st.caption("💡 Lower odds + larger bets = higher suspicion of insider knowledge")

# Auto refresh
if auto_refresh:
    time.sleep(30)
    st.rerun()

# Footer
st.divider()
st.caption("🚨 Polymarket Suspicious Activity Monitor | Built with Streamlit")
st.caption("Data is stored locally in SQLite database")
