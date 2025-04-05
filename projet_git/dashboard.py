import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import subprocess
import datetime
import pytz
import os
import scipy.stats as stats
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Application Initialization
app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)
server = app.server

# Configuration Constants
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_PATH, "projet.csv")
REPORT_FILE = os.path.join(BASE_PATH, "daily_report.csv")
TZ_PARIS = pytz.timezone("Europe/Paris")
MAX_DATA_POINTS = 100
PREDICTION_HOURS = 24  # Prédire 24 heures

# Design Theme
COLORS = {
    "background": "#1C1C1E",
    "text": "#FFFFFF",
    "bitcoin": "#F7931A",
    "positive": "#2ecc71",
    "negative": "#e74c3c",
    "prediction": "#9B59B6",  # Couleur pour les prédictions
    "card_bg": "#2C2C2E",
    "grid": "#3A3A3C"
}

def ensure_files_exist():
    """Ensure required files exist."""
    for file_path in [DATA_FILE, REPORT_FILE]:
        if not os.path.exists(file_path):
            open(file_path, 'a').close()
            print(f"Created file: {file_path}")

def load_data():
    """Load data from CSV file with error handling."""
    try:
        df = pd.read_csv(DATA_FILE, names=["Timestamp", "Price"], header=None)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df = df.dropna().sort_values("Timestamp")
        return df
    except Exception as e:
        print(f"❌ Data loading error: {e}")
        return pd.DataFrame(columns=["Timestamp", "Price"])

def load_daily_report():
    """Load the daily report from the CSV file with precise timestamp."""
    try:
        cols = ["Timestamp", "Open", "Close", "Max", "Min", "Evolution"]
        df = pd.read_csv(REPORT_FILE, names=cols, header=None)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        
        # If no data, return a default/empty report
        if df.empty:
            now = datetime.datetime.now()
            return pd.Series({
                "Timestamp": now,
                "Open": 0,
                "Close": 0,
                "Max": 0,
                "Min": 0,
                "Evolution": "0%"
            })
        
        return df.iloc[-1]  # Return the most recent report
    except Exception as e:
        print(f"❌ Report loading error: {e}")
        return None

def create_features(df):
    """Créer des caractéristiques pour le modèle prédictif."""
    df = df.copy()
    
    # Extraire des caractéristiques temporelles
    df['hour'] = df['Timestamp'].dt.hour
    df['dayofweek'] = df['Timestamp'].dt.dayofweek
    df['quarter'] = df['Timestamp'].dt.quarter
    df['month'] = df['Timestamp'].dt.month
    df['year'] = df['Timestamp'].dt.year
    df['dayofyear'] = df['Timestamp'].dt.dayofyear
    df['dayofmonth'] = df['Timestamp'].dt.day
    df['weekofyear'] = df['Timestamp'].dt.isocalendar().week
    
    # Créer des caractéristiques de lag (données historiques)
    for lag in range(1, 25):  # Utiliser jusqu'à 24 heures de données historiques
        df[f'lag_{lag}h'] = df['Price'].shift(lag)
    
    # Calculer les moyennes mobiles
    df['rolling_mean_6h'] = df['Price'].rolling(window=6).mean()
    df['rolling_mean_12h'] = df['Price'].rolling(window=12).mean()
    df['rolling_mean_24h'] = df['Price'].rolling(window=24).mean()
    
    # Calculer la volatilité (écart-type sur une fenêtre)
    df['volatility_24h'] = df['Price'].rolling(window=24).std()
    
    # Calculer les variations de prix relatives
    df['price_change_1h'] = df['Price'].pct_change(periods=1)
    df['price_change_12h'] = df['Price'].pct_change(periods=12)
    df['price_change_24h'] = df['Price'].pct_change(periods=24)
    
    # Supprimer les lignes avec des valeurs NaN (dues aux lag et rolling windows)
    df = df.dropna()
    
    return df

def prepare_prediction_data(df):
    """Préparer les données pour l'entraînement et les prédictions."""
    if len(df) < 50:  # Nécessite un minimum de données
        return None, None, None, None, None
    
    # Créer des features
    df_features = create_features(df)
    
    # Variable cible: le prix 24h dans le futur
    df_features['target'] = df_features['Price'].shift(-24)
    
    # Séparation des données récentes (pour la prédiction) et des données d'entraînement
    df_recent = df_features.iloc[-1:].copy()  # Dernière ligne pour les prédictions futures
    df_train = df_features.iloc[:-1].dropna().copy()  # Reste des données pour l'entraînement
    
    if df_train.empty:
        return None, None, None, None, None
    
    # Séparer les features et la cible
    features = ['hour', 'dayofweek', 'quarter', 'month', 'dayofyear', 'dayofmonth', 
                'lag_1h', 'lag_12h', 'lag_24h', 
                'rolling_mean_6h', 'rolling_mean_12h', 'rolling_mean_24h',
                'volatility_24h', 'price_change_1h', 'price_change_12h', 'price_change_24h']
    
    # S'assurer que toutes les colonnes existent
    features = [f for f in features if f in df_train.columns]
    
    X = df_train[features]
    y = df_train['target']
    
    # Données récentes pour la prédiction
    X_recent = df_recent[features]
    
    return X, y, X_recent, df_recent['Timestamp'].iloc[0], df_features

def train_model_and_predict(df):
    """Entraîner un modèle et faire des prédictions."""
    if df.empty or len(df) < 50:
        return None, None
    
    X, y, X_recent, last_timestamp, df_features = prepare_prediction_data(df)
    
    if X is None or y is None:
        return None, None
    
    # Entraîner un modèle Random Forest
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Pour les prédictions futures
    future_timestamps = []
    future_predictions = []
    
    # La dernière entrée connue
    current_data = X_recent.iloc[0].copy()
    current_timestamp = last_timestamp
    
    # Faire des prédictions pour les prochaines 24 heures
    for i in range(PREDICTION_HOURS):
        # Calculer le prochain timestamp (1 heure plus tard)
        next_timestamp = current_timestamp + pd.Timedelta(hours=1)
        
        # Mettre à jour les caractéristiques temporelles
        current_data['hour'] = next_timestamp.hour
        current_data['dayofweek'] = next_timestamp.dayofweek
        current_data['quarter'] = next_timestamp.quarter
        current_data['month'] = next_timestamp.month
        current_data['dayofyear'] = next_timestamp.dayofyear
        current_data['dayofmonth'] = next_timestamp.day
        
        # Faire une prédiction
        prediction = model.predict(current_data.values.reshape(1, -1))[0]
        
        # Stocker la prédiction
        future_timestamps.append(next_timestamp)
        future_predictions.append(prediction)
        
        # Mettre à jour pour la prochaine itération
        # Dans un scénario réel, on mettrait à jour les lags, rolling means, etc.
        # Mais pour simplifier, nous gardons les mêmes valeurs
        current_timestamp = next_timestamp
    
    # Créer un DataFrame avec les prévisions
    predictions_df = pd.DataFrame({
        'Timestamp': future_timestamps,
        'Predicted_Price': future_predictions
    })
    
    # Calculer les métriques d'évaluation sur les données connues
    # (utilisez une validation croisée dans un scénario réel)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    eval_metrics = {
        'MAE': mae,
        'RMSE': rmse,
        'Feature_Importance': dict(zip(X.columns, model.feature_importances_))
    }
    
    return predictions_df, eval_metrics

def calculate_volatility(df, window=14):
    """Calculate volatility as the standard deviation of daily returns."""
    if len(df) < 2:
        return 0
    
    # Calculate returns
    df = df.copy()
    df['return'] = df['Price'].pct_change()
    
    # Calculate rolling volatility (annualized)
    volatility = df['return'].rolling(window=min(window, len(df))).std()
    
    # Annualize (assuming daily data)
    annualized_vol = volatility.iloc[-1] * np.sqrt(365) if not volatility.empty else 0
    return annualized_vol

def calculate_var(df, confidence=0.95, window=14):
    """Calculate Value at Risk using historical method."""
    if len(df) < window:
        return 0
    
    # Calculate returns
    df = df.copy()
    df['return'] = df['Price'].pct_change()
    
    # Filter out NaN values
    returns = df['return'].dropna()
    
    if len(returns) < 2:
        return 0
    
    # Calculate VaR
    var = np.percentile(returns, 100 * (1 - confidence))
    
    # Convert to percentage and make it positive for display
    var_pct = abs(var * 100)
    return var_pct

def create_price_graph(df, predictions_df=None):
    """Create a visually enhanced and interactive price graph with predictions."""
    if df.empty:
        return go.Figure()

    # Limiter pour l'affichage
    df_display = df.tail(MAX_DATA_POINTS).copy()

    # Calculer les percentiles pour l'échelle y
    lower_percentile = np.percentile(df_display["Price"], 5)
    upper_percentile = np.percentile(df_display["Price"], 95)

    # Trouver les points min et max pour les mettre en évidence
    min_price = df_display["Price"].min()
    max_price = df_display["Price"].max()
    min_timestamp = df_display[df_display["Price"] == min_price]["Timestamp"].iloc[0]
    max_timestamp = df_display[df_display["Price"] == max_price]["Timestamp"].iloc[0]

    fig = go.Figure()

    # Ligne de prix actuelle
    fig.add_trace(go.Scatter(
        x=df_display["Timestamp"],
        y=df_display["Price"],
        mode='lines',
        name='Prix Actuel',
        line=dict(color=COLORS["bitcoin"], width=3),
        hovertemplate='Heure: %{x}<br>Prix: $%{y:.2f}<extra></extra>',
    ))

    # Ajouter les prédictions si disponibles
    if predictions_df is not None and not predictions_df.empty:
        # Ajuster l'échelle y si nécessaire
        all_prices = list(df_display["Price"]) + list(predictions_df["Predicted_Price"])
        upper_percentile = max(upper_percentile, np.percentile(all_prices, 95))
        
        # Ajouter la ligne de prédiction en pointillés
        fig.add_trace(go.Scatter(
            x=predictions_df["Timestamp"],
            y=predictions_df["Predicted_Price"],
            mode='lines',
            name='Prédiction',
            line=dict(color=COLORS["prediction"], width=2, dash='dash'),
            hovertemplate='Prédiction pour: %{x}<br>Prix prévu: $%{y:.2f}<extra></extra>',
        ))
        
        # Connecter le dernier point réel au premier point prédit pour une transition fluide
        last_real_time = df_display["Timestamp"].iloc[-1]
        last_real_price = df_display["Price"].iloc[-1]
        first_pred_time = predictions_df["Timestamp"].iloc[0]
        first_pred_price = predictions_df["Predicted_Price"].iloc[0]
        
        fig.add_trace(go.Scatter(
            x=[last_real_time, first_pred_time],
            y=[last_real_price, first_pred_price],
            mode='lines',
            line=dict(color=COLORS["prediction"], width=1, dash='dot'),
            showlegend=False,
            hoverinfo='none'
        ))

    # Highlight min and max
    fig.add_trace(go.Scatter(
        x=[min_timestamp],
        y=[min_price],
        mode='markers',
        name='Min',
        marker=dict(color=COLORS["negative"], size=10),
        showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=[max_timestamp],
        y=[max_price],
        mode='markers',
        name='Max',
        marker=dict(color=COLORS["positive"], size=10),
        showlegend=False
    ))

    fig.update_layout(
        title="📈 Evolution du Prix du Bitcoin avec Prédictions",
        plot_bgcolor=COLORS["background"],
        paper_bgcolor=COLORS["background"],
        font=dict(family="Inter", color=COLORS["text"]),
        xaxis=dict(
            title="Date & Heure",
            showgrid=True,
            gridcolor=COLORS["grid"],
            tickangle=-45,
            rangeslider=dict(visible=True),  # Slider for navigation
            type="date",
            tickfont=dict(color=COLORS["text"])
        ),
        yaxis=dict(
            title="Prix (USD)",
            showgrid=True,
            gridcolor=COLORS["grid"],
            tickprefix="$",
            range=[lower_percentile * 0.98, upper_percentile * 1.02],
            tickfont=dict(color=COLORS["text"])
        ),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color=COLORS["text"])
        )
    )

    return fig

def create_volatility_graph(df, window=14):
    """Create a volatility graph based on price data."""
    if len(df) < window:
        return go.Figure()
    
    # Limiter pour l'affichage
    df = df.tail(MAX_DATA_POINTS * 2).copy()  # Plus de données pour les calculs
    
    # Calculate rolling volatility
    df['return'] = df['Price'].pct_change()
    df['volatility'] = df['return'].rolling(window=min(window, len(df))).std() * np.sqrt(365) * 100  # Annualized and in percentage
    
    # Create the figure
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["Timestamp"].tail(MAX_DATA_POINTS),
        y=df["volatility"].tail(MAX_DATA_POINTS),
        mode='lines',
        name='Volatilité',
        line=dict(color="#FF9500", width=2),
        hovertemplate='Date: %{x}<br>Volatilité: %{y:.2f}%<extra></extra>',
    ))
    
    fig.update_layout(
        title="📊 Volatilité du Bitcoin (annualisée)",
        plot_bgcolor=COLORS["background"],
        paper_bgcolor=COLORS["background"],
        font=dict(family="Inter", color=COLORS["text"]),
        xaxis=dict(
            title="Date & Heure",
            showgrid=True,
            gridcolor=COLORS["grid"],
            tickangle=-45,
            type="date",
            tickfont=dict(color=COLORS["text"])
        ),
        yaxis=dict(
            title="Volatilité (%)",
            showgrid=True,
            gridcolor=COLORS["grid"],
            ticksuffix="%",
            tickfont=dict(color=COLORS["text"])
        ),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig

def create_dashboard_layout():
    """Create the dashboard layout with prediction metrics."""
    return html.Div([
        html.Div([
            html.H1("Bitcoin Live Monitor & Prédiction", className="dashboard-title"),
            html.Div(id="current-price", className="current-price")
        ], className="dashboard-header"),
        
        html.Div([
            html.Div([
                dcc.Graph(id="price-graph", config={'displayModeBar': False})
            ], className="graph-container"),
            
            html.Div([
                dcc.Graph(id="volatility-graph", config={'displayModeBar': False})
            ], className="graph-container"),
            
            html.Div([
                html.Div(id="daily-report", className="report-container")
            ], className="report-card"),
            
            html.Div([
                html.Div(id="risk-metrics", className="report-container")
            ], className="report-card"),
            
            # Section pour les métriques de prédiction
            html.Div([
                html.Div(id="prediction-metrics", className="report-container")
            ], className="report-card")
        ], className="content-wrapper"),
        
        # Interval component pour mettre à jour les données
        dcc.Interval(id="interval-component", interval=60000)  # Mise à jour toutes les 60 secondes
    ], className="dashboard-container")

# Single callback to update all components
@app.callback(
    [Output("price-graph", "figure"),
     Output("volatility-graph", "figure"),
     Output("current-price", "children"),
     Output("daily-report", "children"),
     Output("risk-metrics", "children"),
     Output("prediction-metrics", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_dashboard(n):
    """Comprehensive dashboard update function."""
    try:
        # Run scraper and daily report scripts
        subprocess.run(["/bin/bash", os.path.join(BASE_PATH, "scraper.sh")], check=True)
        subprocess.run(["/bin/bash", os.path.join(BASE_PATH, "daily_report.sh")], check=True)

    except Exception as e:
        print(f"❌ Script execution error: {e}")
    
    # Load all data for predictions
    df_full = load_data()
    
    if df_full.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            plot_bgcolor=COLORS["background"],
            paper_bgcolor=COLORS["background"]
        )
        empty_prediction_metrics = html.Div("No prediction data available")
        return empty_fig, empty_fig, "N/A", html.Div("No data available"), html.Div("No data available"), empty_prediction_metrics
    
    # Data for display
    df_display = df_full.tail(MAX_DATA_POINTS).copy()
    
    # Train model and generate predictions
    predictions_df, eval_metrics = train_model_and_predict(df_full)
    
    # Create price graph with predictions
    price_fig = create_price_graph(df_display, predictions_df)
    
    # Create volatility graph
    volatility_fig = create_volatility_graph(df_full)
    
    current_price = f"${df_display['Price'].iloc[-1]:,.2f}"
    
    # Calculate risk metrics
    volatility = calculate_volatility(df_display)
    var_95 = calculate_var(df_display, confidence=0.95)
    var_99 = calculate_var(df_display, confidence=0.99)
    
    # Load daily report
    report = load_daily_report()
    
    if report is None:
        daily_report_html = html.Div("No report available")
    else:
        daily_report_html = html.Div([
            html.H3("Rapport Quotidien Bitcoin", className="report-title"),
            html.Div([
                html.Div([
                    html.Span("Horodatage", className="report-label"),
                    html.Span(report["Timestamp"].strftime("%Y-%m-%d %H:%M:%S"), className="report-value")
                ], className="report-item"),
                html.Div([
                    html.Span("Prix d'ouverture", className="report-label"),
                    html.Span(f"${report['Open']:,.2f}", className="report-value")
                ], className="report-item"),
                html.Div([
                    html.Span("Prix de clôture", className="report-label"),
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
    
    # Create risk metrics card with improved layout
    risk_metrics_html = html.Div([
        html.H3("Métriques de Risque", className="report-title"),
        html.Div([
            html.Div([
                html.Div([
                    html.Span("Volatilité (annualisée)", className="risk-label"),
                    html.Div([
                        html.Span(f"{volatility * 100:.2f}%", className="risk-value"),
                    ], className="risk-value-container")
                ], className="risk-header"),
                html.Div("Mesure de la variance des prix sur la période", className="risk-description")
            ], className="risk-item"),
            
            html.Div([
                html.Div([
                    html.Span("VaR 95%", className="risk-label"),
                    html.Div([
                        html.Span(f"{var_95:.2f}%", className="risk-value"),
                    ], className="risk-value-container")
                ], className="risk-header"),
                html.Div("Perte maximale sur une journée avec 95% de confiance", className="risk-description")
            ], className="risk-item"),
            
            html.Div([
                html.Div([
                    html.Span("VaR 99%", className="risk-label"),
                    html.Div([
                        html.Span(f"{var_99:.2f}%", className="risk-value"),
                    ], className="risk-value-container")
                ], className="risk-header"),
                html.Div("Perte maximale sur une journée avec 99% de confiance", className="risk-description")
            ], className="risk-item")
        ], className="risk-grid")
    ], className="report-container")
    
    # Créer la section des métriques de prédiction
    if predictions_df is not None and eval_metrics is not None and not predictions_df.empty:
        # Calculer la prédiction pour la prochaine journée
        next_day_prediction = predictions_df['Predicted_Price'].iloc[-1]
        current_price_value = df_display['Price'].iloc[-1]
        price_change = (next_day_prediction - current_price_value) / current_price_value * 100
        
        prediction_metrics_html = html.Div([
            html.H3("Prévisions & Métriques du Modèle", className="report-title"),
            html.Div([
                html.Div([
                    html.Div([
                        html.Span("Prédiction à 24h", className="risk-label"),
                        html.Div([
                            html.Span(f"${next_day_prediction:.2f}", className="risk-value"),
                        ], className="risk-value-container")
                    ], className="risk-header"),
                    html.Div(f"Variation prévue: {price_change:.2f}%", 
                             className="risk-description",
                             style={"color": COLORS["positive"] if price_change >= 0 else COLORS["negative"]})
                ], className="risk-item"),
                
                html.Div([
                    html.Div([
                        html.Span("Précision du Modèle (MAE)", className="risk-label"),
                        html.Div([
                            html.Span(f"${eval_metrics['MAE']:.2f}", className="risk-value"),
                        ], className="risk-value-container")
                    ], className="risk-header"),
                    html.Div("Erreur absolue moyenne des prédictions", className="risk-description")
                ], className="risk-item"),
                
                html.Div([
                    html.Div([
                        html.Span("Précision du Modèle (RMSE)", className="risk-label"),
                        html.Div([
                            html.Span(f"${eval_metrics['RMSE']:.2f}", className="risk-value"),
                        ], className="risk-value-container")
                    ], className="risk-header"),
                    html.Div("Erreur quadratique moyenne des prédictions", className="risk-description")
                ], className="risk-item"),
                
                html.Div([
                    html.Div([
                        html.Span("Facteur le Plus Influent", className="risk-label"),
                        html.Div([
                            html.Span(max(eval_metrics['Feature_Importance'].items(), key=lambda x: x[1])[0], className="risk-value"),
                        ], className="risk-value-container")
                    ], className="risk-header"),
                    html.Div("Variable ayant le plus d'impact sur les prédictions", className="risk-description")
                ], className="risk-item")
            ], className="risk-grid")
        ], className="report-container")
    else:
        prediction_metrics_html = html.Div([
            html.H3("Prévisions", className="report-title"),
            html.Div("Données insuffisantes pour générer des prédictions fiables.", 
                     style={"padding": "20px", "text-align": "center", "color": "#B0B0B0"})
        ], className="report-container")
    
    return price_fig, volatility_fig, current_price, daily_report_html, risk_metrics_html, prediction_metrics_html

# Application Layout
app.layout = create_dashboard_layout()
# Custom Index String with Dark Mode Styling
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        <title>Bitcoin Live Dashboard & Prédiction</title>
        {%metas%}
        {%favicon%}
        {%css%}
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            body {
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 0;
                background-color: #1C1C1E;
                color: #FFFFFF;
                line-height: 1.6;
            }
            
            .dashboard-container {
                max-width: 100%; 
                width: 100%;      
                margin: 0 auto;   
                padding: 20px;    
                box-sizing: border-box; 
                overflow: hidden;
            }
            
            .dashboard-header {
                margin-bottom: 30px;
            }
            
            .content-wrapper {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                justify-content: center;
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
            
            .graph-container {
                background-color: #2C2C2E;
                border-radius: 12px;
                padding: 15px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                margin-bottom: 20px;
            }
            
            .report-card {
                background-color: #2C2C2E;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                margin-bottom: 20px;
            }
            
            .report-title {
                color: #F7931A;
                font-size: 22px;
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
                flex-direction: column;
                padding: 15px;
                background-color: #3A3A3C;
                border-radius: 8px;
            }
            
            .report-label {
                color: #B0B0B0;
                font-size: 14px;
                margin-bottom: 5px;
            }
            
            .report-value {
                color: #FFFFFF;
                font-weight: 600;
                font-size: 18px;
            }
            
            /* Styles spécifiques pour les métriques de risque */
            .risk-grid {
                display: grid;
                gap: 15px;
            }
            
            .risk-item {
                background-color: #3A3A3C;
                border-radius: 8px;
                padding: 15px;
            }
            
            .risk-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            
            .risk-label {
                color: #B0B0B0;
                font-size: 14px;
                font-weight: 500;
            }
            
            .risk-value {
                font-size: 18px;
                font-weight: 600;
                color: #FFFFFF;
            }
            
            .risk-description {
                color: #8E8E93;
                font-size: 12px;
                font-style: italic;
            }
            
            @media (min-width: 992px) {
                .content-wrapper {
                    grid-template-columns: repeat(2, 1fr);
                }
                
                .graph-container:nth-child(1),
                .graph-container:nth-child(2) {
                    grid-column: span 2;
                }
            }
            
            @media (max-width: 768px) {
                .content-wrapper {
                    grid-template-columns: 1fr;
                }
                
                .graph-container,
                .report-card {
                    grid-column: span 1;
                }
                
                .current-price {
                    font-size: 36px;
                }
                
                .risk-header {
                    flex-direction: column;
                    align-items: flex-start;
                }
                
                .risk-value-container {
                    margin-top: 5px;
                    width: 100%;
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
