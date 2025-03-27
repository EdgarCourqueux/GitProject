LOG_FILE="/app/cron_debug.log"
 # Créer les fichiers s'ils n'existent pas
 touch "$DATA_FILE" "$REPORT_FILE" "$LOG_FILE"
 
 # Obtenir la date et l'heure actuelles de manière précise
 CURRENT_TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
 
 # Filtrer les données du jour
 TODAY=$(date "+%Y-%m-%d")
 grep "$TODAY" "$DATA_FILE" > temp_data.csv
 @@ -34,9 +37,9 @@ if [[ -z "$OPEN" || -z "$CLOSE" || -z "$MAX" || -z "$MIN" ]]; then
     exit 1
 fi
 
 # Écrire dans le fichier rapport
 echo "$TODAY,$OPEN,$CLOSE,$MAX,$MIN,${EVOLUTION}%" > "$REPORT_FILE"
 echo "[$(date)] ✅ Rapport généré : $TODAY" >> "$LOG_FILE"
 # Écrire dans le fichier rapport avec un timestamp précis
 echo "$CURRENT_TIMESTAMP,$OPEN,$CLOSE,$MAX,$MIN,${EVOLUTION}%" > "$REPORT_FILE"
 echo "[$(date)] ✅ Rapport généré : $CURRENT_TIMESTAMP" >> "$LOG_FILE"
 
 # Nettoyage
 rm temp_data.csv
