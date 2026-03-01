# -*- coding: utf-8 -*-
# Copyright 2024-2025 Streamlit Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import streamlit as st
import pandas as pd
import altair as alt
import datetime
from psx import stocks
from pathlib import Path

st.set_page_config(
    page_title="Stock peer analysis dashboard",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

# Load symbols from data folder
data_dir = Path(__file__).parent / "data"
if (data_dir / "stocks.csv").exists():
    STOCKS_DF = pd.read_csv(data_dir / "stocks.csv")
    STOCKS = STOCKS_DF["symbol"].tolist()
else:
    STOCKS = []

"""
# :material/query_stats: Stock peer analysis

Easily compare stocks against others in their peer group.
"""

""  # Add some space.

cols = st.columns([1, 3])
# Will declare right cell later to avoid showing it when no data.

DEFAULT_STOCKS = ["OGDC", "PPL", "LUCK", "HUBC", "BAFL", "UBL"]


def stocks_to_str(stocks):
    return ",".join(stocks)


if "tickers_input" not in st.session_state:
    st.session_state.tickers_input = st.query_params.get(
        "stocks", stocks_to_str(DEFAULT_STOCKS)
    ).split(",")


# Callback to update query param when input changes
def update_query_param():
    if st.session_state.tickers_input:
        st.query_params["stocks"] = stocks_to_str(st.session_state.tickers_input)
    else:
        st.query_params.pop("stocks", None)


top_left_cell = cols[0].container(
    border=True, height="stretch", vertical_alignment="center"
)

with top_left_cell:
    # Selectbox for stock tickers
    tickers = st.multiselect(
        "Stock tickers",
        options=sorted(set(STOCKS) | set(st.session_state.tickers_input)),
        default=st.session_state.tickers_input,
        placeholder="Choose stocks to compare. Example: NVDA",
        accept_new_options=True,
    )

# Time horizon selector
horizon_map = {
    "1 Months": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "5 Years": "5y",
    "10 Years": "10y",
    "20 Years": "20y",
}

with top_left_cell:
    # Buttons for picking time horizon
    horizon = st.pills(
        "Time horizon",
        options=list(horizon_map.keys()),
        default="6 Months",
    )

tickers = [t.upper() for t in tickers]

# Update query param when text input changes
if tickers:
    st.query_params["stocks"] = stocks_to_str(tickers)
else:
    # Clear the param if input is empty
    st.query_params.pop("stocks", None)

if not tickers:
    top_left_cell.info("Pick some stocks to compare", icon=":material/info:")
    st.stop()


right_cell = cols[1].container(
    border=True, height="stretch", vertical_alignment="center"
)


@st.cache_data(persist=True, show_spinner=False)
def fetch_stock(ticker, start_date, end_date):
    """Fetch and cache data for a single stock."""
    try:
        df = stocks(ticker, start=start_date, end=end_date)
        if df is not None and len(df) > 0:
            return df["Close"]
    except Exception:
        pass
    return None


def load_data(tickers, period, progress_bar):
    """Load data with progress bar."""
    # Convert period to date range
    end_date = datetime.date.today()
    if period == "1mo":
        start_date = end_date - datetime.timedelta(days=30)
    elif period == "3mo":
        start_date = end_date - datetime.timedelta(days=90)
    elif period == "6mo":
        start_date = end_date - datetime.timedelta(days=180)
    elif period == "1y":
        start_date = end_date - datetime.timedelta(days=365)
    elif period == "5y":
        start_date = end_date - datetime.timedelta(days=365 * 5)
    elif period == "10y":
        start_date = end_date - datetime.timedelta(days=365 * 10)
    elif period == "20y":
        start_date = end_date - datetime.timedelta(days=365 * 20)
    else:
        start_date = end_date - datetime.timedelta(days=180)

    # Fetch data for each ticker with progress
    all_data = {}
    for i, ticker in enumerate(tickers):
        progress_bar.progress(
            (i + 1) / len(tickers), text=f"Fetching data for {ticker}"
        )
        close_data = fetch_stock(ticker, start_date, end_date)
        if close_data is not None:
            all_data[ticker] = close_data
        else:
            st.warning(f"No data for {ticker}")

    if not all_data:
        raise RuntimeError("No data returned from PSX.")

    return pd.DataFrame(all_data)


# Load the data
try:
    progress_bar = st.progress(0, text="Loading data...")
    data = load_data(tickers, horizon_map[horizon], progress_bar)
    progress_bar.empty()
except Exception as e:
    st.warning(f"Error loading data: {e}")
    fetch_stock.clear()
    st.stop()

empty_columns = data.columns[data.isna().all()].tolist()

if empty_columns:
    st.error(f"Error loading data for the tickers: {', '.join(empty_columns)}.")
    st.stop()

# Normalize prices (start at 1)
normalized = data.div(data.iloc[0])

latest_norm_values = {normalized[ticker].iat[-1]: ticker for ticker in tickers}
max_norm_value = max(latest_norm_values.items())
min_norm_value = min(latest_norm_values.items())

bottom_left_cell = cols[0].container(
    border=True, height="stretch", vertical_alignment="center"
)

with bottom_left_cell:
    cols = st.columns(2)
    cols[0].metric(
        "Best stock",
        max_norm_value[1],
        delta=f"{round(max_norm_value[0] * 100)}%",
        width="content",
    )
    cols[1].metric(
        "Worst stock",
        min_norm_value[1],
        delta=f"{round(min_norm_value[0] * 100)}%",
        width="content",
    )


# Plot normalized prices
with right_cell:
    st.altair_chart(
        alt.Chart(
            normalized.reset_index().melt(
                id_vars=["Date"], var_name="Stock", value_name="Normalized price"
            )
        )
        .mark_line()
        .encode(
            alt.X("Date:T"),
            alt.Y("Normalized price:Q").scale(zero=False),
            alt.Color("Stock:N"),
        )
        .properties(height=400)
    )

""
""

# Plot individual stock vs peer average
"""
## Individual stocks vs peer average

For the analysis below, the "peer average" when analyzing stock X always
excludes X itself.
"""

if len(tickers) <= 1:
    st.warning("Pick 2 or more tickers to compare them")
    st.stop()

NUM_COLS = 4
cols = st.columns(NUM_COLS)

for i, ticker in enumerate(tickers):
    # Calculate peer average (excluding current stock)
    peers = normalized.drop(columns=[ticker])
    peer_avg = peers.mean(axis=1)

    # Create DataFrame with peer average.
    plot_data = pd.DataFrame(
        {
            "Date": normalized.index,
            ticker: normalized[ticker],
            "Peer average": peer_avg,
        }
    ).melt(id_vars=["Date"], var_name="Series", value_name="Price")

    chart = (
        alt.Chart(plot_data)
        .mark_line()
        .encode(
            alt.X("Date:T"),
            alt.Y("Price:Q").scale(zero=False),
            alt.Color(
                "Series:N",
                scale=alt.Scale(domain=[ticker, "Peer average"], range=["red", "gray"]),
                legend=alt.Legend(orient="bottom"),
            ),
            alt.Tooltip(["Date", "Series", "Price"]),
        )
        .properties(title=f"{ticker} vs peer average", height=300)
    )

    cell = cols[(i * 2) % NUM_COLS].container(border=True)
    cell.write("")
    cell.altair_chart(chart, use_container_width=True)

    # Create Delta chart
    plot_data = pd.DataFrame(
        {
            "Date": normalized.index,
            "Delta": normalized[ticker] - peer_avg,
        }
    )

    chart = (
        alt.Chart(plot_data)
        .mark_area()
        .encode(
            alt.X("Date:T"),
            alt.Y("Delta:Q").scale(zero=False),
        )
        .properties(title=f"{ticker} minus peer average", height=300)
    )

    cell = cols[(i * 2 + 1) % NUM_COLS].container(border=True)
    cell.write("")
    cell.altair_chart(chart, use_container_width=True)

""
""

"""
## Raw data
"""

data
