#!/bin/bash
# Définir les chemins absolus pour le conteneur
DATA_FILE="/app/projet.csv"
REPORT_FILE="/app/daily_report.csv"
LOG_FILE="/app/cron_debug.log"

# Créer les fichiers s'ils n'existent pas
touch "$DATA_FILE" "$REPORT_FILE" "$LOG_FILE"

# Obtenir la date et l'heure actuelles de manière précise
CURRENT_TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Filtrer les données du jour
TODAY=$(date "+%Y-%m-%d")
grep "$TODAY" "$DATA_FILE" > temp_data.csv

# Vérifier si on a des données valides
if [[ ! -s temp_data.csv ]]; then
    echo "[$(date)] ❌ Aucune donnée pour aujourd'hui !" >> "$LOG_FILE"
    rm temp_data.csv
    exit 1
fi

# Extraire les prix avec des valeurs par défaut
OPEN=$(head -n 1 temp_data.csv | cut -d',' -f2)
CLOSE=$(tail -n 1 temp_data.csv | cut -d',' -f2)
MAX=$(cut -d',' -f2 temp_data.csv | sort -nr | head -n1)
MIN=$(cut -d',' -f2 temp_data.csv | sort -n | head -n1)

# Calcul de la variation en pourcentage
EVOLUTION=$(awk "BEGIN {print (($CLOSE - $OPEN) / $OPEN) * 100}")

# Vérification de la validité des prix pour éviter les erreurs
if ! [[ "$OPEN" =~ ^[0-9]+(\.[0-9]+)?$ ]] || ! [[ "$CLOSE" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "[$(date)] ❌ OPEN ou CLOSE non numériques!" >> "$LOG_FILE"
    rm temp_data.csv
    exit 1
fi

# Calcul de la volatilité (écart-type des prix)
PRICES=$(cut -d',' -f2 temp_data.csv)
VOLATILITY=$(echo "$PRICES" | awk '{sum+=$1; sumsq+=$1*$1} END {print sqrt(sumsq/NR - (sum/NR)**2)}')

# Vérifier si les calculs sont valides
if [[ -z "$OPEN" || -z "$CLOSE" || -z "$MAX" || -z "$MIN" || -z "$VOLATILITY" ]]; then
    echo "[$(date)] ❌ Calculs invalides !" >> "$LOG_FILE"
    rm temp_data.csv
    exit 1
fi

# Afficher les résultats intermédiaires pour le débogage
echo "Open: $OPEN, Close: $CLOSE, Max: $MAX, Min: $MIN"
echo "Evolution: $EVOLUTION, Volatility: $VOLATILITY"

# Écrire dans le fichier rapport avec un timestamp précis et inclure la volatilité
echo "$CURRENT_TIMESTAMP,$OPEN,$CLOSE,$MAX,$MIN,${EVOLUTION}%,${VOLATILITY}" > "$REPORT_FILE"
echo "[$(date)] ✅ Rapport généré : $CURRENT_TIMESTAMP" >> "$LOG_FILE"

# Nettoyage
rm temp_data.csv
