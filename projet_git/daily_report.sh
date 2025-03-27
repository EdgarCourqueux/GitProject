#!/bin/bash
# Définir les chemins absolus pour le conteneur
DATA_FILE="/app/projet.csv"
REPORT_FILE="/app/daily_report.csv"
LOG_FILE="/app/cron_debug.log"

# Créer les fichiers s'ils n'existent pas
touch "$DATA_FILE" "$REPORT_FILE" "$LOG_FILE"

# Obtenir la date actuelle
TODAY=$(date "+%Y-%m-%d")

# Filtrer les données du jour jusqu'à 20:00
awk -F, -v date="$TODAY" '{if ($1 >= date " 00:00:00" && $1 <= date " 20:00:00") print $0}' "$DATA_FILE" > temp_data.csv

# Vérifier si on a des données valides
if [[ ! -s temp_data.csv ]]; then
    echo "[$(date)] ❌ Aucune donnée pour aujourd'hui jusqu'à 20:00 !" >> "$LOG_FILE"
    rm temp_data.csv
    exit 1
fi

# Extraire les prix avec des valeurs par défaut
OPEN=$(head -n 1 temp_data.csv | cut -d',' -f2)
CLOSE=$(tail -n 1 temp_data.csv | cut -d',' -f2)
MAX=$(cut -d',' -f2 temp_data.csv | sort -nr | head -n1)
MIN=$(cut -d',' -f2 temp_data.csv | sort -n | head -n1)

# Calcul de la volatilité (écart-type des prix)
PRICES=$(cut -d',' -f2 temp_data.csv)
VOLATILITY=$(echo "$PRICES" | awk '{sum+=$1; sumsq+=$1*$1} END {print sqrt(sumsq/NR - (sum/NR)**2)}')

# Calcul de la variation en pourcentage
EVOLUTION=$(awk "BEGIN {print (($CLOSE - $OPEN) / $OPEN) * 100}")

# Vérifier si les calculs sont valides
if [[ -z "$OPEN" || -z "$CLOSE" || -z "$MAX" || -z "$MIN" || -z "$VOLATILITY" ]]; then
    echo "[$(date)] ❌ Calculs invalides !" >> "$LOG_FILE"
    rm temp_data.csv
    exit 1
fi

# Écrire dans le fichier rapport avec un timestamp précis pour la fin du rapport (20:00)
echo "$(date "+%Y-%m-%d 20:00:00"),$OPEN,$CLOSE,$MAX,$MIN,${EVOLUTION}%,$VOLATILITY" > "$REPORT_FILE"
echo "[$(date)] ✅ Rapport généré jusqu'à 20:00 : $(date "+%Y-%m-%d 20:00:00")" >> "$LOG_FILE"

# Nettoyage
rm temp_data.csv
