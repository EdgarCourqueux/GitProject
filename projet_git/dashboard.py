import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import subprocess
import datetime
import pytz
import os

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
MAX_DATA_POINTS = 100

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
    """Ensure required files exist."""
    for file_path in [DATA_FILE, REPORT_FILE]:
        if not os.path.exists(file_path):
            open(file_path, 'a').close()
            print(f"Created file: {file_path}")

def load_data():
    """Load data from CSV file with error handling."""
    try:
        df = pd.read_csv(DATA_FILE, names=["Timestamp", "Price"], header=None)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df = df.dropna().sort_values("Timestamp")
        return df.tail(MAX_DATA_POINTS)
    except Exception as e:
        print(f"❌ Data loading error: {e}")
        return pd.DataFrame(columns=["Timestamp", "Price"])

def load_daily_report():
    """Load the daily report from the CSV file with precise timestamp."""
    try:
        cols = ["Timestamp", "Open", "Close", "Max", "Min", "Evolution"]
        df = pd.read_csv(REPORT_FILE, names=cols, header=None)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        
        # If no data, return a default/empty report
        if df.empty:
            now = datetime.datetime.now()
            return pd.Series({
                "Timestamp": now,
                "Open": 0,
                "Close": 0,
                "Max": 0,
                "Min": 0,
                "Evolution": "0%"
            })
        
        return df.iloc[-1]  # Return the most recent report
    except Exception as e:
        print(f"❌ Report loading error: {e}")
        return None

@app.callback(
    [Output("price-graph", "figure"),
     Output("current-price", "children"),
     Output("daily-report", "children")],  # Combined outputs
    [Input("graph-update", "n_intervals")]
)

def create_price_graph(df):
    """Create a responsive and visually appealing price graph."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["Timestamp"],
        y=df["Price"],
        mode='lines+markers',
        name='Bitcoin Price',
        line=dict(color=COLORS["bitcoin"], width=2.5),
        marker=dict(size=5, color=COLORS["bitcoin"], opacity=0.7),
        fill='tozeroy',
        fillcolor=f'rgba({242}, {169}, {0}, 0.1)'
    ))
    
    fig.update_layout(
        title="Bitcoin Price Trend",
        plot_bgcolor=COLORS["background"],
        paper_bgcolor=COLORS["background"],
        font=dict(family="Arial, sans-serif", color=COLORS["text"]),
        xaxis=dict(
            title="Time",
            showgrid=True,
            gridcolor=COLORS["grid"],
            tickangle=-45
        ),
        yaxis=dict(
            title="Price (USD)",
            showgrid=True,
            gridcolor=COLORS["grid"],
            tickprefix="$"
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode="x unified"
    )
    
    return fig

# Dashboard Layout (unchanged from previous version)
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
def update_graph_and_price(n):
    """Update graph and current price."""
    try:
        subprocess.run(["/bin/bash", "/app/scraper.sh"], check=True)
    except Exception as e:
        print(f"❌ Scraper script error: {e}")
    
    df = load_data()
    
    if df.empty:
        return go.Figure(), "N/A"
    
    fig = create_price_graph(df)
    current_price = f"${df['Price'].iloc[-1]:,.2f}"
    
    return fig, current_price

@app.callback(
    Output("daily-report", "children"),
    Input("report-update", "n_intervals")
)
def update_daily_report(n, figure):
    """Update daily report section with each graph update."""
    try:
        # Run the daily report script to regenerate the report
        subprocess.run(["/bin/bash", "/app/daily_report.sh"], check=True)
    except Exception as e:
        print(f"❌ Daily report script error: {e}")
    
    report = load_daily_report()
    
    if report is None:
        return html.Div("No report available")
    
    return html.Div([
        html.H3("Daily Bitcoin Report", className="report-title"),
        html.Div([
            html.Div([
                html.Span("Timestamp", className="report-label"),
                html.Span(report["Timestamp"].strftime("%Y-%m-%d %H:%M:%S"), className="report-value")
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

# Rest of the CSS remains the same as in previous version

# Ensure files exist before running
ensure_files_exist()

# Custom Index String with Dark Mode Styling
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        <title>Bitcoin Live Dashboard</title>
        {%metas%}
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 0;
                background-color: #1C1C1E;
                color: #FFFFFF;
                line-height: 1.6;
            }
            .dashboard-container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 30px;
            }
            .dashboard-title {
                color: #F7931A;
                font-size: 32px;
                font-weight: 700;
                margin-bottom: 20px;
                text-align: center;
            }
            .current-price {
                text-align: center;
                font-size: 48px;
                font-weight: 600;
                color: #F7931A;
                margin-bottom: 30px;
            }
            .content-wrapper {
                display: flex;
                gap: 30px;
            }
            .graph-container {
                flex: 2;
                background-color: #2C2C2E;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            }
            .report-container {
                flex: 1;
                background-color: #2C2C2E;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            }
            .report-title {
                color: #F7931A;
                font-size: 24px;
                margin-bottom: 20px;
                border-bottom: 2px solid #F7931A;
                padding-bottom: 10px;
            }
            .report-grid {
                display: grid;
                gap: 15px;
            }
            .report-item {
                display: flex;
                justify-content: space-between;
                padding: 10px;
                background-color: #1C1C1E;
                border-radius: 8px;
            }
            .report-label {
                color: #B0B0B0;
                font-size: 14px;
            }
            .report-value {
                color: #FFFFFF;
                font-weight: 600;
            }
            @media (max-width: 768px) {
                .content-wrapper {
                    flex-direction: column;
                }
                .current-price {
                    font-size: 36px;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# Ensure files exist before running
ensure_files_exist()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
