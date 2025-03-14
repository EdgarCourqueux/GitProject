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
    """Charge les données du fichier CSV en gérant les erreurs."""
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        try:
            df = pd.read_csv(DATA_FILE, names=["Timestamp", "Price"], header=None)
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
            df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
            df = df.dropna()  # Supprime les lignes mal formatées
            return df
        except Exception as e:
            print(f"❌ Erreur lors du chargement des données : {e}")
            return pd.DataFrame(columns=["Timestamp", "Price"])
    return pd.DataFrame(columns=["Timestamp", "Price"])

def save_data(df):
    """Sauvegarde les données DataFrame dans le fichier CSV."""
    try:
        df.to_csv(DATA_FILE, index=False, header=False)
        print(f"✅ Données sauvegardées dans {DATA_FILE}")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde des données : {e}")

def get_bitcoin_price():
    """Récupère le prix du Bitcoin via l'API CoinGecko."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url).json()
        
        if "bitcoin" not in response or "usd" not in response["bitcoin"]:
            print("⚠️ Erreur : Impossible de récupérer les données de l'API")
            return None, None

        price = response["bitcoin"]["usd"]
        timestamp = datetime.datetime.now(pytz.utc).astimezone(TZ_PARIS)
        
        return timestamp, price
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du prix : {e}")
        return None, None

def get_daily_report(df):
    """Génère un rapport quotidien basé sur les dataframe."""
    if df.empty:
        return html.Div("Aucune donnée disponible pour aujourd'hui.")

    # Assurez-vous que Timestamp est un datetime
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    
    today = datetime.datetime.now(TZ_PARIS).date()
    df_today = df[df["Timestamp"].dt.date == today]

    if df_today.empty:
        return html.Div("Aucune donnée disponible pour aujourd'hui.")

    # Utilisation du dernier prix connu issu du script scraper.sh
    open_price = df_today.iloc[0]["Price"]
    close_price = df_today.iloc[-1]["Price"]  # Dernière valeur du DataFrame
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

# Variable globale pour stocker le DataFrame des prix
df_prices = load_data()

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
    
    # CSS personnalisé
    html.Link(
        rel="stylesheet",
        href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap"
    ),
    
    # Store pour garder la dernière valeur correcte
    dcc.Store(id='last-valid-data')
], id="dashboard-container")

# ---------------------- CALLBACKS ----------------------

@app.callback(
    Output("price-graph", "figure"),
    Output("current-price", "children"),
    Output("daily-report", "children"),
    Input("interval-component", "n_intervals")
)
def update_dashboard(n):
    """Met à jour les données et le dashboard complet."""
    global df_prices
    
    # Exécuter scraper.sh pour récupérer de nouvelles données
    try:
        subprocess.run(["bash", "scraper.sh"], check=True)
        print("✅ Script scraper.sh exécuté avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du script : {e}")
    
    # Charger les nouvelles données depuis le fichier CSV
    df_prices = load_data()
    
    # Vérifier si des données sont disponibles
    if df_prices.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Aucune donnée disponible",
            template="plotly_white",
            plot_bgcolor=COLORS["background"],
            paper_bgcolor=COLORS["background"],
            font=dict(color=COLORS["text"])
        )
        return empty_fig, "N/A", html.Div("Aucune donnée disponible")

    # Récupérer le prix actuel directement de l'API pour s'assurer d'avoir la dernière valeur
    timestamp, latest_price = get_bitcoin_price()
    
    if latest_price is not None and timestamp is not None:
        # Si on a réussi à récupérer un nouveau prix de l'API, on l'ajoute au DataFrame
        # mais on ne l'ajoute pas au CSV pour éviter les doublons avec le script scraper.sh
        # On l'utilise uniquement pour l'affichage
        current_price = f"${latest_price:,.2f}"
    else:
        # Si on n'a pas pu récupérer de prix de l'API, on utilise le dernier prix du DataFrame
        latest_price = df_prices["Price"].iloc[-1]
        current_price = f"${latest_price:,.2f}"

    # Calculer les variations de prix pour adapter l'échelle du graphique
    min_price = df_prices["Price"].min()
    max_price = df_prices["Price"].max()
    
    # Ajouter une marge pour mieux visualiser les variations
    price_range = max_price - min_price
    if price_range < 0.01 * min_price:  # Si la plage est très petite
        # Créer une plage artificielle avec une marge de 0.5%
        y_min = min_price * 0.995
        y_max = max_price * 1.005
    else:
        # Ajouter une marge de 2% pour mieux voir les variations
        y_min = min_price - (price_range * 0.05)
        y_max = max_price + (price_range * 0.05)

    # Créer une figure personnalisée
    fig = go.Figure()
    
    # Ajouter la ligne principale
    fig.add_trace(go.Scatter(
        x=df_prices["Timestamp"],
        y=df_prices["Price"],
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
    
    # Ajouter des annotations pour les prix importants
    if len(df_prices) > 1:
        # Marquer le prix le plus bas
        min_price_idx = df_prices["Price"].idxmin()
        fig.add_trace(go.Scatter(
            x=[df_prices.iloc[min_price_idx]["Timestamp"]],
            y=[df_prices.iloc[min_price_idx]["Price"]],
            mode='markers',
            marker=dict(color=COLORS["negative"], size=8),
            hoverinfo='text',
            hovertext=f'Min: ${df_prices.iloc[min_price_idx]["Price"]:,.2f}',
            showlegend=False
        ))
        
        # Marquer le prix le plus haut
        max_price_idx = df_prices["Price"].idxmax()
        fig.add_trace(go.Scatter(
            x=[df_prices.iloc[max_price_idx]["Timestamp"]],
            y=[df_prices.iloc[max_price_idx]["Price"]],
            mode='markers',
            marker=dict(color=COLORS["positive"], size=8),
            hoverinfo='text',
            hovertext=f'Max: ${df_prices.iloc[max_price_idx]["Price"]:,.2f}',
            showlegend=False
        ))
        
        # Marquer le prix actuel avec une étoile
        fig.add_trace(go.Scatter(
            x=[df_prices.iloc[-1]["Timestamp"] if timestamp is None else timestamp],
            y=[df_prices.iloc[-1]["Price"] if latest_price is None else latest_price],
            mode='markers',
            marker=dict(color=COLORS["bitcoin"], size=10, symbol="star"),
            hoverinfo='text',
            hovertext=f'Actuel: ${latest_price if latest_price is not None else df_prices.iloc[-1]["Price"]:,.2f}',
            showlegend=False
        ))
    
    # Si on a récupéré un nouveau prix de l'API, on l'ajoute temporairement au DataFrame
    # pour le rapport quotidien
    temp_df = df_prices.copy()
    if timestamp is not None and latest_price is not None:
        temp_df = pd.concat([
            temp_df, 
            pd.DataFrame({"Timestamp": [timestamp], "Price": [latest_price]})
        ]).reset_index(drop=True)

    # Générer le rapport avec les données les plus récentes
    daily_report = get_daily_report(temp_df)
    
    return fig, current_price, daily_report

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
