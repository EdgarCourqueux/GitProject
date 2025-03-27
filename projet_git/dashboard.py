import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime
import subprocess

# Initialisation de l'application Dash
app = dash.Dash(__name__)

# Définition des couleurs pour le thème
COLORS = {
    "background": "#f9f9f9",
    "text": "#333333",
    "bitcoin": "#f2a900",
    "positive": "#4caf50",
    "negative": "#f44336",
    "card": "#ffffff"
}

REPORT_FILE = "/home/edgar/projet_git/daily_report.csv"

def load_report():
    """Charge les données du rapport quotidien."""
    try:
        df = pd.read_csv(REPORT_FILE, names=["Date", "Open", "Close", "Max", "Min", "Evolution"], header=None)
        df["Date"] = pd.to_datetime(df["Date"])
        print("🔄 Rapport chargé :", df.tail(5))  # Debugging
        return df.to_dict("records")
    except Exception as e:
        print(f"❌ Erreur lors du chargement du rapport : {e}")
        return []

def get_daily_report():
    """Exécute le script daily_report.sh et charge les données du rapport."""
    try:
        # Exécution du script bash
        subprocess.run(["bash", "/home/edgar/projet_git/daily_report.sh"], check=True)
        return load_report()
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du script daily_report.sh : {e}")
        return []

# Charger les données du rapport quotidien
daily_report = get_daily_report()

# ---------------------- DASHBOARD LAYOUT ----------------------
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Bitcoin Live Dashboard", className="header-title"),
        html.Div([html.Img(src="https://cryptologos.cc/logos/bitcoin-btc-logo.svg", className="bitcoin-logo"),
                  html.Div(id="current-price", className="current-price")], className="header-price")
    ], className="header"),

    # Main content
    html.Div([
        # Graphique principal
        html.Div([html.Div([html.H2("Évolution du Prix", className="card-title"),
                           dcc.Graph(id="price-graph", config={'displayModeBar': False}, className="main-graph")],
                          className="card")], className="graph-container"),

        # Rapport quotidien
        html.Div([html.Div([html.H2("Rapport Quotidien", className="card-title"),
                           html.Div(id="daily-report", className="report-content")],
                          className="card")], className="report-container")
    ], className="main-content"),

    # Intervalles de mise à jour
    dcc.Interval(id="interval-report", interval=86400000, n_intervals=0)  # 24 heures

], id="dashboard-container")

# ---------------------- CALLBACKS ----------------------

@app.callback(
    Output("price-graph", "figure"),
    Output("current-price", "children"),
    Input("interval-report", "n_intervals")
)
def update_data_and_graph(n):
    """Met à jour les données et le graphique en fonction du rapport quotidien."""
    # Charger le rapport quotidien
    global daily_report
    daily_report = get_daily_report()

    # Créer un DataFrame pour le graphique
    df = pd.DataFrame(daily_report)

    # Créer une figure personnalisée
    fig = go.Figure()

    # Ajouter une ligne pour l'évolution du prix
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Close"],
        mode='lines',
        name='Prix BTC',
        line=dict(color=COLORS["bitcoin"], width=3),
        fill='tozeroy',
        fillcolor=f'rgba(242, 169, 0, 0.1)'
    ))

    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor=COLORS["background"],
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Roboto, sans-serif", color=COLORS["text"]),
        xaxis=dict(title="", showgrid=True),
        yaxis=dict(title="Prix (USD)", showgrid=True, tickprefix="$"),
        hovermode="x unified"
    )

    # Retourner le graphique et le prix actuel
    current_price = f"${df['Close'].iloc[-1]:,.2f}"
    return fig, current_price

@app.callback(
    Output("daily-report", "children"),
    Input("interval-report", "n_intervals")
)
def update_report(n):
    """Met à jour le rapport quotidien."""
    return get_daily_report()

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8080)
