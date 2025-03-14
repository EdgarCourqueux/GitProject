import dash
from dash import dcc, html
import plotly.express as px
import requests
import datetime
import pandas as pd

app = dash.Dash(__name__)
prices = []  # Stockage en mémoire

def get_bitcoin_price():
    """ Récupère le prix et l'ajoute à la liste en mémoire. """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    response = requests.get(url).json()

    # Vérification de la réponse avant de l'utiliser
    if "bitcoin" not in response or "usd" not in response["bitcoin"]:
        print("❌ Erreur : Impossible de récupérer le prix Bitcoin")
        return  # Sortir sans ajouter de valeur

    price = response["bitcoin"]["usd"]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prices.append({"Timestamp": timestamp, "Price": price})
    
    if len(prices) > 50:  # Garde les 50 dernières valeurs
        prices.pop(0)

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
    get_bitcoin_price()  # Récupère un nouveau prix
    
    if not prices:
        return px.line(title="Aucune donnée disponible", template="plotly_dark")

    df = pd.DataFrame(prices)
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
