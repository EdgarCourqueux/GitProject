from flask import Flask
import dash
from dash import dcc, html
import plotly.express as px
import requests
import datetime

app = Flask(__name__)  # Nécessaire pour Railway
dash_app = dash.Dash(__name__, server=app)

# Données stockées en mémoire
prices = []

def get_bitcoin_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    response = requests.get(url).json()
    price = response["bitcoin"]["usd"]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prices.append({"Timestamp": timestamp, "Price": price})
    if len(prices) > 50:
        prices.pop(0)  # Garder seulement les 50 dernières valeurs
    print(f"[{timestamp}] Prix récupéré : {price}")

# Layout du Dashboard
dash_app.layout = html.Div([
    html.H1("📈 Bitcoin Live Dashboard"),
    dcc.Graph(id="price-graph"),
    dcc.Interval(id="interval-component", interval=60000, n_intervals=0)  # MAJ toutes les minutes
])

@dash_app.callback(
    dash.Output("price-graph", "figure"),
    [dash.Input("interval-component", "n_intervals")]
)
def update_graph(n):
    get_bitcoin_price()  # Récupérer le dernier prix
    if not prices:
        return px.line(title="Aucune donnée disponible", template="plotly_dark")

    df = px.data.pandas.DataFrame(prices)
    fig = px.line(df, x="Timestamp", y="Price", title="📊 Évolution du prix du Bitcoin", template="plotly_white")
    
    fig.update_layout(
        xaxis_title="Heure",
        yaxis_title="Prix ($)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, zeroline=False),
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor="white"
    )

    return fig

if __name__ == "__main__":
    dash_app.run_server(debug=False, host="0.0.0.0", port=8050)
