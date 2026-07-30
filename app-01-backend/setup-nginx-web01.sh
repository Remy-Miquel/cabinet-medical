#!/bin/bash
# ============================================================
# WEB-01 — Mise en place nginx + HTTPS + Gunicorn
# À lancer en root sur WEB-01 : sudo bash setup-nginx-web01.sh
# ============================================================
set -e

echo "[1/6] Installation nginx + openssl..."
apt update
apt install -y nginx openssl

echo "[2/6] Génération du certificat auto-signé..."
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/cabinet.key \
    -out /etc/nginx/ssl/cabinet.crt \
    -subj "/C=FR/ST=NouvelleAquitaine/L=Limoges/O=Cabinet Medical/CN=cabinet.local"
chmod 600 /etc/nginx/ssl/cabinet.key

echo "[3/6] Installation de la config nginx..."
cp nginx-cabinet.conf /etc/nginx/sites-available/cabinet
ln -sf /etc/nginx/sites-available/cabinet /etc/nginx/sites-enabled/cabinet
# Retire le site par défaut
rm -f /etc/nginx/sites-enabled/default

echo "[4/6] Test de la config nginx..."
nginx -t

echo "[5/6] Redémarrage nginx..."
systemctl restart nginx
systemctl enable nginx

echo "[6/6] Terminé !"
echo ""
echo "nginx écoute maintenant sur :"
echo "  - HTTP  80  -> redirige vers HTTPS"
echo "  - HTTPS 443 -> proxy vers Flask (127.0.0.1:5000)"
echo ""
echo "Prochaine étape : lancer Flask via Gunicorn sur 127.0.0.1:5000"
echo "  (voir start-gunicorn.sh)"
