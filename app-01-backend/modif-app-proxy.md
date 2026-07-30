# Modif app.py — faire confiance au reverse proxy nginx

Ajouter ProxyFix pour que Flask lise correctement les headers
X-Forwarded-* envoyés par nginx (schéma HTTPS, IP réelle du client).

## En haut de app.py, après les imports existants :

    from werkzeug.middleware.proxy_fix import ProxyFix

## Juste après la ligne  app = Flask(__name__)  ajouter :

    # Derrière nginx : lire les X-Forwarded-* (HTTPS, IP réelle)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

## Et sécuriser les cookies de session — après app.secret_key = ... :

    app.config.update(
        SESSION_COOKIE_SECURE=True,      # cookie envoyé uniquement en HTTPS
        SESSION_COOKIE_HTTPONLY=True,    # inaccessible au JavaScript (anti-XSS)
        SESSION_COOKIE_SAMESITE="Lax",   # protection CSRF de base
    )

## Enfin, retirer le app.run(debug=True) en bas (Gunicorn le remplace) :
# On peut le garder pour le dev local, mais en prod c'est Gunicorn qui lance.
