import dash
from dash import dcc, html
import plotly.express as px
import requests
import datetime
import pandas as pd
import os
import pytz
import subprocess  # ✅ Ajouté en haut avec les autres imports


app = dash.Dash(__name__)

DATA_FILE = "projet.csv"
prices = []  # Stockage temporaire
# Définir le fuseau horaire correct (Paris)
TZ_PARIS = pytz.timezone("Europe/Paris")

def load_data():
    """ Charge les données du fichier CSV au démarrage en gérant les erreurs. """
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        try:
            df = pd.read_csv(DATA_FILE, names=["Timestamp", "Price"], header=None)
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce").astype(str)  # Convertir en string
            df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
            df = df.dropna()  # Supprime les lignes mal formatées
            return df.to_dict("records")  # Liste de dictionnaires
        except Exception as e:
            print(f"❌ Erreur lors du chargement des données : {e}")
            return []
    return []



def save_data():
    """ Sauvegarde les données dans le fichier CSV. """
    df = pd.DataFrame(prices)
    df.to_csv(DATA_FILE, index=False)

def get_bitcoin_price():
    """ Récupère le prix et l'ajoute à la liste en mémoire avec la bonne heure. """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    response = requests.get(url).json()
    
    if "bitcoin" not in response or "usd" not in response["bitcoin"]:
        print("⚠️ Erreur : Impossible de récupérer les données de l'API")
        return

    price = response["bitcoin"]["usd"]
    
    # Convertir en heure locale
    timestamp = datetime.datetime.now(pytz.utc).astimezone(TZ_PARIS).strftime("%Y-%m-%d %H:%M:%S")
    
    prices.append({"Timestamp": timestamp, "Price": price})

    if len(prices) > 50:  # Garde les 50 dernières valeurs
        prices.pop(0)

    save_data()  # Sauvegarde après chaque mise à jour
    print(f"[{timestamp}] Prix récupéré : {price}")


def get_daily_report():
    """ Génère un rapport quotidien basé sur les prix stockés. """
    if not prices:
        return "Aucune donnée pour aujourd'hui."

    df = pd.DataFrame(prices)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df_today = df[df["Timestamp"].dt.date == datetime.date.today()]

    if df_today.empty:
        return "Aucune donnée disponible pour aujourd'hui."

    open_price = df_today.iloc[0]["Price"]
    close_price = df_today.iloc[-1]["Price"]
    max_price = df_today["Price"].max()
    min_price = df_today["Price"].min()
    evolution = round(((close_price - open_price) / open_price) * 100, 2)

    return f"""
    📅 **Date** : {datetime.date.today()}
    🔹 **Ouverture** : {open_price} USD
    🔹 **Clôture** : {close_price} USD
    🔺 **Max** : {max_price} USD
    🔻 **Min** : {min_price} USD
    📊 **Évolution** : {evolution}%
    """

# Charger les données sauvegardées au démarrage
prices = load_data()

# ---------------------- DASHBOARD ----------------------
app.layout = html.Div([
    html.H1("📈 Bitcoin Live Dashboard", style={"textAlign": "center"}),

    # Graphique
    dcc.Graph(id="price-graph"),

    # Intervalle de mise à jour
    dcc.Interval(id="interval-component", interval=60000, n_intervals=0),

    # Rapport quotidien
    html.Div([
        html.H2("📊 Rapport Quotidien"),
        html.P(id="daily-report", style={"fontSize": "18px", "textAlign": "center"})
    ]),

    # Intervalle pour mise à jour du rapport
    dcc.Interval(id="interval-report", interval=60000, n_intervals=0)
])

# Mise à jour du graphique des prix
@app.callback(
    dash.Output("price-graph", "figure"),
    [dash.Input("interval-component", "n_intervals")]
)


def update_graph(n):
    """ Met à jour le graphique en exécutant `scraper.sh` pour récupérer les nouvelles données. """
    
    # Exécuter `scraper.sh` pour récupérer de nouvelles données
    subprocess.run(["bash", "scraper.sh"], check=True)

    # Charger les nouvelles données depuis le fichier CSV
    df = pd.read_csv(DATA_FILE, names=["Timestamp", "Price"], header=None)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce").astype(str)  # Convertir en string
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df = df.dropna()  # Supprime les lignes mal formatées

    if df.empty:
        return px.line(title="Aucune donnée disponible", template="plotly_dark")

    fig = px.line(df, x="Timestamp", y="Price", title="📊 Évolution du prix du Bitcoin", template="plotly_white")
    return fig

# Mise à jour du rapport quotidien
@app.callback(
    dash.Output("daily-report", "children"),
    [dash.Input("interval-report", "n_intervals")]
)
def update_report(n):
    return get_daily_report()

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8080)
