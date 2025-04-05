#!/bin/bash

# Définir les chemins absolus basés sur l'emplacement du script
BASE_DIR="$(dirname "$0")"
DATA_FILE="$BASE_DIR/projet.csv"
REPORT_FILE="$BASE_DIR/daily_report.csv"
LOG_FILE="$BASE_DIR/cron_debug.log"

echo "📊 [$(date)] Script daily_report.sh lancé" | tee -a "$LOG_FILE"

# Créer les fichiers s'ils n'existent pas
touch "$DATA_FILE" "$REPORT_FILE" "$LOG_FILE"

# Obtenir la date actuelle
TODAY=$(date "+%Y-%m-%d")
CURRENT_TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Extraire les lignes du jour
grep "$TODAY" "$DATA_FILE" > "$BASE_DIR/temp_data.csv"

# Vérification de données disponibles
if [[ ! -s "$BASE_DIR/temp_data.csv" ]]; then
    echo "❌ [$(date)] Aucune donnée pour aujourd'hui ($TODAY) !" | tee -a "$LOG_FILE"
    rm "$BASE_DIR/temp_data.csv"
    exit 1
fi

# Extraction des valeurs
OPEN=$(head -n 1 "$BASE_DIR/temp_data.csv" | cut -d',' -f2)
CLOSE=$(tail -n 1 "$BASE_DIR/temp_data.csv" | cut -d',' -f2)
MAX=$(cut -d',' -f2 "$BASE_DIR/temp_data.csv" | sort -nr | head -n1)
MIN=$(cut -d',' -f2 "$BASE_DIR/temp_data.csv" | sort -n | head -n1)

# Calcul de l'évolution
EVOLUTION=$(awk "BEGIN {printf \"%.2f\", (($CLOSE - $OPEN) / $OPEN) * 100}")

# Validation des valeurs
if [[ -z "$OPEN" || -z "$CLOSE" || -z "$MAX" || -z "$MIN" ]]; then
    echo "❌ [$(date)] Erreur : données manquantes pour le calcul" | tee -a "$LOG_FILE"
    rm "$BASE_DIR/temp_data.csv"
    exit 1
fi

# Écriture dans le rapport
echo "$CURRENT_TIMESTAMP,$OPEN,$CLOSE,$MAX,$MIN,${EVOLUTION}%" > "$REPORT_FILE"
echo "✅ [$(date)] Rapport généré avec succès." | tee -a "$LOG_FILE"

# Nettoyage
rm "$BASE_DIR/temp_data.csv"
