#!/usr/bin/env python3
"""
Dual-axis chart: daily global earthquake count (filtered) vs. Bitcoin price (USD).
"""

import datetime as dt
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


MONTHS_BACK = 6
MIN_MAGNITUDE = 4.5
USGS_PAGE_SIZE = 20_000
REQUEST_TIMEOUT_SECONDS = 30
MAX_USGS_PAGES = 50
COINGECKO_MAX_DAYS = 365


class DataFetchError(RuntimeError):
    """Raised when an external API cannot be fetched or parsed."""


def get_date_window(
    months_back: int = MONTHS_BACK,
    today: dt.date | None = None,
) -> tuple[dt.date, dt.date]:
    """Return [start_date, end_date] for the selected month window."""
    if months_back < 1:
        raise ValueError("months_back must be >= 1")
    end_date = today or dt.date.today()
    start_date = (pd.Timestamp(end_date) - pd.DateOffset(months=months_back)).date()
    return start_date, end_date


def fetch_earthquake_counts(
    start_date: dt.date,
    end_date: dt.date,
    min_magnitude: float = MIN_MAGNITUDE,
) -> pd.DataFrame:
    """
    Return a DataFrame with columns ['date', 'earthquakes'].
    Only events with magnitude >= min_magnitude are counted.
    """
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    base_params = {
        "format": "geojson",
        "starttime": start_date.isoformat(),
        "endtime": (end_date + dt.timedelta(days=1)).isoformat(),
        "minmagnitude": str(min_magnitude),
        "orderby": "time-asc",
        "limit": str(USGS_PAGE_SIZE),
    }

    all_features: list[dict] = []
    offset = 1
    for _ in range(MAX_USGS_PAGES):
        params = {**base_params, "offset": str(offset)}
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise DataFetchError(f"USGS request failed: {exc}") from exc

        features = data.get("features")
        if not isinstance(features, list):
            raise DataFetchError("USGS response did not include a valid 'features' list.")

        all_features.extend(features)
        if len(features) < USGS_PAGE_SIZE:
            break
        offset += USGS_PAGE_SIZE
    else:
        raise DataFetchError("USGS pagination exceeded the safety limit.")

    daily_counts: dict[dt.date, int] = {}
    for feat in all_features:
        ts_ms = feat.get("properties", {}).get("time")
        if ts_ms is None:
            continue
        day = dt.datetime.utcfromtimestamp(ts_ms / 1000).date()
        daily_counts[day] = daily_counts.get(day, 0) + 1

    all_days = pd.date_range(start=start_date, end=end_date, freq="D").date
    df = pd.DataFrame({"date": all_days})
    df["earthquakes"] = df["date"].map(daily_counts).fillna(0).astype(int)
    return df


def fetch_bitcoin_prices(days: int) -> pd.DataFrame:
    """
    Return a DataFrame with columns ['date', 'price_usd'] for the last `days`.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    days = min(days, COINGECKO_MAX_DAYS)

    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": str(days)}

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        raise DataFetchError(f"CoinGecko request failed: {exc}") from exc

    prices = payload.get("prices")
    if not isinstance(prices, list):
        raise DataFetchError("CoinGecko response did not include a valid 'prices' list.")

    price_df = pd.DataFrame(prices, columns=["ts_ms", "price_usd"])
    price_df["date"] = pd.to_datetime(price_df["ts_ms"], unit="ms").dt.date
    return price_df.groupby("date", as_index=False)["price_usd"].last()


@st.cache_data(ttl=86_400)
def load_data(
    months_back: int = MONTHS_BACK,
    min_magnitude: float = MIN_MAGNITUDE,
) -> pd.DataFrame:
    """Fetch and merge earthquake and Bitcoin datasets for the same date window."""
    start_date, end_date = get_date_window(months_back=months_back)
    lookback_days = (end_date - start_date).days + 2
    eq = fetch_earthquake_counts(start_date, end_date, min_magnitude=min_magnitude)
    btc = fetch_bitcoin_prices(days=lookback_days)
    merged = pd.merge(eq, btc, on="date", how="inner").sort_values("date")
    if merged.empty:
        raise DataFetchError("No overlapping earthquake and Bitcoin data was returned.")
    return merged


def build_figure(df: pd.DataFrame) -> go.Figure:
    """Build the dual-axis Plotly figure for the dashboard."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["earthquakes"],
            name="Earthquakes",
            marker_color="#d62728",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["price_usd"],
            name="Bitcoin (USD)",
            mode="lines",
            line=dict(color="#111111", width=2),
            yaxis="y2",
        )
    )
    fig.update_layout(
        title=dict(
            text="Daily Earthquakes vs. Bitcoin (USD)",
            font=dict(color="#111111", size=22),
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="Date",
        yaxis=dict(
            title=dict(text="Earthquakes per day", font=dict(color="#d62728")),
            tickfont=dict(color="#d62728"),
        ),
        yaxis2=dict(
            title=dict(text="Bitcoin price (USD)", font=dict(color="#111111")),
            tickfont=dict(color="#111111"),
            overlaying="y",
            side="right",
        ),
        legend=dict(orientation="h", y=1.02, x=1),
        template="plotly_white",
        margin=dict(l=60, r=60, t=80, b=60),
        hovermode="x unified",
    )
    return fig


def render_app() -> None:
    st.set_page_config(page_title="Earthquakes vs Bitcoin", layout="wide")
    st.title("Daily Earthquakes vs. Bitcoin Price (USD)")
    st.sidebar.header("Controls")
    months_back = st.sidebar.slider(
        "Months back",
        min_value=1,
        max_value=11,
        value=MONTHS_BACK,
        step=1,
    )
    min_magnitude = st.sidebar.slider(
        "Minimum earthquake magnitude",
        min_value=4.0,
        max_value=9.0,
        value=max(4.0, MIN_MAGNITUDE),
        step=0.1,
    )
    st.sidebar.caption(
        "USGS reports multiple magnitude types (commonly moment magnitude, Mw). "
        "This is not strictly the original Richter scale (ML), though values are "
        "comparable in overlapping ranges."
    )

    try:
        df = load_data(months_back=months_back, min_magnitude=min_magnitude)
    except (DataFetchError, ValueError) as exc:
        st.error(str(exc))
        st.stop()

    st.plotly_chart(build_figure(df), use_container_width=True)

    st.divider()
    st.subheader("README")
    readme_path = Path(__file__).with_name("README.md")
    try:
        st.markdown(readme_path.read_text(encoding="utf-8"))
    except OSError:
        st.info("README.md was not found.")


if __name__ == "__main__":
    render_app()
