#!/usr/bin/env python3
"""
Dual‑axis chart: Daily global earthquake count (filtered) vs. Bitcoin price (USD).

Features added compared to the basic version:
  • Only the most recent 2 months are queried.
  • A minimum magnitude filter (default 4.5) removes tiny events,
    keeping the USGS request comfortably under the 20 000‑event limit.
"""

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests


# ----------------------------------------------------------------------
# 1️⃣ CONFIGURATION
# ----------------------------------------------------------------------
# How many months back you want to look (must be >= 1)
MONTHS_BACK = 2

# Minimum magnitude to keep (USGS uses the same scale as the Richter scale)
MIN_MAGNITUDE = 4.5   # change to 3.0, 5.0, etc. as you wish

# ----------------------------------------------------------------------
# 2️⃣ Helper – fetch filtered earthquake counts from USGS
# ----------------------------------------------------------------------
def fetch_earthquake_counts(
    start_date: dt.date,
    end_date: dt.date,
    min_magnitude: float = MIN_MAGNITUDE,
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns ['date', 'earthquakes'].
    Only events with magnitude >= min_magnitude are counted.
    """
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": start_date.isoformat(),
        "endtime": (end_date + dt.timedelta(days=1)).isoformat(),
        "minmagnitude": str(min_magnitude),
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        sys.exit(f"[ERROR] USGS request failed: {exc}")

    data = resp.json()
    # Count per UTC day
    daily_counts = {}
    for feat in data.get("features", []):
        ts_ms = feat["properties"]["time"]
        day = dt.datetime.utcfromtimestamp(ts_ms / 1000).date()
        daily_counts[day] = daily_counts.get(day, 0) + 1

    # Build a full date range (fill missing days with 0)
    all_days = pd.date_range(start=start_date, end=end_date, freq="D")
    df = pd.DataFrame({"date": all_days})
    df["earthquakes"] = df["date"].dt.date.map(daily_counts).fillna(0).astype(int)
    df["date"] = df["date"].dt.date
    return df


# ----------------------------------------------------------------------
# 3️⃣ Helper – fetch daily Bitcoin closing price from CoinGecko
# ----------------------------------------------------------------------
def fetch_bitcoin_prices() -> pd.DataFrame:
    """
    Returns a DataFrame with columns ['date', 'price_usd'].
    Uses CoinGecko's market_chart endpoint (all‑time data).
    """
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": "62"}
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        sys.exit(f"[ERROR] CoinGecko request failed: {exc}")

    payload = resp.json()
    price_df = pd.DataFrame(payload["prices"], columns=["ts_ms", "price_usd"])
    price_df["date"] = pd.to_datetime(price_df["ts_ms"], unit="ms").dt.date
    # Take the last price reported for each day → acts as the closing price
    daily = price_df.groupby("date", as_index=False)["price_usd"].last()
    return daily



import streamlit as st

st.set_page_config(page_title="Earthquakes ↔ Bitcoin", layout="wide")

st.title("🌍 Daily Earthquakes vs. 💰 Bitcoin Price (USD)")

# Re‑run the fetches each time the page loads (or cache them)
@st.cache_data(ttl=86400)   # cache for 24 h
def load_data():
    today = dt.date.today()
    start = today - dt.timedelta(days=365)
    eq = fetch_earthquake_counts(start, today)
    btc = fetch_bitcoin_prices()
    return pd.merge(eq, btc, on="date", how="inner").sort_values("date")

df = load_data()

# ------------------------------------------------------------
# Plotting – the only part that needed fixing
# ------------------------------------------------------------
fig = go.Figure()

# Bars – earthquake count
fig.add_trace(
    go.Bar(
        x=df["date"],
        y=df["earthquakes"],
        name="Earthquakes",
        marker_color="#636efa",
    )
)

# Line – Bitcoin price
fig.add_trace(
    go.Scatter(
        x=df["date"],
        y=df["price_usd"],
        name="Bitcoin (USD)",
        mode="lines",
        line=dict(color="#ef553b", width=2),
        yaxis="y2",
    )
)

# ----------- Updated layout ---------------------------------
fig.update_layout(
    # Title (use the nested dict syntax)
    title=dict(
        text="🌍 Daily Earthquakes vs. 💰 Bitcoin (USD)",
        font=dict(color="#ef553b", size=22),   # optional styling
        x=0.5,                                 # centre the title
        xanchor="center",
    ),

    # X‑axis
    xaxis_title="Date",

    # Left Y‑axis – earthquakes
    yaxis=dict(
        title=dict(text="Earthquakes per day", font=dict(color="#636efa")),
        tickfont=dict(color="#636efa"),
    ),

    # Right Y‑axis – Bitcoin price
    yaxis2=dict(
        title=dict(text="Bitcoin price (USD)", font=dict(color="#ef553b")),
        tickfont=dict(color="#ef553b"),
        overlaying="y",
        side="right",
    ),

    legend=dict(orientation="h", y=1.02, x=1),
    template="plotly_white",
    margin=dict(l=60, r=60, t=80, b=60),
    hovermode="x unified",
)

# ------------------------------------------------------------
# Streamlit rendering
# ------------------------------------------------------------
st.plotly_chart(fig, use_container_width=True)
