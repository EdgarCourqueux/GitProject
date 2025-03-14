#!/bin/bash
# Démarrer le scraper en arrière-plan
nohup bash scraper.sh &
# Lancer le dashboard
python3 dashboard.py
