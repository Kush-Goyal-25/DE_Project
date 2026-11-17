"""Reusable charts and time-bucket aggregation for the dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

TEAL = "#167D8D"
NAVY = "#12233F"
TYPE_COLORS = ["#167D8D", "#4D7EA8", "#E1A04A", "#7B6FA8", "#5A9B79", "#A9B5C2"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

GRANULARITY_LABELS = {
    "Daily": "Day",
    "Weekly": "Week",
    "Monthly": "Month",
    "Yearly": "Year",
}

_BASE = {
    "margin": {"l": 8, "r": 8, "t": 12, "b": 8},
    "plot_bgcolor": "rgba(0,0,0,0)",
    "paper_bgcolor": "rgba(0,0,0,0)",
}


def _style(figure: go.Figure, **extra) -> go.Figure:
    figure.update_layout(**_BASE, **extra)
    return figure


def _period_starts(frame: pd.DataFrame, granularity: str) -> pd.Series:
    if granularity not in GRANULARITY_LABELS:
        raise ValueError(f"Unsupported trend granularity: {granularity}")

    dates = frame["incident_date"]
    if granularity == "Daily":
        return dates.dt.floor("D")
    if granularity == "Weekly":
        return dates.dt.to_period("W-SUN").dt.start_time
    if granularity == "Monthly":
        return dates.dt.to_period("M").dt.start_time
    return dates.dt.to_period("Y").dt.start_time


def aggregate_incidents_by_period(
    frame: pd.DataFrame, granularity: str
) -> pd.DataFrame:
    """Count distinct incidents in each selected calendar period."""
    data = frame.assign(period_start=_period_starts(frame, granularity))
    return (
        data.groupby("period_start", as_index=False)
        .agg(reported_incidents=("id", "nunique"))
        .sort_values("period_start")
    )


def build_incident_trend(
    frame: pd.DataFrame, granularity: str, rolling: int = 0
) -> go.Figure:
    counts = aggregate_incidents_by_period(frame, granularity)
    figure = px.line(
        counts,
        x="period_start",
        y="reported_incidents",
        markers=True,
        labels={
            "period_start": GRANULARITY_LABELS[granularity],
            "reported_incidents": "Reported incidents",
        },
    )
    figure.update_traces(line={"color": TEAL, "width": 3}, marker={"size": 7})
    if rolling > 1 and len(counts) >= rolling:
        figure.add_scatter(
            x=counts["period_start"],
            y=counts["reported_incidents"].rolling(rolling).mean(),
            mode="lines",
            name=f"{rolling}-period average",
            line={"color": "#E1A04A", "width": 2, "dash": "dash"},
        )
    return _style(
        figure,
        xaxis={"title": None, "showgrid": False},
        yaxis={"title": None, "rangemode": "tozero", "gridcolor": "#E8EDF2"},
        hovermode="x unified",
        showlegend=rolling > 1,
        legend={"title": None, "orientation": "h", "y": 1.12},
    )


def build_type_composition(frame: pd.DataFrame, granularity: str) -> go.Figure:
    """Show the top five incident types over time, grouping the rest as Other."""
    top_types = frame.groupby("incident_type")["id"].nunique().nlargest(5).index
    data = frame.assign(
        period_start=_period_starts(frame, granularity),
        type_group=frame["incident_type"].where(
            frame["incident_type"].isin(top_types), "Other"
        ),
    )
    grouped = (
        data.groupby(["period_start", "type_group"], as_index=False)
        .agg(reported_incidents=("id", "nunique"))
        .pivot(
            index="period_start",
            columns="type_group",
            values="reported_incidents",
        )
        .fillna(0)
        .astype(int)
    )
    type_order = [value for value in top_types if value in grouped.columns]
    if "Other" in grouped.columns:
        type_order.append("Other")
    chart_data = grouped.reindex(columns=type_order).reset_index()
    figure = px.area(
        chart_data,
        x="period_start",
        y=type_order,
        labels={
            "period_start": GRANULARITY_LABELS[granularity],
            "value": "Reported incidents",
            "variable": "Incident type",
        },
        color_discrete_sequence=TYPE_COLORS,
        category_orders={"variable": type_order},
    )
    return _style(
        figure,
        xaxis={"title": None, "showgrid": False},
        yaxis={"title": None, "rangemode": "tozero", "gridcolor": "#E8EDF2"},
        legend={"title": None, "orientation": "h", "y": 1.12},
        hovermode="x unified",
    )


def _ranked_bar(frame: pd.DataFrame, column: str, top_n: int) -> go.Figure:
    counts = (
        frame.groupby(column)["id"].nunique().nlargest(top_n).sort_values()
        .rename("reported_incidents").reset_index()
    )
    figure = px.bar(
        counts, x="reported_incidents", y=column, orientation="h",
        labels={"reported_incidents": "Reported incidents", column: ""},
    )
    figure.update_traces(marker_color=TEAL)
    return _style(figure, xaxis={"gridcolor": "#E8EDF2"}, yaxis={"title": None})


def build_top_types(frame: pd.DataFrame, top_n: int = 15) -> go.Figure:
    return _ranked_bar(frame, "incident_type", top_n)


def build_top_subtypes(frame: pd.DataFrame, top_n: int = 15) -> go.Figure:
    return _ranked_bar(frame, "subtype", top_n)


def build_top_locations(frame: pd.DataFrame, top_n: int = 15) -> go.Figure:
    return _ranked_bar(frame, "location", top_n)


def build_hourly_distribution(frame: pd.DataFrame) -> go.Figure:
    counts = (
        frame.groupby("hour")["id"].nunique()
        .reindex(range(24), fill_value=0).rename("n").reset_index()
    )
    figure = px.bar(counts, x="hour", y="n",
                    labels={"hour": "Hour of day", "n": "Reported incidents"})
    figure.update_traces(marker_color=TEAL)
    return _style(
        figure,
        xaxis={"dtick": 1, "title": "Hour of day"},
        yaxis={"title": None, "gridcolor": "#E8EDF2"},
    )


def build_weekday_distribution(frame: pd.DataFrame) -> go.Figure:
    counts = (
        frame.groupby("weekday")["id"].nunique()
        .reindex(WEEKDAYS, fill_value=0).rename("n").reset_index()
    )
    figure = px.bar(counts, x="weekday", y="n",
                    labels={"weekday": "", "n": "Reported incidents"})
    figure.update_traces(marker_color=NAVY)
    return _style(figure, yaxis={"title": None, "gridcolor": "#E8EDF2"})


def build_weekday_hour_heatmap(frame: pd.DataFrame) -> go.Figure:
    grid = (
        frame.groupby(["weekday", "hour"])["id"].nunique()
        .unstack(fill_value=0)
        .reindex(index=WEEKDAYS, columns=range(24), fill_value=0)
    )
    figure = px.imshow(
        grid, aspect="auto",
        color_continuous_scale=["#F3F7FA", "#9CCBD3", TEAL, NAVY],
        labels={"x": "Hour of day", "y": "", "color": "Incidents"},
    )
    return _style(figure, xaxis={"dtick": 1})


def build_monthly_seasonality(frame: pd.DataFrame) -> go.Figure:
    counts = (
        frame.groupby(["year", "month"])["id"].nunique()
        .rename("n").reset_index()
    )
    counts["year"] = counts["year"].astype(str)
    figure = px.line(
        counts, x="month", y="n", color="year", markers=True,
        color_discrete_sequence=TYPE_COLORS * 3,
        labels={"month": "Month", "n": "Reported incidents", "year": "Year"},
    )
    return _style(
        figure,
        xaxis={"tickmode": "array", "tickvals": list(range(1, 13)),
               "ticktext": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]},
        yaxis={"title": None, "rangemode": "tozero", "gridcolor": "#E8EDF2"},
        legend={"orientation": "h", "y": 1.12, "title": None},
    )


def build_type_share(frame: pd.DataFrame) -> go.Figure:
    top = frame.groupby("incident_type")["id"].nunique().nlargest(8)
    other = frame["id"].nunique() - top.sum()
    if other > 0:
        top.loc["Other"] = other
    figure = px.pie(
        values=top.values, names=top.index, hole=0.55,
        color_discrete_sequence=TYPE_COLORS + ["#C9A0DC", "#E87461", "#8AA1B1"],
    )
    figure.update_traces(textinfo="percent")
    return _style(figure, legend={"title": None})


def build_type_hour_heatmap(frame: pd.DataFrame, top_n: int = 10) -> go.Figure:
    top = frame.groupby("incident_type")["id"].nunique().nlargest(top_n).index
    grid = (
        frame[frame["incident_type"].isin(top)]
        .groupby(["incident_type", "hour"])["id"].nunique()
        .unstack(fill_value=0)
        .reindex(index=top, columns=range(24), fill_value=0)
    )
    figure = px.imshow(
        grid, aspect="auto",
        color_continuous_scale=["#F3F7FA", "#9CCBD3", TEAL, NAVY],
        labels={"x": "Hour of day", "y": "", "color": "Incidents"},
    )
    return _style(figure, xaxis={"dtick": 1})
