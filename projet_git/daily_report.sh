#!/bin/bash

DATA_FILE="/home/edgar/projet_git/projet.csv"
REPORT_FILE="/home/edgar/projet_git/daily_report.csv"
LOG_FILE="/home/edgar/projet_git/cron_debug.log"

# Filtrer les données du jour
TODAY=$(date "+%Y-%m-%d")
grep "$TODAY" "$DATA_FILE" > temp_data.csv

# Vérifier si on a des données valides
if [[ ! -s temp_data.csv ]]; then
    echo "[$(date)] ❌ Aucune donnée pour aujourd'hui !" >> "$LOG_FILE"
    exit 1
fi

# Extraire les prix
OPEN=$(head -n 1 temp_data.csv | cut -d',' -f2)
CLOSE=$(tail -n 1 temp_data.csv | cut -d',' -f2)
MAX=$(cut -d',' -f2 temp_data.csv | sort -nr | head -n1)
MIN=$(cut -d',' -f2 temp_data.csv | sort -n | head -n1)

# Calcul de la variation en pourcentage
EVOLUTION=$(awk "BEGIN {print (($CLOSE - $OPEN) / $OPEN) * 100}")

# Écrire dans le fichier rapport
echo "$TODAY,$OPEN,$CLOSE,$MAX,$MIN,$EVOLUTION%" >> "$REPORT_FILE"
echo "[$(date)] ✅ Rapport généré : $TODAY" >> "$LOG_FILE"

# Nettoyage
rm temp_data.csv
