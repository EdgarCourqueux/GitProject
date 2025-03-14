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
    price = response["bitcoin"]["usd"]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prices.append({"Timestamp": timestamp, "Price": price})
    
    if len(prices) > 50:  # Garde les 50 dernières valeurs
        prices.pop(0)

    print(f"[{timestamp}] Prix récupéré : {price}")

app.layout = html.Div([
    html.H1("📈 Bitcoin Live Dashboard"),
    dcc.Graph(id="price-graph"),
    dcc.Interval(id="interval-component", interval=60000, n_intervals=0)  # Mise à jour toutes les 60 sec
])

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

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8080)
