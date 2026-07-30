#!/bin/bash
# ============================================================
# WEB-01 — Lancement du front via Gunicorn (production)
# Gunicorn écoute UNIQUEMENT en local (127.0.0.1:5000).
# Seul nginx y accède ; l'extérieur passe par nginx en HTTPS.
# ============================================================
cd ~/cabinet-medical/web-01-frontend
source venv/bin/activate

# Variables d'environnement (à adapter)
export API_URL=http://172.16.10.2:8443
export FLASK_SECRET=$(openssl rand -hex 32)

# Gunicorn : 3 workers, bind local uniquement
# 'app:app' = fichier app.py, objet Flask nommé 'app'
gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
