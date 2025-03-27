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
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
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
    """Load the daily report from the CSV file."""
    try:
        cols = ["Date", "Open", "Close", "Max", "Min", "Evolution"]
        df = pd.read_csv(REPORT_FILE, names=cols, header=None)
        df["Date"] = pd.to_datetime(df["Date"])
        return df.iloc[-1]  # Return the most recent report
    except Exception as e:
        print(f"❌ Report loading error: {e}")
        return None

def create_price_graph(df):
    """Create a responsive and visually appealing price graph."""
    fig = go.Figure()
    
    # Price line
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
    
    # Customize layout
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

def create_dashboard_layout():
    """Create the dashboard layout with responsive design."""
    return html.Div([
        # Header
        html.Div([
            html.H1("Bitcoin Live Monitor", className="dashboard-title"),
            html.Div(id="current-price", className="current-price")
        ], className="dashboard-header"),
        
        # Main Content
        html.Div([
            # Price Graph
            html.Div([
                dcc.Graph(id="price-graph", config={'displayModeBar': False})
            ], className="graph-container"),
            
            # Daily Report
            html.Div([
                html.Div(id="daily-report", className="report-container")
            ])
        ], className="content-wrapper")
    ], className="dashboard-container")

# Dashboard Layout
app.layout = html.Div([
    create_dashboard_layout(),
    
    # Update Intervals
    dcc.Interval(id="graph-update", interval=60000),  # 1 minute
    dcc.Interval(id="report-update", interval=3600000)  # 1 hour
])

@app.callback(
    Output("price-graph", "figure"),
    Output("current-price", "children"),
    Input("graph-update", "n_intervals")
)
def update_graph_and_price(n):
    """Update graph and current price."""
    # Run scraper script
    try:
        subprocess.run(["bash", "scraper.sh"], check=True)
    except Exception as e:
        print(f"❌ Scraper script error: {e}")
    
    # Load data
    df = load_data()
    
    if df.empty:
        return go.Figure(), "N/A"
    
    # Create graph
    fig = create_price_graph(df)
    current_price = f"${df['Price'].iloc[-1]:,.2f}"
    
    return fig, current_price

@app.callback(
    Output("daily-report", "children"),
    Input("report-update", "n_intervals")
)
def update_daily_report(n):
    """Update daily report section."""
    # Run daily report script
    try:
        subprocess.run(["bash", "daily_report.sh"], check=True)
    except Exception as e:
        print(f"❌ Daily report script error: {e}")
    
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
                html.Span(report["Evolution"], 
                          className="report-value", 
                          style={"color": COLORS["positive"] if float(report["Evolution"].rstrip('%')) >= 0 else COLORS["negative"]})
            ], className="report-item")
        ], className="report-grid")
    ], className="report-container")

# Custom CSS for enhanced styling
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        <title>Bitcoin Live Monitor</title>
        {%metas%}
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Inter', sans-serif;
                background-color: #f4f6f9;
                margin: 0;
                padding: 0;
                color: #2c3e50;
            }
            .dashboard-container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .dashboard-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 2px solid #f2a900;
            }
            .dashboard-title {
                font-size: 28px;
                font-weight: 600;
                margin: 0;
            }
            .current-price {
                font-size: 24px;
                color: #f2a900;
                font-weight: 600;
            }
            .content-wrapper {
                display: flex;
                gap: 20px;
                flex-wrap: wrap;
            }
            .graph-container {
                flex: 2;
                min-width: 500px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                padding: 15px;
            }
            .report-container {
                flex: 1;
                min-width: 300px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                padding: 20px;
            }
            .report-title {
                margin-bottom: 15px;
                color: #2c3e50;
                border-bottom: 1px solid #ecf0f1;
                padding-bottom: 10px;
            }
            .report-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }
            .report-item {
                display: flex;
                flex-direction: column;
                background-color: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
            }
            .report-label {
                font-size: 12px;
                color: #7f8c8d;
                margin-bottom: 5px;
            }
            .report-value {
                font-size: 16px;
                font-weight: 600;
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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
