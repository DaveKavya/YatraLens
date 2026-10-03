"""
YatraLens Tourism Analysis Module
===================================
Core data analysis logic for the tourism analytics application.
All insights and statistics are computed directly from the loaded dataset.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import json
from plotly.utils import PlotlyJSONEncoder


# ─────────────────────────────────────────────
# SEASON MAPPING
# ─────────────────────────────────────────────
# Indian Tourism Seasonal Classification:
#   Winter  (Nov–Feb): Best travel weather, highest tourist season
#   Summer  (Mar–May): Hot but transitional, moderate tourist activity
#   Monsoon (Jun–Sep): Rainy season, generally lower footfall
#   Autumn  (Oct):     Post-monsoon, good weather, recovering footfall

MONTH_TO_SEASON = {
    1: "Winter",
    2: "Winter",
    3: "Summer",
    4: "Summer",
    5: "Summer",
    6: "Monsoon",
    7: "Monsoon",
    8: "Monsoon",
    9: "Monsoon",
    10: "Autumn",
    11: "Winter",
    12: "Winter",
}

SEASON_ORDER = ["Winter", "Summer", "Autumn", "Monsoon"]
MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

# Chart colour palette (restrained, professional)
PRIMARY_COLOR = "#2563EB"
SECONDARY_COLOR = "#059669"
ACCENT_COLORS = [
    "#2563EB", "#059669", "#D97706", "#DC2626",
    "#7C3AED", "#0891B2", "#BE185D", "#065F46",
    "#92400E", "#1E3A8A", "#166534", "#991B1B",
    "#4338CA", "#0E7490", "#9D174D",
]


# ─────────────────────────────────────────────
# DATA LOADING & CLEANING
# ─────────────────────────────────────────────

REQUIRED_COLUMNS = {
    "DestinationID", "Destination", "State",
    "Month", "DomesticVisitors", "ForeignVisitors", "HotelOccupancyPct"
}


def load_and_clean(filepath: str) -> pd.DataFrame:
    """
    Load CSV, coerce types, derive computed columns.
    Returns a clean DataFrame ready for analysis.
    """
    df = pd.read_csv(filepath)

    # Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

    # Parse Month – expected format: YYYY-MM
    df["Month"] = pd.to_datetime(df["Month"], format="%Y-%m", errors="coerce")
    df.dropna(subset=["Month"], inplace=True)

    # Coerce numeric columns, drop rows where visitor counts are invalid
    for col in ["DomesticVisitors", "ForeignVisitors", "HotelOccupancyPct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.dropna(subset=["DomesticVisitors", "ForeignVisitors"], inplace=True)
    df["HotelOccupancyPct"] = df["HotelOccupancyPct"].fillna(df["HotelOccupancyPct"].median())

    # Derived columns
    df["TotalVisitors"] = df["DomesticVisitors"] + df["ForeignVisitors"]
    df["MonthNum"] = df["Month"].dt.month
    df["Year"] = df["Month"].dt.year
    df["MonthLabel"] = df["MonthNum"].map(MONTH_NAMES) + " " + df["Year"].astype(str)
    df["Season"] = df["MonthNum"].map(MONTH_TO_SEASON)

    df.reset_index(drop=True, inplace=True)
    return df


def validate_columns(df: pd.DataFrame) -> list[str]:
    """Return list of missing required columns."""
    return list(REQUIRED_COLUMNS - set(df.columns))


# ─────────────────────────────────────────────
# FILTER HELPERS
# ─────────────────────────────────────────────

def apply_filters(df: pd.DataFrame, state=None, destination=None,
                  month=None, season=None) -> pd.DataFrame:
    """Apply user-selected filters and return filtered DataFrame."""
    fdf = df.copy()
    if state and state != "All":
        fdf = fdf[fdf["State"] == state]
    if destination and destination != "All":
        fdf = fdf[fdf["Destination"] == destination]
    if month and month != "All":
        fdf = fdf[fdf["MonthLabel"] == month]
    if season and season != "All":
        fdf = fdf[fdf["Season"] == season]
    return fdf


# ─────────────────────────────────────────────
# SUMMARY STATISTICS
# ─────────────────────────────────────────────

def compute_summary(df: pd.DataFrame) -> dict:
    """Compute high-level KPIs shown on the dashboard."""
    if df.empty:
        return {
            "total_visitors": 0, "domestic_visitors": 0,
            "foreign_visitors": 0, "avg_occupancy": 0.0,
            "top_destination": "N/A", "num_destinations": 0,
            "num_states": 0, "data_period": "N/A",
        }

    top_dest_row = (
        df.groupby("Destination")["TotalVisitors"].sum().idxmax()
    )
    period_start = df["Month"].min().strftime("%b %Y")
    period_end = df["Month"].max().strftime("%b %Y")

    return {
        "total_visitors": int(df["TotalVisitors"].sum()),
        "domestic_visitors": int(df["DomesticVisitors"].sum()),
        "foreign_visitors": int(df["ForeignVisitors"].sum()),
        "avg_occupancy": round(float(df["HotelOccupancyPct"].mean()), 1),
        "top_destination": top_dest_row,
        "num_destinations": df["Destination"].nunique(),
        "num_states": df["State"].nunique(),
        "data_period": f"{period_start} – {period_end}",
    }


# ─────────────────────────────────────────────
# CHART GENERATORS
# ─────────────────────────────────────────────

CHART_LAYOUT = dict(
    font=dict(family="Inter, sans-serif", size=13, color="#1f2937"),
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    margin=dict(l=50, r=30, t=55, b=50),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
)


def chart_domestic_foreign_stacked(df: pd.DataFrame, top_n: int = 10) -> str:
    """Stacked bar: Domestic vs Foreign visitors for top N destinations."""
    if df.empty:
        return _empty_chart("No data available")

    dest_grp = (
        df.groupby("Destination")[["DomesticVisitors", "ForeignVisitors"]]
        .sum()
        .nlargest(top_n, "DomesticVisitors")
        .reset_index()
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Domestic",
        x=dest_grp["Destination"],
        y=dest_grp["DomesticVisitors"],
        marker_color=PRIMARY_COLOR,
        hovertemplate="%{x}<br>Domestic: %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Foreign",
        x=dest_grp["Destination"],
        y=dest_grp["ForeignVisitors"],
        marker_color=SECONDARY_COLOR,
        hovertemplate="%{x}<br>Foreign: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack",
        title="Domestic vs Foreign Visitors by Destination",
        xaxis_title="Destination",
        yaxis_title="Visitor Count",
        **CHART_LAYOUT,
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)


def chart_monthly_trend(df: pd.DataFrame) -> str:
    """Line chart: total monthly visitor trend."""
    if df.empty:
        return _empty_chart("No data available")

    monthly = (
        df.groupby("Month")[["DomesticVisitors", "ForeignVisitors", "TotalVisitors"]]
        .sum()
        .reset_index()
        .sort_values("Month")
    )
    monthly["Label"] = monthly["Month"].dt.strftime("%b %Y")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["Label"], y=monthly["TotalVisitors"],
        name="Total", mode="lines+markers",
        line=dict(color=PRIMARY_COLOR, width=2.5),
        marker=dict(size=6),
        hovertemplate="%{x}<br>Total: %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=monthly["Label"], y=monthly["DomesticVisitors"],
        name="Domestic", mode="lines+markers",
        line=dict(color=SECONDARY_COLOR, width=2, dash="dot"),
        marker=dict(size=5),
        hovertemplate="%{x}<br>Domestic: %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=monthly["Label"], y=monthly["ForeignVisitors"],
        name="Foreign", mode="lines+markers",
        line=dict(color="#D97706", width=2, dash="dash"),
        marker=dict(size=5),
        hovertemplate="%{x}<br>Foreign: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title="Monthly Visitor Footfall Trend",
        xaxis_title="Month",
        yaxis_title="Visitor Count",
        **CHART_LAYOUT,
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)


def chart_top_destinations(df: pd.DataFrame, top_n: int = 10) -> str:
    """Horizontal bar: top destinations by total visitors."""
    if df.empty:
        return _empty_chart("No data available")

    dest_totals = (
        df.groupby("Destination")["TotalVisitors"]
        .sum()
        .nlargest(top_n)
        .reset_index()
        .sort_values("TotalVisitors")
    )

    fig = go.Figure(go.Bar(
        x=dest_totals["TotalVisitors"],
        y=dest_totals["Destination"],
        orientation="h",
        marker_color=PRIMARY_COLOR,
        hovertemplate="%{y}<br>Total: %{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Top {top_n} Destinations by Total Visitors",
        xaxis_title="Total Visitors",
        yaxis_title="",
        **CHART_LAYOUT,
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)


def chart_state_comparison(df: pd.DataFrame) -> str:
    """Bar chart: visitor totals by state."""
    if df.empty:
        return _empty_chart("No data available")

    state_grp = (
        df.groupby("State")[["DomesticVisitors", "ForeignVisitors"]]
        .sum()
        .reset_index()
        .sort_values("DomesticVisitors", ascending=False)
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Domestic",
        x=state_grp["State"],
        y=state_grp["DomesticVisitors"],
        marker_color=PRIMARY_COLOR,
        hovertemplate="%{x}<br>Domestic: %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Foreign",
        x=state_grp["State"],
        y=state_grp["ForeignVisitors"],
        marker_color=SECONDARY_COLOR,
        hovertemplate="%{x}<br>Foreign: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        barmode="group",
        title="State-wise Visitor Comparison",
        xaxis_title="State",
        yaxis_title="Visitor Count",
        **CHART_LAYOUT,
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)


def chart_seasonal_comparison(df: pd.DataFrame) -> str:
    """Bar chart: total footfall by season."""
    if df.empty:
        return _empty_chart("No data available")

    season_grp = (
        df.groupby("Season")[["DomesticVisitors", "ForeignVisitors", "TotalVisitors"]]
        .sum()
        .reindex([s for s in SEASON_ORDER if s in df["Season"].unique()])
        .reset_index()
    )

    season_colors = {
        "Winter": "#2563EB",
        "Summer": "#D97706",
        "Monsoon": "#059669",
        "Autumn": "#DC2626",
    }
    colors = [season_colors.get(s, PRIMARY_COLOR) for s in season_grp["Season"]]

    fig = go.Figure(go.Bar(
        x=season_grp["Season"],
        y=season_grp["TotalVisitors"],
        marker_color=colors,
        hovertemplate="%{x}<br>Total: %{y:,.0f}<extra></extra>",
        text=season_grp["TotalVisitors"].apply(lambda v: f"{v/1e6:.1f}M"),
        textposition="outside",
    ))
    fig.update_layout(
        title="Total Visitor Footfall by Season",
        xaxis_title="Season",
        yaxis_title="Total Visitors",
        **CHART_LAYOUT,
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)


def chart_hotel_occupancy(df: pd.DataFrame, top_n: int = 12) -> str:
    """Bar chart: average hotel occupancy by destination."""
    if df.empty:
        return _empty_chart("No data available")

    occ = (
        df.groupby("Destination")["HotelOccupancyPct"]
        .mean()
        .nlargest(top_n)
        .reset_index()
        .sort_values("HotelOccupancyPct")
    )
    occ["HotelOccupancyPct"] = occ["HotelOccupancyPct"].round(1)

    fig = go.Figure(go.Bar(
        x=occ["HotelOccupancyPct"],
        y=occ["Destination"],
        orientation="h",
        marker=dict(
            color=occ["HotelOccupancyPct"],
            colorscale=[[0, "#bfdbfe"], [1, "#1d4ed8"]],
            showscale=True,
            colorbar=dict(title="Occ. %"),
        ),
        hovertemplate="%{y}<br>Avg Occupancy: %{x:.1f}%<extra></extra>",
        text=occ["HotelOccupancyPct"].astype(str) + "%",
        textposition="inside",
    ))
    fig.update_layout(
        title="Average Hotel Occupancy by Destination",
        xaxis_title="Occupancy (%)",
        yaxis_title="",
        **CHART_LAYOUT,
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)


def chart_foreign_contribution(df: pd.DataFrame) -> str:
    """Pie chart: domestic vs foreign visitor share."""
    if df.empty:
        return _empty_chart("No data available")

    domestic = int(df["DomesticVisitors"].sum())
    foreign = int(df["ForeignVisitors"].sum())

    fig = go.Figure(go.Pie(
        labels=["Domestic Visitors", "Foreign Visitors"],
        values=[domestic, foreign],
        marker=dict(colors=[PRIMARY_COLOR, SECONDARY_COLOR]),
        hole=0.38,
        hovertemplate="%{label}<br>Count: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        textinfo="label+percent",
        insidetextfont=dict(size=12),
    ))
    fig.update_layout(
        title="Domestic vs Foreign Visitor Contribution",
        **CHART_LAYOUT,
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)


def _empty_chart(message: str) -> str:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="#6b7280"),
    )
    fig.update_layout(**CHART_LAYOUT)
    return json.dumps(fig, cls=PlotlyJSONEncoder)


# ─────────────────────────────────────────────
# INSIGHTS GENERATOR
# ─────────────────────────────────────────────

def generate_insights(df: pd.DataFrame) -> list[dict]:
    """
    Compute data-driven insights from the dataset.
    Returns a list of insight dicts with 'title', 'detail', 'category'.
    All values are derived from df — no hard-coded conclusions.
    """
    if df.empty:
        return [{"title": "No data", "detail": "Load a dataset to see insights.", "category": "info"}]

    insights = []

    # 1. Peak tourist month
    monthly = df.groupby("MonthLabel")["TotalVisitors"].sum()
    peak_month = monthly.idxmax()
    peak_val = int(monthly.max())
    insights.append({
        "title": "Peak Tourist Month",
        "detail": (
            f"<strong>{peak_month}</strong> recorded the highest footfall with "
            f"<strong>{peak_val:,}</strong> total visitors across all destinations."
        ),
        "category": "peak",
    })

    # 2. Lowest footfall month
    low_month = monthly.idxmin()
    low_val = int(monthly.min())
    insights.append({
        "title": "Lowest Footfall Month",
        "detail": (
            f"<strong>{low_month}</strong> had the lowest tourist activity with "
            f"<strong>{low_val:,}</strong> visitors — "
            f"{round((1 - low_val/peak_val) * 100, 1)}% lower than the peak month."
        ),
        "category": "low",
    })

    # 3. Top destination
    dest_totals = df.groupby("Destination")["TotalVisitors"].sum()
    top_dest = dest_totals.idxmax()
    top_dest_val = int(dest_totals.max())
    insights.append({
        "title": "Most Visited Destination",
        "detail": (
            f"<strong>{top_dest}</strong> is the most visited destination with "
            f"<strong>{top_dest_val:,}</strong> total visitors across the data period."
        ),
        "category": "top",
    })

    # 4. Least visited destination
    least_dest = dest_totals.idxmin()
    least_dest_val = int(dest_totals.min())
    insights.append({
        "title": "Least Visited Destination",
        "detail": (
            f"<strong>{least_dest}</strong> recorded the fewest visitors "
            f"(<strong>{least_dest_val:,}</strong>), suggesting potential for "
            f"targeted promotional campaigns."
        ),
        "category": "low",
    })

    # 5. Highest foreign visitors destination
    foreign_dest = df.groupby("Destination")["ForeignVisitors"].sum()
    top_foreign_dest = foreign_dest.idxmax()
    top_foreign_val = int(foreign_dest.max())
    insights.append({
        "title": "Top Destination for Foreign Visitors",
        "detail": (
            f"<strong>{top_foreign_dest}</strong> attracts the most international tourists "
            f"(<strong>{top_foreign_val:,}</strong> foreign visitors), "
            f"indicating strong global appeal."
        ),
        "category": "foreign",
    })

    # 6. Foreign visitor share
    total_dom = int(df["DomesticVisitors"].sum())
    total_for = int(df["ForeignVisitors"].sum())
    total_all = total_dom + total_for
    foreign_pct = round(total_for / total_all * 100, 1)
    insights.append({
        "title": "Domestic vs Foreign Visitor Split",
        "detail": (
            f"Domestic visitors account for <strong>{100 - foreign_pct}%</strong> "
            f"(<strong>{total_dom:,}</strong>) of total footfall, while foreign "
            f"visitors contribute <strong>{foreign_pct}%</strong> "
            f"(<strong>{total_for:,}</strong>)."
        ),
        "category": "info",
    })

    # 7. Peak season
    season_totals = df.groupby("Season")["TotalVisitors"].sum()
    peak_season = season_totals.idxmax()
    peak_season_val = int(season_totals.max())
    insights.append({
        "title": "Peak Tourist Season",
        "detail": (
            f"The <strong>{peak_season}</strong> season records the highest overall footfall "
            f"(<strong>{peak_season_val:,}</strong> visitors), making it the primary "
            f"planning period for tourism authorities."
        ),
        "category": "peak",
    })

    # 8. Monsoon vs Winter comparison
    if "Monsoon" in season_totals.index and "Winter" in season_totals.index:
        monsoon_val = int(season_totals["Monsoon"])
        winter_val = int(season_totals["Winter"])
        diff_pct = round((winter_val - monsoon_val) / monsoon_val * 100, 1)
        insights.append({
            "title": "Winter vs Monsoon Season Contrast",
            "detail": (
                f"Winter footfall (<strong>{winter_val:,}</strong>) exceeds Monsoon footfall "
                f"(<strong>{monsoon_val:,}</strong>) by <strong>{diff_pct}%</strong>, "
                f"highlighting clear seasonal demand patterns."
            ),
            "category": "seasonal",
        })

    # 9. Highest hotel occupancy destination
    avg_occ = df.groupby("Destination")["HotelOccupancyPct"].mean()
    top_occ_dest = avg_occ.idxmax()
    top_occ_val = round(avg_occ.max(), 1)
    insights.append({
        "title": "Highest Hotel Occupancy",
        "detail": (
            f"<strong>{top_occ_dest}</strong> maintains the highest average hotel occupancy "
            f"at <strong>{top_occ_val}%</strong>, indicating strong and consistent demand "
            f"for accommodation at this destination."
        ),
        "category": "occupancy",
    })

    # 10. Leading state
    state_totals = df.groupby("State")["TotalVisitors"].sum()
    top_state = state_totals.idxmax()
    top_state_val = int(state_totals.max())
    insights.append({
        "title": "Highest Tourism Activity State",
        "detail": (
            f"<strong>{top_state}</strong> leads all states with "
            f"<strong>{top_state_val:,}</strong> total visitors, driven by its "
            f"high-profile destinations and tourism infrastructure."
        ),
        "category": "state",
    })

    return insights


# ─────────────────────────────────────────────
# RECOMMENDATIONS GENERATOR
# ─────────────────────────────────────────────

def generate_recommendations(df: pd.DataFrame) -> list[dict]:
    """
    Generate data-driven policy/planning recommendations.
    All recommendations are derived from actual dataset findings.
    These are not official government recommendations.
    """
    if df.empty:
        return []

    recs = []

    # 1. Infrastructure at top destination
    top_dest = df.groupby("Destination")["TotalVisitors"].sum().idxmax()
    recs.append({
        "area": "Infrastructure Development",
        "recommendation": (
            f"Prioritise infrastructure expansion at <strong>{top_dest}</strong> — "
            f"including transport connectivity, crowd management systems, and visitor "
            f"amenity upgrades — to sustainably accommodate its high footfall volume."
        ),
        "icon": "🏗️",
    })

    # 2. Accommodation at high-occupancy destinations
    avg_occ = df.groupby("Destination")["HotelOccupancyPct"].mean()
    high_occ_dests = avg_occ[avg_occ >= avg_occ.quantile(0.75)].index.tolist()
    recs.append({
        "area": "Accommodation Capacity",
        "recommendation": (
            f"Destinations including <strong>{', '.join(high_occ_dests[:3])}</strong> "
            f"consistently show high hotel occupancy (above 75th percentile). "
            f"Expand budget and mid-range accommodation options to reduce demand pressure "
            f"and improve tourist experience."
        ),
        "icon": "🏨",
    })

    # 3. Promote low-season destinations
    season_totals = df.groupby("Season")["TotalVisitors"].sum()
    low_season = season_totals.idxmin()
    recs.append({
        "area": "Seasonal Planning",
        "recommendation": (
            f"The <strong>{low_season}</strong> season shows the lowest footfall. "
            f"Develop targeted off-season promotional packages, festivals, and incentive "
            f"schemes to distribute tourist load more evenly throughout the year."
        ),
        "icon": "📅",
    })

    # 4. Promote least visited destinations
    least_dest = df.groupby("Destination")["TotalVisitors"].sum().idxmin()
    least_state_dest = df[df["Destination"] == least_dest]["State"].iloc[0]
    recs.append({
        "area": "Promotional Activities",
        "recommendation": (
            f"<strong>{least_dest}</strong> ({least_state_dest}) shows significant untapped "
            f"tourism potential. Invest in digital marketing campaigns, influencer collaborations, "
            f"and heritage storytelling to raise its visibility among domestic and international tourists."
        ),
        "icon": "📢",
    })

    # 5. Foreign tourist facilities
    top_foreign = df.groupby("Destination")["ForeignVisitors"].sum().idxmax()
    recs.append({
        "area": "Tourist Facilities for International Visitors",
        "recommendation": (
            f"<strong>{top_foreign}</strong> attracts the highest number of international tourists. "
            f"Enhance multilingual signage, guided tour availability, foreign currency exchange "
            f"facilities, and visa-on-arrival support services at this destination."
        ),
        "icon": "🌐",
    })

    # 6. Transportation in peak season
    peak_season = season_totals.idxmax()
    recs.append({
        "area": "Transportation & Support Facilities",
        "recommendation": (
            f"During the <strong>{peak_season}</strong> season, transportation networks at major "
            f"tourist hubs face maximum load. Plan for increased public transport frequency, "
            f"pre-booked shuttle services, and temporary visitor information kiosks during peak months."
        ),
        "icon": "🚌",
    })

    return recs


# ─────────────────────────────────────────────
# DESTINATIONS TABLE DATA
# ─────────────────────────────────────────────

def destinations_table(df: pd.DataFrame) -> list[dict]:
    """Aggregate per-destination statistics for the destinations page table."""
    if df.empty:
        return []

    agg = (
        df.groupby(["Destination", "State"])
        .agg(
            DomesticVisitors=("DomesticVisitors", "sum"),
            ForeignVisitors=("ForeignVisitors", "sum"),
            TotalVisitors=("TotalVisitors", "sum"),
            HotelOccupancyPct=("HotelOccupancyPct", "mean"),
        )
        .reset_index()
    )
    agg["HotelOccupancyPct"] = agg["HotelOccupancyPct"].round(1)

    max_total = agg["TotalVisitors"].max()
    agg["IsTopTier"] = agg["TotalVisitors"] >= (max_total * 0.6)

    return agg.sort_values("TotalVisitors", ascending=False).to_dict("records")


# ─────────────────────────────────────────────
# REPORT DATA BUILDER
# ─────────────────────────────────────────────

def build_report_data(df: pd.DataFrame) -> dict:
    """Compile all data needed for the downloadable report."""
    summary = compute_summary(df)
    insights = generate_insights(df)
    recs = generate_recommendations(df)

    # Top 5 destinations
    top5 = (
        df.groupby("Destination")["TotalVisitors"]
        .sum()
        .nlargest(5)
        .reset_index()
    )
    top5["TotalVisitors"] = top5["TotalVisitors"].astype(int)

    # Seasonal summary
    seasonal = (
        df.groupby("Season")[["DomesticVisitors", "ForeignVisitors", "TotalVisitors"]]
        .sum()
        .reset_index()
        .to_dict("records")
    )

    return {
        "summary": summary,
        "insights": insights,
        "recommendations": recs,
        "top5_destinations": top5.to_dict("records"),
        "seasonal_summary": seasonal,
    }
