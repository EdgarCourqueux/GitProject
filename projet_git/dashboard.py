import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import subprocess
import datetime
import os
import numpy as np

# Constants and Configuration
DATA_FILE = "/app/bitcoin_prices.csv"
REPORT_FILE = "/app/daily_reports.csv"
MAX_DATA_POINTS = 100

# Color Palette
COLORS = {
    "background": "#1C1C1E",
    "primary": "#F7931A",  # Bitcoin Orange
    "text_primary": "#FFFFFF",
    "text_secondary": "#B0B0B0",
    "grid": "#2C2C2E",
    "positive": "#4CAF50",
    "negative": "#F44336"
}

# Application Initialization
app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "theme-color", "content": COLORS["background"]}
    ],
    external_stylesheets=[
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap'
    ]
)
server = app.server

def ensure_files_exist():
    """Ensure required files exist with proper permissions."""
    for file_path in [DATA_FILE, REPORT_FILE]:
        try:
            if not os.path.exists(file_path):
                open(file_path, 'a').close()
                print(f"Created file: {file_path}")
            
            os.chmod(file_path, 0o666)
        except Exception as e:
            print(f"Error ensuring file {file_path} exists: {e}")

def load_data():
    """Load and filter Bitcoin price data."""
    try:
        today = datetime.date.today().strftime("%Y-%m-%d")
        df = pd.read_csv(DATA_FILE, names=["Timestamp", "Price"], header=None)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        
        today_data = df[df["Timestamp"].dt.date == datetime.date.today()]
        
        if today_data.empty:
            return pd.DataFrame(columns=["Timestamp", "Price"])
        
        # Advanced outlier removal
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

def load_daily_report():
    """Load and generate daily Bitcoin report."""
    try:
        cols = ["Date", "Open", "Close", "Max", "Min", "Evolution"]
        df = pd.read_csv(REPORT_FILE, names=cols, header=None)
        df["Date"] = pd.to_datetime(df["Date"])
        
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

def create_price_graph(df):
    """Create an advanced price graph with professional styling."""
    if df.empty:
        return go.Figure()

    # Dynamic Y-axis range
    lower_percentile = np.percentile(df["Price"], 5)
    upper_percentile = np.percentile(df["Price"], 95)

    fig = go.Figure()
    
    # Advanced trace with gradient fill and smooth interpolation
    fig.add_trace(go.Scatter(
        x=df["Timestamp"],
        y=df["Price"],
        mode='lines+markers',
        name='Bitcoin Price',
        line=dict(color=COLORS["primary"], width=3, shape='spline'),
        marker=dict(size=6, color=COLORS["primary"], opacity=0.7),
        fill='tozeroy',
        fillcolor=f'rgba({242}, {147}, {26}, 0.2)'
    ))
    
    fig.update_layout(
        title={
            'text': f"Bitcoin Price Trend ({datetime.date.today()})",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(color=COLORS["text_primary"], size=16)
        },
        plot_bgcolor=COLORS["background"],
        paper_bgcolor=COLORS["background"],
        font=dict(family="Inter, sans-serif", color=COLORS["text_primary"]),
        xaxis=dict(
            title="Time",
            showgrid=True,
            gridcolor=COLORS["grid"],
            tickangle=-45,
            color=COLORS["text_secondary"]
        ),
        yaxis=dict(
            title="Price (USD)",
            showgrid=True,
            gridcolor=COLORS["grid"],
            tickprefix="$",
            range=[lower_percentile * 0.99, upper_percentile * 1.01],
            color=COLORS["text_secondary"]
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=COLORS["background"],
            font_color=COLORS["text_primary"]
        )
    )
    
    return fig

def create_dashboard_layout():
    """Create a modern, professional dashboard layout."""
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
    ], className="dashboard-container", style={
        'backgroundColor': COLORS["background"],
        'color': COLORS["text_primary"],
        'padding': '20px',
        'fontFamily': 'Inter, sans-serif'
    })

app.layout = html.Div([
    create_dashboard_layout(),
    dcc.Interval(id="graph-update", interval=60000),  # Update every minute
    dcc.Interval(id="report-update", interval=3600000)  # Update hourly
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
def update_daily_report(n):
    """Update daily report section."""
    try:
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
