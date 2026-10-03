"""
YatraLens – Flask Application Entry Point
==========================================
Tourism Data Analytics & Insights
"""

import os
import json
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, flash, session
)
from werkzeug.utils import secure_filename

import pandas as pd

from analysis.tourism_analysis import (
    load_and_clean, validate_columns, apply_filters,
    compute_summary, destinations_table,
    generate_insights, generate_recommendations, build_report_data,
    chart_domestic_foreign_stacked, chart_monthly_trend,
    chart_top_destinations, chart_state_comparison,
    chart_seasonal_comparison, chart_hotel_occupancy,
    chart_foreign_contribution,
)

# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "yatralens-pbl-2025"

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DEMO_CSV = DATA_DIR / "tourism_statistics.csv"
UPLOAD_FOLDER = DATA_DIR
ALLOWED_EXTENSIONS = {"csv"}

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB limit

# Track which file is currently active (default = demo)
ACTIVE_FILE_KEY = "active_csv_path"
DEMO_LABEL = "Demo Dataset (tourism_statistics.csv)"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_active_path() -> str:
    """Return path of currently active CSV."""
    return session.get(ACTIVE_FILE_KEY, str(DEMO_CSV))


def load_df() -> pd.DataFrame:
    path = get_active_path()
    if not Path(path).exists():
        session.pop(ACTIVE_FILE_KEY, None)
        path = str(DEMO_CSV)
    return load_and_clean(path)


def get_filter_options(df: pd.DataFrame) -> dict:
    """Extract unique filter values from the full (unfiltered) dataset."""
    months = sorted(df["MonthLabel"].unique().tolist(),
                    key=lambda x: pd.to_datetime(x, format="%b %Y"))
    return {
        "states": ["All"] + sorted(df["State"].unique().tolist()),
        "destinations": ["All"] + sorted(df["Destination"].unique().tolist()),
        "months": ["All"] + months,
        "seasons": ["All"] + ["Winter", "Summer", "Autumn", "Monsoon"],
    }


def read_filters() -> dict:
    return {
        "state": request.args.get("state", "All"),
        "destination": request.args.get("destination", "All"),
        "month": request.args.get("month", "All"),
        "season": request.args.get("season", "All"),
    }


def is_demo() -> bool:
    return get_active_path() == str(DEMO_CSV)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    df_full = load_df()
    filters = read_filters()
    df = apply_filters(df_full, **filters)
    summary = compute_summary(df)
    options = get_filter_options(df_full)
    charts = {
        "monthly_trend": chart_monthly_trend(df),
        "seasonal": chart_seasonal_comparison(df),
        "top_destinations": chart_top_destinations(df, top_n=8),
        "foreign_pie": chart_foreign_contribution(df),
    }
    return render_template(
        "dashboard.html",
        summary=summary,
        filters=filters,
        options=options,
        charts=charts,
        is_demo=is_demo(),
        active_page="dashboard",
    )


@app.route("/analytics")
def analytics():
    df_full = load_df()
    filters = read_filters()
    df = apply_filters(df_full, **filters)
    options = get_filter_options(df_full)

    charts = {
        "monthly_trend": chart_monthly_trend(df),
        "stacked_bar": chart_domestic_foreign_stacked(df),
        "top_destinations": chart_top_destinations(df),
        "state_comparison": chart_state_comparison(df),
        "seasonal": chart_seasonal_comparison(df),
        "occupancy": chart_hotel_occupancy(df),
        "foreign_pie": chart_foreign_contribution(df),
    }

    return render_template(
        "analytics.html",
        charts=charts,
        filters=filters,
        options=options,
        is_demo=is_demo(),
        active_page="analytics",
    )


@app.route("/destinations")
def destinations():
    df_full = load_df()
    filters = read_filters()
    df = apply_filters(df_full, **filters)
    options = get_filter_options(df_full)
    table_data = destinations_table(df)
    return render_template(
        "destinations.html",
        table_data=table_data,
        filters=filters,
        options=options,
        is_demo=is_demo(),
        active_page="destinations",
    )


@app.route("/insights")
def insights():
    df_full = load_df()
    filters = read_filters()
    df = apply_filters(df_full, **filters)
    options = get_filter_options(df_full)
    insight_list = generate_insights(df)
    recs = generate_recommendations(df)
    return render_template(
        "insights.html",
        insights=insight_list,
        recommendations=recs,
        filters=filters,
        options=options,
        is_demo=is_demo(),
        active_page="insights",
    )


@app.route("/report")
def report():
    df_full = load_df()
    filters = read_filters()
    df = apply_filters(df_full, **filters)
    options = get_filter_options(df_full)
    report_data = build_report_data(df)
    charts = {
        "monthly_trend": chart_monthly_trend(df),
        "top_destinations": chart_top_destinations(df, top_n=5),
        "seasonal": chart_seasonal_comparison(df),
        "foreign_pie": chart_foreign_contribution(df),
    }
    return render_template(
        "report.html",
        report=report_data,
        charts=charts,
        filters=filters,
        options=options,
        is_demo=is_demo(),
        active_page="report",
    )


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        if "csv_file" not in request.files:
            flash("No file part in the request.", "error")
            return redirect(url_for("upload"))

        file = request.files["csv_file"]
        if file.filename == "":
            flash("No file selected.", "error")
            return redirect(url_for("upload"))

        if not allowed_file(file.filename):
            flash("Invalid file type. Please upload a .csv file.", "error")
            return redirect(url_for("upload"))

        filename = secure_filename(file.filename)
        save_path = Path(app.config["UPLOAD_FOLDER"]) / filename
        file.save(str(save_path))

        # Validate columns
        try:
            temp_df = pd.read_csv(str(save_path))
            missing = validate_columns(temp_df)
            if missing:
                save_path.unlink(missing_ok=True)
                flash(
                    f"Upload failed. Missing required columns: {', '.join(sorted(missing))}. "
                    f"Please ensure your CSV has: DestinationID, Destination, State, Month, "
                    f"DomesticVisitors, ForeignVisitors, HotelOccupancyPct.",
                    "error",
                )
                return redirect(url_for("upload"))

            session[ACTIVE_FILE_KEY] = str(save_path)
            flash(
                f"✓ '{filename}' uploaded successfully. "
                f"Found {len(temp_df)} rows across {temp_df['Destination'].nunique()} destinations.",
                "success",
            )
            return redirect(url_for("dashboard"))

        except Exception as e:
            save_path.unlink(missing_ok=True)
            flash(f"Could not parse the file: {str(e)}", "error")
            return redirect(url_for("upload"))

    return render_template(
        "upload.html",
        is_demo=is_demo(),
        active_page="upload",
        active_file=Path(get_active_path()).name,
    )


@app.route("/use-demo")
def use_demo():
    """Switch back to the demo dataset."""
    session.pop(ACTIVE_FILE_KEY, None)
    flash("Switched to the demo dataset.", "success")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
# API Endpoints (used by JS for dynamic filter updates)
# ─────────────────────────────────────────────

@app.route("/api/summary")
def api_summary():
    df_full = load_df()
    filters = read_filters()
    df = apply_filters(df_full, **filters)
    return jsonify(compute_summary(df))


@app.route("/api/charts")
def api_charts():
    df_full = load_df()
    filters = read_filters()
    df = apply_filters(df_full, **filters)
    return jsonify({
        "monthly_trend": chart_monthly_trend(df),
        "stacked_bar": chart_domestic_foreign_stacked(df),
        "top_destinations": chart_top_destinations(df),
        "state_comparison": chart_state_comparison(df),
        "seasonal": chart_seasonal_comparison(df),
        "occupancy": chart_hotel_occupancy(df),
        "foreign_pie": chart_foreign_contribution(df),
    })


@app.route("/api/destinations")
def api_destinations():
    df_full = load_df()
    filters = read_filters()
    df = apply_filters(df_full, **filters)
    return jsonify(destinations_table(df))


@app.route("/api/insights")
def api_insights():
    df_full = load_df()
    filters = read_filters()
    df = apply_filters(df_full, **filters)
    return jsonify({
        "insights": generate_insights(df),
        "recommendations": generate_recommendations(df),
    })


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
