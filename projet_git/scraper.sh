#!/bin/bash

# URL de l'API CoinGecko pour récupérer le prix du Bitcoin
URL="https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

# Fichier de stockage des données
DATA_FILE="projet.csv"
LOG_FILE="cron_debug.log"

# Récupérer les données JSON de l'API
PRICE=$(curl -s "$URL" | grep -oP '(?<="usd":)[0-9.]+')

# Vérifier si le prix est valide (éviter d'écrire une ligne vide)
if [[ -z "$PRICE" || "$PRICE" == "null" ]]; then
    echo "[$(date)] Erreur : Prix non récupéré !" >> "$LOG_FILE"
    exit 1
fi

# Ajouter un horodatage et sauvegarder les données
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
echo "$TIMESTAMP,$PRICE" >> "$DATA_FILE"
echo "🔍 Contenu actuel de projet.csv :"
cat "$DATA_FILE"

# Afficher les données pour le débogage
echo "[$TIMESTAMP] Prix récupéré : $PRICE"
echo "[$TIMESTAMP] Prix enregistré : $PRICE" >> "$LOG_FILE"
