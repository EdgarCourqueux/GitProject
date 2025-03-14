import dash
from dash import dcc, html
import pandas as pd
import plotly.express as px
import os

# Charger les données scrappées
DATA_FILE = "projet.csv"
REPORT_FILE = "daily_report.csv"

def load_data():
    """ Charge les données du fichier CSV en gérant les erreurs. """
    if not os.path.exists(DATA_FILE):
        print("⚠️ Fichier projet.csv introuvable !")
        return pd.DataFrame(columns=["Timestamp", "Price"])
    
    try:
        df = pd.read_csv(DATA_FILE, names=["Timestamp", "Price"], dtype={"Timestamp": str, "Price": str})
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df = df.dropna()  # Supprimer les lignes invalides
        return df.tail(50)  # Garde seulement les 50 dernières valeurs
    except Exception as e:
        print(f"❌ Erreur lors du chargement des données : {e}")
        return pd.DataFrame(columns=["Timestamp", "Price"])

def load_daily_report():
    """ Charge les statistiques du jour si disponibles """
    if not os.path.exists(REPORT_FILE):
        return "📌 Aucun rapport disponible pour aujourd'hui."

    try:
        df = pd.read_csv(REPORT_FILE, names=["Date", "Open", "Close", "Max", "Min", "Evolution"])
        last_report = df.iloc[-1]

        return html.Div([
            html.P(f"📅 **Date** : {last_report['Date']}", style={"margin": "5px"}),
            html.P(f"🔹 **Ouverture** : {last_report['Open']} USD", style={"margin": "5px"}),
            html.P(f"🔹 **Clôture** : {last_report['Close']} USD", style={"margin": "5px"}),
            html.P(f"🔺 **Max** : {last_report['Max']} USD", style={"margin": "5px"}),
            html.P(f"🔻 **Min** : {last_report['Min']} USD", style={"margin": "5px"}),
            html.P(f"📊 **Évolution** : {last_report['Evolution']}", style={"margin": "5px", "color": "green" if float(last_report['Evolution'].replace('%', '')) > 0 else "red"})
        ])
    except Exception as e:
        print(f"❌ Erreur lors du chargement du rapport : {e}")
        return "⚠️ Impossible de charger le rapport."

# Initialiser l'application Dash
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("📈 Bitcoin Live Dashboard", style={"textAlign": "center", "color": "#2c3e50"}),

    html.Div("Mise à jour automatique toutes les 60 secondes.",
             style={"textAlign": "center", "fontSize": "16px", "color": "#7f8c8d"}),

    dcc.Graph(id="price-graph", style={"height": "500px"}),

    # Mise à jour des données en temps réel
    dcc.Interval(id="interval-component", interval=60000, n_intervals=0),

    # Section Rapport Quotidien
    html.Div([
        html.H2("📊 Rapport Quotidien", style={"margin-top": "20px", "textAlign": "center", "color": "#2c3e50"}),
        html.Div(id="daily-report", style={"textAlign": "center", "fontSize": "16px"}),
        dcc.Interval(id="interval-report", interval=60000, n_intervals=0)  # Mise à jour chaque minute
    ], style={"backgroundColor": "#f8f9fa", "padding": "20px", "borderRadius": "10px", "marginTop": "20px"})
], style={
    "fontFamily": "Arial, sans-serif",
    "backgroundColor": "#ecf0f1",
    "padding": "20px"
})

@app.callback(
    dash.Output("price-graph", "figure"),
    [dash.Input("interval-component", "n_intervals")]
)
def update_graph(n):
    df = load_data()
    if df.empty:
        return px.line(title="Aucune donnée disponible", template="plotly_dark")

    fig = px.line(
        df, x="Timestamp", y="Price", 
        title="📊 Évolution du prix du Bitcoin",
        template="plotly_white",
        markers=True  # Ajoute des points pour mieux voir les valeurs
    )

    # Améliorer l'affichage des axes
    fig.update_layout(
        xaxis_title="Heure",
        yaxis_title="Prix (USD)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, zeroline=False),
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor="white"
    )

    return fig

@app.callback(
    dash.Output("daily-report", "children"),
    [dash.Input("interval-report", "n_intervals")]
)
def update_report(n):
    return load_daily_report()

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8050)

