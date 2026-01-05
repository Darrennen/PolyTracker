"""
PolyTracker Dashboard - Streamlit Web UI
Deploy this on Streamlit Cloud for viewing data.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from database import Database
from polymarket_monitor import PolymarketMonitor

# Page configuration
st.set_page_config(
    page_title="PolyTracker - Suspicious Activity Monitor",
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
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize database connection
@st.cache_resource
def get_database():
    """Get cached database connection"""
    return Database()


@st.cache_resource
def get_monitor():
    """Get cached monitor instance"""
    return PolymarketMonitor()


# Get instances
db = get_database()
monitor = get_monitor()

# Sidebar
with st.sidebar:
    st.title("⚙️ Configuration")

    # Connection status
    st.subheader("📡 Status")
    db_type = "PostgreSQL" if os.getenv("DATABASE_URL") else "SQLite (Local)"
    st.info(f"Database: {db_type}")

    st.divider()

    # Detection thresholds display
    st.subheader("🎯 Detection Thresholds")
    st.caption(f"Wallet Age: < {monitor.WALLET_AGE_DAYS} days")
    st.caption(f"Bet Size: > ${monitor.MIN_BET_SIZE:,.0f}")
    st.caption(f"Max Odds: < {monitor.MAX_ODDS*100:.0f}%")

    st.divider()

    # Manual wallet monitoring
    st.subheader("👛 Monitor Wallet")

    new_wallet = st.text_input("Wallet Address", placeholder="0x...")
    wallet_label = st.text_input("Label (optional)", placeholder="Whale #1")
    wallet_notes = st.text_area("Notes (optional)", placeholder="Why monitoring...")

    if st.button("➕ Add to Watchlist", type="primary", use_container_width=True):
        if new_wallet and new_wallet.startswith("0x") and len(new_wallet) == 42:
            if monitor.add_monitored_wallet(new_wallet, wallet_label, wallet_notes):
                st.success(f"✅ Added {new_wallet[:10]}...")
                st.rerun()
            else:
                st.error("Failed to add wallet")
        else:
            st.error("Invalid wallet address")

    # Show monitored wallets
    monitored = monitor.get_monitored_wallets()
    if monitored:
        st.caption(f"Monitoring {len(monitored)} wallets")
        for w in monitored[:5]:
            col1, col2 = st.columns([3, 1])
            with col1:
                label = w.get('label') or w['wallet_address'][:10]
                st.caption(f"• {label}")
            with col2:
                if st.button("❌", key=f"remove_{w['wallet_address']}", help="Remove"):
                    monitor.remove_monitored_wallet(w['wallet_address'])
                    st.rerun()

    st.divider()

    # Manual scan (only if running locally with write access)
    if not os.getenv("DATABASE_URL"):
        st.subheader("🔍 Manual Scan")
        if st.button("🚀 Run Scan Now", type="primary", use_container_width=True):
            with st.spinner("Scanning markets..."):
                count = monitor.scan_markets()
                st.success(f"Found {count} suspicious trades")
                st.rerun()

    # Refresh button
    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Main content
st.title("🚨 PolyTracker")
st.markdown("Suspicious betting activity monitor for Polymarket")

# Get data
suspicious_trades = db.get_suspicious_trades(limit=1000)

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
    st.metric("🔍 Suspicious Trades", total_suspicious)

with col2:
    unique_wallets = df['wallet_address'].nunique() if not df.empty else 0
    st.metric("👛 Unique Wallets", unique_wallets)

with col3:
    total_volume = df['bet_size'].sum() if not df.empty else 0
    st.metric("💰 Total Volume", f"${total_volume:,.0f}")

with col4:
    alerted = df['alerted'].sum() if not df.empty and 'alerted' in df.columns else 0
    st.metric("📱 Alerts Sent", int(alerted))

st.divider()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔍 Recent Activity", "👛 Wallet Analysis", "📈 Statistics"])

with tab1:
    if df.empty:
        st.info("No suspicious activity detected yet. Data will appear here once the worker detects trades.")
    else:
        # Time series
        st.subheader("Suspicious Activity Over Time")

        df['date'] = df['detected_at'].dt.date
        daily_counts = df.groupby('date').size().reset_index(name='count')

        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Bar(
            x=daily_counts['date'],
            y=daily_counts['count'],
            name='Suspicious Trades',
            marker_color='#ff4b4b'
        ))
        fig_timeline.update_layout(
            xaxis_title="Date",
            yaxis_title="Count",
            height=300
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # Top markets
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top Markets")
            market_counts = df['market_question'].value_counts().head(10)
            fig_markets = px.bar(
                x=market_counts.values,
                y=[q[:40] + "..." if len(q) > 40 else q for q in market_counts.index],
                orientation='h',
                labels={'x': 'Count', 'y': 'Market'},
                color=market_counts.values,
                color_continuous_scale='Reds'
            )
            fig_markets.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_markets, use_container_width=True)

        with col2:
            st.subheader("Bet Size Distribution")
            fig_size = px.histogram(
                df, x='bet_size', nbins=30,
                labels={'bet_size': 'Bet Size ($)'},
                color_discrete_sequence=['#ff4b4b']
            )
            fig_size.update_layout(height=400)
            st.plotly_chart(fig_size, use_container_width=True)

with tab2:
    st.subheader("🔍 Recent Suspicious Activity")

    if df.empty:
        st.info("No suspicious activity detected yet.")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            min_size = st.number_input("Min Bet Size ($)", value=0, step=1000)
        with col2:
            position_filter = st.selectbox("Position", ["All", "YES", "NO"])
        with col3:
            max_results = st.selectbox("Show", [25, 50, 100, 200], index=1)

        # Apply filters
        filtered_df = df[df['bet_size'] >= min_size]
        if position_filter != "All":
            filtered_df = filtered_df[filtered_df['outcome'] == position_filter]

        st.caption(f"Showing {min(len(filtered_df), max_results)} of {len(filtered_df)} trades")

        # Display trades
        for idx, row in filtered_df.head(max_results).iterrows():
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.markdown(f"**{row['market_question'][:80]}...**" if len(row['market_question']) > 80 else f"**{row['market_question']}**")

                with col2:
                    if row['outcome'] == 'YES':
                        st.markdown("🟢 **YES**")
                    else:
                        st.markdown("🔴 **NO**")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.caption("💰 Bet Size")
                    st.write(f"**${row['bet_size']:,.0f}**")

                with col2:
                    st.caption("🎲 Odds")
                    st.write(f"**{row['odds']:.1f}%**")

                with col3:
                    st.caption("👛 Wallet")
                    wallet_short = f"{row['wallet_address'][:6]}...{row['wallet_address'][-4:]}"
                    st.code(wallet_short)

                with col4:
                    st.caption("📅 Detected")
                    st.write(row['detected_at'].strftime('%m/%d %H:%M'))

                # Action buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.link_button("📊 Polygonscan", f"https://polygonscan.com/address/{row['wallet_address']}", use_container_width=True)
                with col2:
                    st.link_button("🔎 Arkham", f"https://platform.arkhamintelligence.com/explorer/address/{row['wallet_address']}", use_container_width=True)
                with col3:
                    if st.button("📋 Copy", key=f"copy_{idx}", use_container_width=True):
                        st.code(row['wallet_address'])

                st.divider()

with tab3:
    st.subheader("👛 Wallet Deep Dive")

    # Wallet selector
    if not df.empty:
        wallets = df['wallet_address'].unique().tolist()

        # Add monitored wallets
        for w in monitored:
            if w['wallet_address'] not in wallets:
                wallets.insert(0, w['wallet_address'])

        selected = st.selectbox(
            "Select Wallet",
            wallets,
            format_func=lambda x: f"{x[:10]}...{x[-6:]}"
        )

        if selected:
            stats = db.get_wallet_stats(selected)

            if stats:
                # Stats row
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Bets", stats.get('total_bets', 0))
                with col2:
                    st.metric("Total Volume", f"${stats.get('total_volume', 0):,.0f}")
                with col3:
                    st.metric("Suspicious", stats.get('suspicious_bets', 0))
                with col4:
                    first_seen = stats.get('first_seen', '')[:10] if stats.get('first_seen') else 'Unknown'
                    st.metric("First Seen", first_seen)

                st.divider()

                # Trades
                trades = stats.get('trades', [])
                if trades:
                    trades_df = pd.DataFrame(trades)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Position Distribution**")
                        yes_count = len(trades_df[trades_df['outcome'] == 'YES'])
                        no_count = len(trades_df[trades_df['outcome'] == 'NO'])
                        fig = go.Figure(data=[go.Pie(
                            labels=['YES', 'NO'],
                            values=[yes_count, no_count],
                            marker=dict(colors=['#00cc00', '#ff4444']),
                            hole=0.4
                        )])
                        fig.update_layout(height=250, showlegend=True)
                        st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        st.markdown("**Bet Size Summary**")
                        st.write(f"Average: **${trades_df['bet_size'].mean():,.0f}**")
                        st.write(f"Largest: **${trades_df['bet_size'].max():,.0f}**")
                        st.write(f"Total: **${trades_df['bet_size'].sum():,.0f}**")

                    st.divider()

                    # Trades table
                    st.markdown("**All Trades**")
                    display_df = trades_df[['market_question', 'outcome', 'bet_size', 'odds', 'timestamp']].copy()
                    display_df['bet_size'] = display_df['bet_size'].apply(lambda x: f"${x:,.0f}")
                    display_df['odds'] = display_df['odds'].apply(lambda x: f"{x:.1f}%")
                    display_df.columns = ['Market', 'Position', 'Size', 'Odds', 'Time']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

                # External links
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.link_button("📊 View on Polygonscan", f"https://polygonscan.com/address/{selected}", use_container_width=True)
                with col2:
                    st.link_button("🔎 View on Arkham", f"https://platform.arkhamintelligence.com/explorer/address/{selected}", use_container_width=True)
            else:
                st.info("No data found for this wallet")
    else:
        st.info("No wallets to analyze yet")

with tab4:
    st.subheader("📈 Statistics & Insights")

    if df.empty:
        st.info("No data available yet.")
    else:
        # Position analysis
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
            yes_pct = len(yes_bets) / len(df) * 100 if len(df) > 0 else 0
            st.metric("YES %", f"{yes_pct:.1f}%")

        st.divider()

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Category Breakdown**")
            cat_counts = df['market_category'].value_counts()
            fig = px.pie(
                values=cat_counts.values,
                names=cat_counts.index,
                hole=0.3
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Bet Size vs Odds**")
            fig = px.scatter(
                df, x='odds', y='bet_size',
                color='outcome',
                labels={'odds': 'Odds (%)', 'bet_size': 'Bet Size ($)'},
                color_discrete_map={'YES': '#00cc00', 'NO': '#ff4444'}
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        # Summary stats
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Bet Size Statistics**")
            st.write(f"Mean: ${df['bet_size'].mean():,.0f}")
            st.write(f"Median: ${df['bet_size'].median():,.0f}")
            st.write(f"Max: ${df['bet_size'].max():,.0f}")

        with col2:
            st.markdown("**Odds Statistics**")
            st.write(f"Mean: {df['odds'].mean():.1f}%")
            st.write(f"Median: {df['odds'].median():.1f}%")
            st.write(f"Min: {df['odds'].min():.1f}%")

# Footer
st.divider()
st.caption("🚨 PolyTracker | Data updates when worker runs")
