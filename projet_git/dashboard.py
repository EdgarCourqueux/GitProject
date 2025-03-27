import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import subprocess
import datetime
import pytz
import os
import numpy as np

# Application Initialization
app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)
server = app.server

# Configuration Constants
BASE_PATH = "/app"
DATA_FILE = os.path.join(BASE_PATH, "projet.csv")
REPORT_FILE = os.path.join(BASE_PATH, "daily_report.csv")
TZ_PARIS = pytz.timezone("Europe/Paris")
MAX_DATA_POINTS = 200  # Increased for more detailed view

# Design Theme
COLORS = {
    "background": "#f4f6f9",
    "text": "#2c3e50",
    "bitcoin": "#f2a900",
    "positive": "#2ecc71",
    "negative": "#e74c3c",
    "card_bg": "#ffffff",
    "grid": "#ecf0f1"
}

def ensure_files_exist():
    """Ensure required files exist with proper permissions."""
    for file_path in [DATA_FILE, REPORT_FILE]:
        try:
            # Create the file if it doesn't exist
            if not os.path.exists(file_path):
                open(file_path, 'a').close()
                print(f"Created file: {file_path}")
            
            # Ensure the file is writable
            os.chmod(file_path, 0o666)
        except Exception as e:
            print(f"Error ensuring file {file_path} exists: {e}")

def load_data():
    """Load data from CSV file with improved error handling and filtering."""
    try:
        # Load all data for today
        today = datetime.date.today().strftime("%Y-%m-%d")
        df = pd.read_csv(DATA_FILE, names=["Timestamp", "Price"], header=None)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        
        # Filter for today's data and remove any extreme outliers
        today_data = df[df["Timestamp"].dt.date == datetime.date.today()]
        
        if today_data.empty:
            return pd.DataFrame(columns=["Timestamp", "Price"])
        
        # Remove outliers using Interquartile Range (IQR) method
        Q1 = today_data["Price"].quantile(0.25)
        Q3 = today_data["Price"].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        filtered_data = today_data[
            (today_data["Price"] >= lower_bound) & 
            (today_data["Price"] <= upper_bound)
        ]
        
        return filtered_data.sort_values("Timestamp").tail(MAX_DATA_POINTS)
    
    except Exception as e:
        print(f"❌ Data loading error: {e}")
        return pd.DataFrame(columns=["Timestamp", "Price"])
# Dashboard Layout
def create_dashboard_layout():
    return html.Div([
        html.Div([
            html.H1("Bitcoin Live Monitor", className="dashboard-title"),
            html.Div(id="current-price", className="current-price")
        ], className="dashboard-header"),
        
        html.Div([
            html.Div([
                dcc.Graph(id="price-graph", config={'displayModeBar': False})
            ], className="graph-container"),
            
            html.Div([
                html.Div(id="daily-report", className="report-container")
            ])
        ], className="content-wrapper")
    ], className="dashboard-container")

app.layout = html.Div([
    create_dashboard_layout(),
    dcc.Interval(id="graph-update", interval=60000),
    dcc.Interval(id="report-update", interval=3600000)
])

@app.callback(
    Output("price-graph", "figure"),
    Output("current-price", "children"),
    Input("graph-update", "n_intervals")
)
def load_daily_report():
    """Enhanced daily report loading with real-time calculations."""
    try:
        # Always generate a report for today
        today = datetime.date.today()
        data = load_data()
        
        if data.empty:
            return pd.Series({
                "Date": today,
                "Open": 0,
                "Close": 0,
                "Max": 0,
                "Min": 0,
                "Evolution": "0%"
            })
        
        open_price = data["Price"].iloc[0]
        close_price = data["Price"].iloc[-1]
        max_price = data["Price"].max()
        min_price = data["Price"].min()
        evolution = ((close_price - open_price) / open_price * 100)
        
        # Optionally, write the report to file for persistence
        report_data = f"{today},{open_price},{close_price},{max_price},{min_price},{evolution}%"
        with open(REPORT_FILE, 'w') as f:
            f.write(report_data)
        
        return pd.Series({
            "Date": today,
            "Open": open_price,
            "Close": close_price,
            "Max": max_price,
            "Min": min_price,
            "Evolution": f"{evolution:.2f}%"
        })
    
    except Exception as e:
        print(f"❌ Report loading error: {e}")
        return None

# Rest of the script remains the same as in the previous version...

# Modify the app layout to update the report more frequently
app.layout = html.Div([
    create_dashboard_layout(),
    dcc.Interval(id="graph-update", interval=60000),
    dcc.Interval(id="report-update", interval=60000)  # Changed to 1 minute
])

# Ensure the update_daily_report callback always runs
@app.callback(
    Output("daily-report", "children"),
    Input("report-update", "n_intervals")
)
def update_daily_report(n):
    """Update daily report section with real-time data."""
    # We don't need to run the bash script every time
    report = load_daily_report()
    
    if report is None:
        return html.Div("No report available")
    
    return html.Div([
        html.H3("Daily Bitcoin Report", className="report-title"),
        html.Div([
            html.Div([
                html.Span("Date", className="report-label"),
                html.Span(report["Date"].strftime("%Y-%m-%d"), className="report-value")
            ], className="report-item"),
            html.Div([
                html.Span("Open Price", className="report-label"),
                html.Span(f"${report['Open']:,.2f}", className="report-value")
            ], className="report-item"),
            html.Div([
                html.Span("Close Price", className="report-label"),
                html.Span(f"${report['Close']:,.2f}", className="report-value")
            ], className="report-item"),
            html.Div([
                html.Span("Maximum", className="report-label"),
                html.Span(f"${report['Max']:,.2f}", className="report-value")
            ], className="report-item"),
            html.Div([
                html.Span("Minimum", className="report-label"),
                html.Span(f"${report['Min']:,.2f}", className="report-value")
            ], className="report-item"),
            html.Div([
                html.Span("Evolution", className="report-label"),
                html.Span(str(report["Evolution"]), 
                          className="report-value", 
                          style={"color": COLORS["positive"] if float(str(report["Evolution"]).rstrip('%')) >= 0 else COLORS["negative"]})
            ], className="report-item")
        ], className="report-grid")
    ], className="report-container")

# Ensure files exist before running
ensure_files_exist()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
