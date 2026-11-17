"""Cambridge Police incident dashboard (Streamlit).

Run:  streamlit run dashboard.py
"""

from __future__ import annotations

import time as _time
from datetime import time
from pathlib import Path

import pandas as pd
import streamlit as st

import charts

CACHE_FILE = Path("data/incidents_clean.csv")
MAX_AGE_HOURS = 24


def cache_is_fresh() -> bool:
    return (
        CACHE_FILE.exists()
        and _time.time() - CACHE_FILE.stat().st_mtime < MAX_AGE_HOURS * 3600
    )


@st.cache_data(ttl=3600, show_spinner="Loading incident data…")
def load_data(refresh_token: int) -> pd.DataFrame:
    if refresh_token == 0 and cache_is_fresh():
        raw = pd.read_csv(CACHE_FILE, parse_dates=["date_time"])
    else:
        try:
            raw = run_pipeline()
            CACHE_FILE.parent.mkdir(exist_ok=True)
            raw.to_csv(CACHE_FILE, index=False)
        except Exception:
            if not CACHE_FILE.exists():
                raise
            raw = pd.read_csv(CACHE_FILE, parse_dates=["date_time"])  # use old data
    return prepare(raw)


st.set_page_config(page_title="Cambridge Crime Trends", page_icon="🚓", layout="wide")

st.markdown(
    f"""
    <style>
      .block-container {{padding-top: 1.5rem;}}
      .kpi {{background:#F3F7FA; border-left:5px solid {charts.TEAL};
             border-radius:8px; padding:12px 16px;}}
      .kpi .label {{font-size:0.78rem; color:#5B6B7C; text-transform:uppercase;
                    letter-spacing:.04em;}}
      .kpi .value {{font-size:1.6rem; font-weight:700; color:{charts.NAVY};}}
      .kpi .sub {{font-size:0.8rem; color:#5B6B7C;}}
      @media (prefers-color-scheme: dark) {{
        .kpi {{background:#1B2A3D;}} .kpi .value {{color:#E8EEF4;}}
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- data loading
def run_pipeline() -> pd.DataFrame:
    """Run the existing extract -> validate -> transform stages."""
    from extract import extract_data
    from transform import transform_data
    from validate import validate_data

    return transform_data(validate_data(extract_data()))


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Add the columns the charts expect."""
    df = df.copy()
    df["date_time"] = pd.to_datetime(df["date_time"])
    df["incident_date"] = df["date_time"].dt.normalize()
    df["incident_type"] = df["type"].fillna("Unknown").astype(str).str.strip()
    df["subtype"] = df["subtype"].fillna("Unspecified").astype(str).str.strip()
    df["location"] = df["location"].fillna("Unknown").astype(str).str.strip()
    df["description"] = df["description"].fillna("")
    df["year"] = df["date_time"].dt.year
    df["month"] = df["date_time"].dt.month
    df["hour"] = df["date_time"].dt.hour
    df["weekday"] = pd.Categorical(
        df["date_time"].dt.day_name().str[:3], categories=charts.WEEKDAYS, ordered=True
    )
    df["minute_of_day"] = df["hour"] * 60 + df["date_time"].dt.minute
    return df


# --------------------------------------------------------------------- sidebar
if "refresh" not in st.session_state:
    st.session_state.refresh = 0

st.sidebar.title("Filters")
if st.sidebar.button("🔄 Re-fetch from Socrata"):
    st.session_state.refresh += 1
    st.cache_data.clear()

try:
    data = load_data(st.session_state.refresh)
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not load data: {exc}")
    st.info(
        "Check SOCRATA_APP_TOKEN in .env, or place a cleaned CSV at " f"`{CACHE_FILE}`."
    )
    st.stop()

min_d, max_d = data["incident_date"].min().date(), data["incident_date"].max().date()

preset = st.sidebar.radio(
    "Quick range",
    ["Custom", "Last 30 days", "Last 90 days", "Last 12 months", "All time"],
    index=4,
)
if preset == "Custom":
    picked = st.sidebar.date_input(
        "Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d
    )
    start_d, end_d = (
        picked if isinstance(picked, tuple) and len(picked) == 2 else (min_d, max_d)
    )
else:
    days = {"Last 30 days": 30, "Last 90 days": 90, "Last 12 months": 365}.get(preset)
    end_d = max_d
    start_d = (
        max(min_d, (pd.Timestamp(max_d) - pd.Timedelta(days=days)).date())
        if days
        else min_d
    )

t_start, t_end = st.sidebar.slider(
    "Time of day",
    value=(time(0, 0), time(23, 59)),
    format="HH:mm",
    step=pd.Timedelta(minutes=15).to_pytimedelta(),
)
granularity = st.sidebar.selectbox(
    "Trend granularity", list(charts.GRANULARITY_LABELS), index=2
)
rolling = st.sidebar.slider(
    "Moving average (periods)", 0, 12, 0, help="0 disables the overlay"
)

all_types = sorted(data["incident_type"].unique())
chosen_types = st.sidebar.multiselect(
    "Incident types", all_types, placeholder="All types"
)
location_q = st.sidebar.text_input("Location contains", placeholder="e.g. Mass Ave")
desc_q = st.sidebar.text_input("Description contains")

# ------------------------------------------------------------------- filtering
lo = t_start.hour * 60 + t_start.minute
hi = t_end.hour * 60 + t_end.minute
mask = data["incident_date"].between(pd.Timestamp(start_d), pd.Timestamp(end_d)) & data[
    "minute_of_day"
].between(lo, hi)
if chosen_types:
    mask &= data["incident_type"].isin(chosen_types)
if location_q:
    mask &= data["location"].str.contains(location_q, case=False, na=False, regex=False)
if desc_q:
    mask &= data["description"].str.contains(desc_q, case=False, na=False, regex=False)
view = data[mask]

# ---------------------------------------------------------------------- header
st.title("🚓 Cambridge Crime Trends")
st.caption(
    f"Cambridge Police Log · {start_d:%d %b %Y} → {end_d:%d %b %Y} · "
    f"{t_start:%H:%M}–{t_end:%H:%M}"
)

if view.empty:
    st.warning("No incidents match the current filters.")
    st.stop()

# ------------------------------------------------------------------------ KPIs
total = view["id"].nunique()
n_days = max((end_d - start_d).days + 1, 1)

# compare with the immediately preceding window of equal length (same other filters)
prev_start = pd.Timestamp(start_d) - pd.Timedelta(days=n_days)
prev_mask = data["incident_date"].between(
    prev_start, pd.Timestamp(start_d) - pd.Timedelta(days=1)
) & data["minute_of_day"].between(lo, hi)
if chosen_types:
    prev_mask &= data["incident_type"].isin(chosen_types)
prev_total = data[prev_mask]["id"].nunique()
delta = (
    f"{(total - prev_total) / prev_total:+.1%} vs previous period"
    if prev_total
    else "no prior period"
)

busiest_hour = view.groupby("hour")["id"].nunique().idxmax()
top_type = view.groupby("incident_type")["id"].nunique().idxmax()
top_loc = view.groupby("location")["id"].nunique().idxmax()


def kpi(col, label, value, sub=""):
    col.markdown(
        f'<div class="kpi"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


c1, c2, c3, c4, c5 = st.columns(5)
kpi(c1, "Incidents", f"{total:,}", delta)
kpi(c2, "Avg per day", f"{total / n_days:.1f}", f"over {n_days:,} days")
kpi(c3, "Busiest hour", f"{busiest_hour:02d}:00", "most incidents")
kpi(
    c4,
    "Top type",
    top_type[:22],
    f"{view[view.incident_type == top_type]['id'].nunique():,} incidents",
)
kpi(
    c5,
    "Top location",
    top_loc[:22],
    f"{view[view.location == top_loc]['id'].nunique():,} incidents",
)
st.write("")

# ------------------------------------------------------------------------ tabs
t_trend, t_types, t_when, t_where, t_data = st.tabs(
    ["📈 Trends", "🗂️ Incident types", "🕒 When", "📍 Where", "📋 Data"]
)

with t_trend:
    st.subheader(f"{granularity} incident trend")
    st.plotly_chart(
        charts.build_incident_trend(view, granularity, rolling),
        width="stretch",
    )
    st.subheader("Incident type composition over time")
    st.plotly_chart(charts.build_type_composition(view, granularity), width="stretch")
    st.subheader("Seasonality by year")
    st.plotly_chart(charts.build_monthly_seasonality(view), width="stretch")

with t_types:
    a, b = st.columns([1, 1])
    a.subheader("Share of incidents by type")
    a.plotly_chart(charts.build_type_share(view), width="stretch")
    b.subheader("Top incident types")
    b.plotly_chart(charts.build_top_types(view), width="stretch")
    st.subheader("Top subtypes")
    st.plotly_chart(charts.build_top_subtypes(view), width="stretch")

with t_when:
    a, b = st.columns(2)
    a.subheader("By hour of day")
    a.plotly_chart(charts.build_hourly_distribution(view), width="stretch")
    b.subheader("By day of week")
    b.plotly_chart(charts.build_weekday_distribution(view), width="stretch")
    st.subheader("Weekday × hour heatmap")
    st.plotly_chart(charts.build_weekday_hour_heatmap(view), width="stretch")
    st.subheader("Incident type × hour heatmap")
    st.plotly_chart(charts.build_type_hour_heatmap(view), width="stretch")

with t_where:
    st.subheader("Top locations")
    n = st.slider("Locations to show", 5, 40, 15)
    st.plotly_chart(charts.build_top_locations(view, n), width="stretch")

with t_data:
    st.subheader("Matching incidents")
    cols = ["date_time", "id", "incident_type", "subtype", "location", "description"]
    table = view.sort_values("date_time", ascending=False)[cols]
    st.dataframe(table, width="stretch", hide_index=True, height=480)
    st.download_button(
        "⬇️ Download filtered CSV",
        table.to_csv(index=False),
        "filtered_incidents.csv",
        "text/csv",
    )
