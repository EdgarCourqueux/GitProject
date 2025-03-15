import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import requests
import datetime
import pandas as pd
import os
import pytz
import subprocess

# Initialisation de l'application Dash avec un thème personnalisé
app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# Configuration des constantes
DATA_FILE = "projet.csv"
TZ_PARIS = pytz.timezone("Europe/Paris")
MAX_DATA_POINTS = 50

# Définition des couleurs pour le thème
COLORS = {
    "background": "#f9f9f9",
    "text": "#333333",
    "bitcoin": "#f2a900",
    "positive": "#4caf50",
    "negative": "#f44336",
    "card": "#ffffff"
}

def load_data():
    """ Charge les données du fichier CSV en gérant les erreurs et force la mise à jour. """
    try:
        df = pd.read_csv(DATA_FILE, names=["Timestamp", "Price"], header=None)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df = df.dropna()
        print("🔄 Données chargées :", df.tail(5))  # Debugging
        return df.to_dict("records")
    except Exception as e:
        print(f"❌ Erreur lors du chargement des données : {e}")
        return []

def save_data(prices_data):
    """Sauvegarde les données dans le fichier CSV."""
    df = pd.DataFrame(prices_data)
    df.to_csv(DATA_FILE, index=False, header=False)

def get_bitcoin_price():
    """Récupère le prix du Bitcoin via l'API CoinGecko."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url).json()
        
        if "bitcoin" not in response or "usd" not in response["bitcoin"]:
            print("⚠️ Erreur : Impossible de récupérer les données de l'API")
            return None

        price = response["bitcoin"]["usd"]
        timestamp = datetime.datetime.now(pytz.utc).astimezone(TZ_PARIS)
        
        return {"Timestamp": timestamp, "Price": price}
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du prix : {e}")
        return None

def update_prices_data(prices_data):
    """Met à jour les données de prix et maintient la taille de la liste."""
    new_price_data = get_bitcoin_price()
    if new_price_data:
        prices_data.append(new_price_data)
        
        # Garder seulement les MAX_DATA_POINTS dernières valeurs
        if len(prices_data) > MAX_DATA_POINTS:
            prices_data = prices_data[-MAX_DATA_POINTS:]
            
        save_data(prices_data)
        print(f"[{new_price_data['Timestamp']}] Prix récupéré : {new_price_data['Price']}")
    
    return prices_data

def get_daily_report(prices_data):
    """Génère un rapport quotidien basé sur les prix stockés."""
    if not prices_data:
        return html.Div("Aucune donnée disponible pour aujourd'hui.")

    df = pd.DataFrame(prices_data)
    today = datetime.datetime.now(TZ_PARIS).date()
    df_today = df[pd.to_datetime(df["Timestamp"]).dt.date == today]

    if df_today.empty:
        return html.Div("Aucune donnée disponible pour aujourd'hui.")

    open_price = df_today.iloc[0]["Price"]
    close_price = df_today.iloc[-1]["Price"]
    max_price = df_today["Price"].max()
    min_price = df_today["Price"].min()
    evolution = round(((close_price - open_price) / open_price) * 100, 2)
    
    evolution_color = COLORS["positive"] if evolution >= 0 else COLORS["negative"]
    evolution_symbol = "▲" if evolution >= 0 else "▼"

    return html.Div([
        html.Div([
            html.Div("Date", className="stat-label"),
            html.Div(today.strftime("%d/%m/%Y"), className="stat-value")
        ], className="stat-item"),
        html.Div([
            html.Div("Ouverture", className="stat-label"),
            html.Div(f"${open_price:,.2f}", className="stat-value")
        ], className="stat-item"),
        html.Div([
            html.Div("Dernière valeur", className="stat-label"),
            html.Div(f"${close_price:,.2f}", className="stat-value")
        ], className="stat-item"),
        html.Div([
            html.Div("Maximum", className="stat-label"),
            html.Div(f"${max_price:,.2f}", className="stat-value")
        ], className="stat-item"),
        html.Div([
            html.Div("Minimum", className="stat-label"),
            html.Div(f"${min_price:,.2f}", className="stat-value")
        ], className="stat-item"),
        html.Div([
            html.Div("Évolution", className="stat-label"),
            html.Div(f"{evolution_symbol} {evolution}%", 
                    className="stat-value", 
                    style={"color": evolution_color, "font-weight": "bold"})
        ], className="stat-item"),
    ], className="stats-container")

# Charger les données sauvegardées au démarrage
prices = load_data()

# ---------------------- DASHBOARD LAYOUT ----------------------
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Bitcoin Live Dashboard", className="header-title"),
        html.Div([
            html.Img(src="https://cryptologos.cc/logos/bitcoin-btc-logo.svg", className="bitcoin-logo"),
            html.Div(id="current-price", className="current-price")
        ], className="header-price")
    ], className="header"),
    
    # Main content
    html.Div([
        # Graphique principal
        html.Div([
            html.Div([
                html.H2("Évolution du Prix", className="card-title"),
                dcc.Graph(
                    id="price-graph",
                    config={'displayModeBar': False},
                    className="main-graph"
                ),
            ], className="card")
        ], className="graph-container"),
        
        # Rapport quotidien
        html.Div([
            html.Div([
                html.H2("Rapport Quotidien", className="card-title"),
                html.Div(id="daily-report", className="report-content")
            ], className="card")
        ], className="report-container")
    ], className="main-content"),
    
    # Intervalles de mise à jour
    dcc.Interval(id="interval-component", interval=60000, n_intervals=0),  # 1 minute
    dcc.Interval(id="interval-report", interval=60000, n_intervals=0),    # 1 minute
    
    # CSS personnalisé
    html.Link(
        rel="stylesheet",
        href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap"
    ),
    
], id="dashboard-container")

# ---------------------- CALLBACKS ----------------------

@app.callback(
    Output("price-graph", "figure"),
    Output("current-price", "children"),
    Input("interval-component", "n_intervals")
)
def update_data_and_graph(n):
    """Met à jour les données et le graphique."""
    global prices
    
    # Exécuter scraper.sh pour récupérer de nouvelles données
    try:
        subprocess.run(["bash", "scraper.sh"], check=True)
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du script : {e}")
    
    # Charger les nouvelles données depuis le fichier CSV
    prices = load_data()
    
    # Créer un DataFrame pour le graphique
    df = pd.DataFrame(prices)
    
    # Vérifier si des données sont disponibles
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Aucune donnée disponible",
            template="plotly_white",
            plot_bgcolor=COLORS["background"],
            paper_bgcolor=COLORS["background"],
            font=dict(color=COLORS["text"])
        )
        return empty_fig, "N/A"

    # Calculer les variations de prix pour adapter l'échelle du graphique
    min_price = df["Price"].min()
    max_price = df["Price"].max()
    
    # Ajouter une marge de 1% pour mieux visualiser les variations
    price_range = max_price - min_price
    if price_range < 0.01 * min_price:  # Si la plage est très petite
        # Créer une plage artificielle avec une marge de 0.5%
        y_min = min_price * 0.995
        y_max = max_price * 1.005
    else:
        # Ajouter une marge de 5% pour mieux voir les variations
        y_min = min_price - (price_range * 0.05)
        y_max = max_price + (price_range * 0.05)

    # Créer une figure personnalisée
    fig = go.Figure()
    
    # Ajouter la ligne principale
    fig.add_trace(go.Scatter(
        x=df["Timestamp"],
        y=df["Price"],
        mode='lines',
        name='Prix BTC',
        line=dict(color=COLORS["bitcoin"], width=3),
        fill='tozeroy',
        fillcolor=f'rgba({242}, {169}, {0}, 0.1)'  # Version transparente de la couleur Bitcoin
    ))
    
    # Mise en forme du graphique avec adaptation de l'échelle
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor=COLORS["background"],
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Roboto, sans-serif", color=COLORS["text"]),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor='rgba(200,200,200,0.2)'
        ),
        yaxis=dict(
            title="Prix (USD)",
            showgrid=True,
            gridcolor='rgba(200,200,200,0.2)',
            tickprefix="$",
            range=[y_min, y_max]  # Ajuster l'échelle Y pour mieux voir les variations
        ),
        hovermode="x unified"
    )
    
    # Ajouter des annotations pour les points importants
    if len(df) > 1:
        # Marquer le prix le plus bas
        min_price_idx = df["Price"].idxmin()
        fig.add_trace(go.Scatter(
            x=[df.iloc[min_price_idx]["Timestamp"]],
            y=[df.iloc[min_price_idx]["Price"]],
            mode='markers',
            marker=dict(color=COLORS["negative"], size=8),
            hoverinfo='text',
            hovertext=f'Min: ${df.iloc[min_price_idx]["Price"]:,.2f}',
            showlegend=False
        ))
        
        # Marquer le prix le plus haut
        max_price_idx = df["Price"].idxmax()
        fig.add_trace(go.Scatter(
            x=[df.iloc[max_price_idx]["Timestamp"]],
            y=[df.iloc[max_price_idx]["Price"]],
            mode='markers',
            marker=dict(color=COLORS["positive"], size=8),
            hoverinfo='text',
            hovertext=f'Max: ${df.iloc[max_price_idx]["Price"]:,.2f}',
            showlegend=False
        ))
        
        # Marquer le prix actuel
        current_idx = len(df) - 1
        fig.add_trace(go.Scatter(
            x=[df.iloc[current_idx]["Timestamp"]],
            y=[df.iloc[current_idx]["Price"]],
            mode='markers',
            marker=dict(color=COLORS["bitcoin"], size=10, symbol="star"),
            hoverinfo='text',
            hovertext=f'Actuel: ${df.iloc[current_idx]["Price"]:,.2f}',
            showlegend=False
        ))
    
    # Récupérer le prix actuel (dernier prix)
    current_price = f"${df['Price'].iloc[-1]:,.2f}"
    
    return fig, current_price

@app.callback(
    Output("daily-report", "children"),
    Input("interval-report", "n_intervals")
)
def update_report(n):
    """Met à jour le rapport quotidien."""
    return get_daily_report(prices)

# -------------------- STYLES CSS --------------------
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
                font-family: 'Roboto', sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f9f9f9;
                color: #333333;
            }
            #dashboard-container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #f2a900;
            }
            .header-title {
                font-size: 28px;
                font-weight: 700;
                margin: 0;
                color: #333333;
            }
            .header-price {
                display: flex;
                align-items: center;
            }
            .bitcoin-logo {
                height: 32px;
                margin-right: 10px;
            }
            .current-price {
                font-size: 24px;
                font-weight: 700;
                color: #f2a900;
            }
            .main-content {
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
            }
            .graph-container {
                flex: 2;
                min-width: 300px;
            }
            .report-container {
                flex: 1;
                min-width: 300px;
            }
            .card {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                padding: 20px;
                height: 100%;
            }
            .card-title {
                margin-top: 0;
                margin-bottom: 20px;
                font-size: 20px;
                font-weight: 500;
                color: #333333;
                padding-bottom: 10px;
                border-bottom: 1px solid #eee;
            }
            .main-graph {
                height: 400px;
            }
            .stats-container {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
                gap: 15px;
            }
            .stat-item {
                background-color: #f9f9f9;
                border-radius: 6px;
                padding: 12px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .stat-label {
                font-size: 14px;
                color: #666666;
                margin-bottom: 5px;
            }
            .stat-value {
                font-size: 18px;
                font-weight: 500;
            }
            /* Responsive design */
            @media (max-width: 768px) {
                .header {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 15px;
                }
                .header-price {
                    width: 100%;
                    justify-content: flex-start;
                }
                .main-graph {
                    height: 300px;
                }
                .stats-container {
                    grid-template-columns: repeat(2, 1fr);
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

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8080)
