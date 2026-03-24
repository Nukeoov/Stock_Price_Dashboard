from typing import Any
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf

#Page config
st.set_page_config(page_title="Stock Price Dashboard", layout="wide")

st.markdown("""
<style>
    .main-title { text-align: center; color: #1a73e8 !important; font-size: 6rem !important; font-weight: 700 !important; margin-bottom: 0.8rem; line-height: 1.1; }
    .metric-card { border-radius: 10px; padding: 16px 20px; margin: 4px; }
    .card-open    { background-color: #dbeafe; }
    .card-high    { background-color: #dcfce7; }
    .card-low     { background-color: #fee2e2; }
    .card-close   { background-color: #dbeafe; }
    .card-volume  { background-color: #dbeafe; }
    .card-change-up   { background-color: #dcfce7; }
    .card-change-down { background-color: #fee2e2; }
    .card-change-flat { background-color: #fef9c3; }
    .card-label  { font-size: 0.75rem; color: #555; font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }
    .card-value  { font-size: 1.6rem; font-weight: 700; }
    .open-val    { color: #1d4ed8; }
    .high-val    { color: #15803d; }
    .low-val     { color: #dc2626; }
    .close-val   { color: #1d4ed8; }
    .vol-val     { color: #1d4ed8; }
    .change-up   { color: #15803d; }
    .change-down { color: #dc2626; }
    .change-flat { color: #92400e; }
</style>
""", unsafe_allow_html=True)

#Header
st.markdown('<h1 class="main-title">Stock Price Dashboard</h1>', unsafe_allow_html=True)

#Controls (Stock symbol + Time range + Candle time)
col_sym, col_range, col_candle = st.columns([2, 1.2, 1.2])

with col_sym:
    st.markdown("**Stock Symbol**")
    ticker_input = st.text_input("Stock Symbol", value="AAPL", label_visibility="collapsed").upper().strip()

with col_range:
    st.markdown("**Time Range**")
    time_options = {
        "7 days":   "7d",
        "14 days":  "14d",
        "30 days":  "1mo",
        "90 days":  "3mo",
        "180 days": "6mo",
        "1 year":   "1y",
        "5 years":  "5y",
    }
    selected_range = st.selectbox("Time Range", list(time_options.keys()), index=2, label_visibility="collapsed")

with col_candle:
    st.markdown("**Candle Time**")
    candle_options = {
        "15 min": "15m",
        "30 min": "30m",
        "1h": "1h",
        "4h": "4h",
        "1day": "1d",
    }
    selected_candle = st.selectbox("Candle Time", list(candle_options.keys()), index=4, label_visibility="collapsed")

#Fetch data from Yahoo Finance
@st.cache_data(ttl=300)
def fetch_stock_data(ticker: str, yf_period: str, yf_interval: str):
    stock = yf.Ticker(ticker)
    hist = stock.history(period=yf_period, interval=yf_interval)
    if hist.empty:
        return None, None
    hist.index = hist.index.tz_localize(None)
    hist.reset_index(inplace=True)
    hist.columns = hist.columns.str.lower()
    hist.rename(columns={"datetime": "date"}, inplace=True)
    info = stock.info
    return hist, info

period = time_options[selected_range]
interval = candle_options[selected_candle]

ticker_df, stock_info = fetch_stock_data(ticker_input, period, interval)

#Validate
if ticker_df is None or ticker_df.empty:
    st.error(f"Could not find data for **{ticker_input}**. Check the symbol and try again.")
    st.stop()

#Company name
company_name = stock_info.get("longName", ticker_input) if stock_info else ticker_input
st.markdown(f"### {company_name} &nbsp; `{ticker_input}`")
st.caption(f"Latest trading date: {ticker_df['date'].iloc[-1].strftime('%Y-%m-%d')}")

#Metric cards
latest = ticker_df.iloc[-1]

# Calculate % change vs previous candle
if len(ticker_df) >= 2:
    prev_close = ticker_df.iloc[-2]['close']
    curr_close = latest['close']
    pct_change = ((curr_close - prev_close) / prev_close) * 100
    if pct_change > 0:
        change_card_css = "card-change-up"
        change_val_css  = "change-up"
        change_display  = f"+{pct_change:.2f}%"
    elif pct_change < 0:
        change_card_css = "card-change-down"
        change_val_css  = "change-down"
        change_display  = f"{pct_change:.2f}%"
    else:
        change_card_css = "card-change-flat"
        change_val_css  = "change-flat"
        change_display  = "--"
else:
    change_card_css = "card-change-flat"
    change_val_css  = "change-flat"
    change_display  = "--"

c1, c2, c3, c4, c5, c6 = st.columns(6)

def metric_card(column, css_card, css_val, label, value):
    column.markdown(f"""
    <div class="metric-card {css_card}">
        <div class="card-label">{label}</div>
        <div class="card-value {css_val}">{value}</div>
    </div>""", unsafe_allow_html=True)

metric_card(c1, "card-open",      "open-val",   "Open",     f"${latest['open']:,.2f}")
metric_card(c2, "card-high",      "high-val",   "High",     f"${latest['high']:,.2f}")
metric_card(c3, "card-low",       "low-val",    "Low",      f"${latest['low']:,.2f}")
metric_card(c4, "card-close",     "close-val",  "Close",    f"${latest['close']:,.2f}")
metric_card(c5, "card-volume",    "vol-val",    "Volume",   f"{int(latest['volume']):,}")
metric_card(c6, change_card_css,  change_val_css, "% Change", change_display)

st.markdown("<br>", unsafe_allow_html=True)

# Remove gaps
range_breaks: list[dict[str, Any]] = [{"bounds": ["sat", "mon"]}]

if interval in ["15m", "30m", "1h"]:
    range_breaks.append({"bounds": [16, 9.5], "pattern": "hour"})

#Candlestick chart
price_fig = go.Figure()

price_fig.add_trace(go.Candlestick(
    x=ticker_df["date"],
    open=ticker_df["open"],
    high=ticker_df["high"],
    low=ticker_df["low"],
    close=ticker_df["close"],
    name="Price",
    increasing=dict(line=dict(color="#16a34a"), fillcolor="#16a34a"),
    decreasing=dict(line=dict(color="#dc2626"), fillcolor="#dc2626"),
))

price_fig.update_layout(
    title=dict(
        text=f"Candlestick Chart — {selected_range} | {selected_candle} ({ticker_input})",
        font=dict(size=15, color="#1e293b"),
    ),
    xaxis=dict(
        showgrid=False,
        title="",
        rangeslider=dict(visible=False),
        rangebreaks=range_breaks
    ),
    yaxis=dict(showgrid=True, gridcolor="#e5e7eb", title="Price (USD)"),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=10, r=10, t=50, b=10),
    hovermode="x unified",
    height=450,
)

st.plotly_chart(price_fig, use_container_width=True)

#Volume chart
with st.expander("**Volume Chart**", expanded=False):
    vol_fig = go.Figure()
    vol_fig.add_trace(go.Bar(
        x=ticker_df["date"],
        y=ticker_df["volume"],
        marker=dict(color="#60a5fa"),
        name="Volume",
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Volume: %{y:,}<extra></extra>",
    ))
    vol_fig.update_layout(
        xaxis=dict(
            showgrid=False,
            title="",
            rangebreaks=range_breaks
        ),
        yaxis=dict(showgrid=True, gridcolor="#e5e7eb", title="Volume"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        height=260,
    )
    st.plotly_chart(vol_fig, use_container_width=True)