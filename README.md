# YatraLens — Tourism Data Analytics & Insights
### A Python-Based Web Application for PBL (Project-Based Learning)

---

## Project Overview

**YatraLens** is a web-based Tourism Data Analytics application built using Python (Flask) and Plotly.
It allows tourism departments and analysts to study visitor statistics, identify seasonal trends, compare destinations, and generate data-driven insights and recommendations — all from a CSV file.

This project was developed as a **PBL (Project-Based Learning)** submission demonstrating practical application of data analysis, visualization, and web development skills.

---

## Problem Statement

Tourism departments analyze visitor statistics to plan infrastructure and promotional activities.
This application studies tourism datasets to:
- Identify **seasonal trends** in visitor footfall
- Find **popular and underperforming destinations**
- Understand **visitor demographics** (domestic vs. foreign)
- Provide **data-driven recommendations** for tourism policy

---

## Features

| Feature | Description |
|---|---|
| **Dashboard** | KPI cards: Total Visitors, Domestic, Foreign, Avg Occupancy, Top Destination |
| **Analytics** | 7 interactive Plotly charts with full hover/zoom support |
| **Destinations** | Sortable table of all destinations with occupancy bars |
| **Insights** | 10 auto-computed data-driven insights from the live dataset |
| **Recommendations** | 6 planning recommendations derived from findings |
| **Report** | Printable/PDF analytics report with charts and tables |
| **CSV Upload** | Upload custom dataset with validation and error reporting |
| **Filters** | State, Destination, Month, Season filters — update all views |
| **Demo Data** | Built-in realistic sample data for 15 Indian destinations × 12 months |

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+, Flask 3.x |
| **Data Analysis** | Pandas, NumPy |
| **Visualization** | Plotly (Python for chart generation, Plotly.js for rendering) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Data Format** | CSV |

---

## Project Structure

```
yatralens/
│
├── app.py                        ← Flask application (routes, API endpoints)
├── requirements.txt              ← Python dependencies
├── README.md                     ← This file
│
├── data/
│   └── tourism_statistics.csv    ← Demo dataset (15 destinations × 12 months)
│
├── templates/
│   ├── base.html                 ← Shared layout (sidebar, header)
│   ├── dashboard.html            ← Dashboard with KPI cards + quick charts
│   ├── analytics.html            ← 7 interactive charts page
│   ├── destinations.html         ← Sortable destinations data table
│   ├── insights.html             ← Insights + Recommendations page
│   ├── report.html               ← Printable report
│   └── upload.html               ← CSV upload interface
│
├── static/
│   ├── css/style.css             ← Main stylesheet
│   └── js/app.js                 ← Chart rendering, table sort, drag-drop
│
└── analysis/
    ├── __init__.py
    └── tourism_analysis.py       ← Core analysis: cleaning, charts, insights
```

---

## Dataset Structure

Your CSV must have these exact column headers:

| Column | Description | Example |
|---|---|---|
| `DestinationID` | Unique ID for destination | `TOU-101` |
| `Destination` | Destination name | `Taj Mahal` |
| `State` | Indian state name | `Uttar Pradesh` |
| `Month` | Year-Month in YYYY-MM format | `2025-01` |
| `DomesticVisitors` | Number of domestic visitors | `320000` |
| `ForeignVisitors` | Number of foreign visitors | `85000` |
| `HotelOccupancyPct` | Hotel occupancy percentage | `95.0` |

**Example row:**
```csv
TOU-104,Taj Mahal,Uttar Pradesh,2025-01,320000,85000,95.0
```

---

## Installation

### Step 1: Clone / Open the project folder
```bash
cd yatralens
```

### Step 2: Create a virtual environment (recommended)
```bash
python -m venv venv
venv\Scripts\activate      # Windows
# or: source venv/bin/activate  (Linux/Mac)
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

---

## How to Run

```bash
python app.py
```

Then open your browser at: **http://localhost:5000**

The application starts with the demo dataset loaded automatically.

---

## How to Upload Your CSV

1. Navigate to **Dataset / Upload** in the sidebar
2. Drag and drop your `.csv` file onto the upload zone (or click to browse)
3. Click **Upload and Analyse**
4. The application validates required columns — clear error messages appear if any are missing
5. On success, all pages update to use your dataset immediately

To switch back to the demo dataset, click **Use Demo Data** in the sidebar.

---

## How Analysis Works

### Data Loading (`load_and_clean`)
- Reads the CSV using `pd.read_csv()`
- Parses `Month` column as `datetime` with format `%Y-%m`
- Converts `DomesticVisitors`, `ForeignVisitors`, `HotelOccupancyPct` to numeric
- Drops rows with invalid/missing visitor counts
- Fills missing occupancy values with the dataset median

### TotalVisitors Calculation
```python
df["TotalVisitors"] = df["DomesticVisitors"] + df["ForeignVisitors"]
```

### Season Derivation
```python
MONTH_TO_SEASON = {
    1: "Winter", 2: "Winter",       # Nov-Feb: peak travel season
    3: "Summer", 4: "Summer", 5: "Summer",
    6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Autumn",                   # Post-monsoon recovery
    11: "Winter", 12: "Winter",
}
df["Season"] = df["MonthNum"].map(MONTH_TO_SEASON)
```

### Grouping / Aggregation
```python
# Top destination
df.groupby("Destination")["TotalVisitors"].sum().idxmax()

# State comparison
df.groupby("State")[["DomesticVisitors", "ForeignVisitors"]].sum()

# Seasonal totals
df.groupby("Season")["TotalVisitors"].sum()
```

---

## How Charts Are Generated

Charts are created using **Plotly Graph Objects** in `analysis/tourism_analysis.py` and serialised to JSON:

```python
import plotly.graph_objects as go
import json
from plotly.utils import PlotlyJSONEncoder

fig = go.Figure(go.Bar(...))
chart_json = json.dumps(fig, cls=PlotlyJSONEncoder)
```

The JSON is passed to the template via Jinja2, and rendered in the browser using **Plotly.js**:

```javascript
const fig = JSON.parse(chartJsonString);
Plotly.newPlot(element, fig.data, fig.layout, { responsive: true });
```

---

## How Insights Are Calculated

Each insight is computed dynamically from the filtered dataset:

| Insight | Pandas Operation |
|---|---|
| Peak month | `groupby("MonthLabel")["TotalVisitors"].sum().idxmax()` |
| Top destination | `groupby("Destination")["TotalVisitors"].sum().idxmax()` |
| Foreign contribution | `ForeignVisitors.sum() / TotalVisitors.sum() * 100` |
| Peak season | `groupby("Season")["TotalVisitors"].sum().idxmax()` |
| Highest occupancy | `groupby("Destination")["HotelOccupancyPct"].mean().idxmax()` |

---

## How Recommendations Are Derived

Recommendations are generated by inspecting the computed insights:
- High-occupancy destinations (above 75th percentile) → accommodation expansion recommendation
- Low-season identification → off-season promotion recommendation
- Least visited destination → targeted marketing recommendation
- Top foreign visitor destination → international facility improvement recommendation

---

## How Report Generation Works

The `/report` page assembles:
- Summary statistics (from `compute_summary()`)
- Top 5 destinations table (from `build_report_data()`)
- Seasonal footfall table
- All computed insights
- All recommendations
- 4 Plotly charts embedded inline

Clicking **Print / Save as PDF** triggers `window.print()` — the print stylesheet hides the sidebar and navigation automatically.

---

## PBL Implementation Mapping

| PBL Requirement | Implementation in YatraLens |
|---|---|
| **1. Visitor Data Parsing** | `load_and_clean()` in `tourism_analysis.py` — reads CSV, validates types, handles missing values |
| **2. Seasonal Footfall Analysis** | `MONTH_TO_SEASON` mapping derives Season; grouped by season for footfall comparison |
| **3. Tourism Footprint Charts** | 7 Plotly charts: bar, stacked bar, line, pie, horizontal bar, grouped bar, occupancy heatbar |
| **4. Tourism Policy Recommendation** | `generate_recommendations()` derives 6 planning suggestions from dataset findings |

---

## PBL Evaluation Coverage

| Evaluation Area | Weight | Coverage |
|---|---|---|
| Python Implementation | 20% | Flask backend, Pandas processing, Plotly generation (`app.py`, `tourism_analysis.py`) |
| Data Analysis | 15% | Groupby, aggregation, seasonal analysis, occupancy analysis, footfall analysis |
| Visualization & Interpretation | 15% | 7 interactive Plotly charts with hover, legends, meaningful titles |
| Documentation & Report | 10% | This README + printable in-app report with insights and tables |
| Requirement Analysis | 10% | All specified analyses implemented: visitor footfall, seasonal, destination, state, foreign, occupancy |
| Dataset Selection & Quality | 10% | 15 Indian destinations × 12 months × 7 columns = 180 rows realistic demo data |
| Presentation & Viva | 10% | Clean UI, sidebar navigation, explainable code, analysis notes in the app |
| Problem Understanding | 10% | Problem statement directly addressed: seasonal trends, popular destinations, visitor demographics |

---

## Important Notes

- The demo dataset (`tourism_statistics.csv`) is **sample data created for demonstration purposes**.
- It is **not** official government statistics.
- Insights and recommendations are **algorithmically derived** from the loaded data — not hard-coded.
- The application requires no internet connection after initial setup (Plotly.js loaded from CDN on first use; cached by browser).

---

*YatraLens · Tourism Data Analytics · PBL Academic Project*
