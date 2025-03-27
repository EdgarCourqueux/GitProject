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
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "theme-color", "content": "#3498db"}
    ],
    external_stylesheets=[
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap'
    ]
)
server = app.server

app.layout = html.Div([
    dcc.Meta(
        name='viewport', 
        content='width=device-width, initial-scale=1'
    ),
    html.Style('''
        :root {
            --bg-primary: #f4f6f9;
            --text-primary: #2c3e50;
            --accent-color: #3498db;
            --bitcoin-color: #f2a900;
            --positive-color: #2ecc71;
            --negative-color: #e74c3c;
            --card-bg: #ffffff;
            --shadow-subtle: 0 4px 6px rgba(0, 0, 0, 0.05);
            --shadow-hover: 0 10px 20px rgba(0, 0, 0, 0.1);
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }

        .dashboard-container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: var(--card-bg);
            border-radius: 12px;
            box-shadow: var(--shadow-subtle);
            padding: 20px;
            transition: all 0.3s ease;
        }

        .dashboard-container:hover {
            box-shadow: var(--shadow-hover);
        }

        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 2px solid var(--accent-color);
            padding-bottom: 10px;
        }

        .dashboard-title {
            font-size: 2rem;
            font-weight: 600;
            color: var(--accent-color);
            margin: 0;
        }

        .current-price {
            font-size: 1.8rem;
            font-weight: bold;
            color: var(--bitcoin-color);
        }

        .content-wrapper {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }

        .graph-container {
            background-color: var(--bg-primary);
            border-radius: 8px;
            padding: 15px;
        }

        .report-container {
            background-color: var(--bg-primary);
            border-radius: 8px;
            padding: 15px;
        }

        .report-title {
            color: var(--accent-color);
            border-bottom: 1px solid var(--accent-color);
            padding-bottom: 10px;
            margin-bottom: 15px;
        }

        .report-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .report-item {
            display: flex;
            flex-direction: column;
            background-color: var(--card-bg);
            border-radius: 6px;
            padding: 10px;
            box-shadow: var(--shadow-subtle);
        }

        .report-label {
            font-size: 0.8rem;
            color: var(--text-primary);
            opacity: 0.7;
            margin-bottom: 5px;
        }

        .report-value {
            font-size: 1rem;
            font-weight: 600;
        }

        @media (max-width: 768px) {
            .content-wrapper {
                grid-template-columns: 1fr;
            }
        }
    '''),  # Your existing CSS
    create_dashboard_layout(),
    dcc.Interval(id="graph-update", interval=60000),
    dcc.Interval(id="report-update", interval=3600000)
], className="dashboard-container")

# Continue with the rest of your app's setup...



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

def load_daily_report():
    """Enhanced daily report loading with more robust error handling."""
    try:
        cols = ["Date", "Open", "Close", "Max", "Min", "Evolution"]
        df = pd.read_csv(REPORT_FILE, names=cols, header=None)
        df["Date"] = pd.to_datetime(df["Date"])
        
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
    """Create a more adaptive and informative price graph."""
    if df.empty:
        return go.Figure()

    # Calculate percentile-based y-axis limits for better scaling
    lower_percentile = np.percentile(df["Price"], 5)
    upper_percentile = np.percentile(df["Price"], 95)

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
        title=f"Bitcoin Price Trend ({datetime.date.today()})",
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
            tickprefix="$",
            range=[lower_percentile * 0.99, upper_percentile * 1.01]  # Dynamic range
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode="x unified"
    )
    
    return fig

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

# Ensure files exist before running
ensure_files_exist()
# Ajoutez ces styles à votre fichier CSS ou dans un style inline

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
