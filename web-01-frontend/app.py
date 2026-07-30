"""
WEB-01 — Front-end du cabinet médical (Flask, zone DMZ) — version durcie
Sécurité applicative : CSRF, rate-limiting, validation, cookies sécurisés,
révocation du token à la déconnexion. Ne stocke aucune donnée médicale.
"""
import os
import requests
from flask import Flask, request, session, redirect, url_for, render_template, flash
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from email_validator import validate_email, EmailNotValidError

app = Flask(__name__)

# --- Secret de session (obligatoire, fort) ---
app.secret_key = os.getenv("FLASK_SECRET")
if not app.secret_key or len(app.secret_key) < 32:
    raise RuntimeError("FLASK_SECRET manquant ou trop court. openssl rand -hex 32")

# --- Derrière le reverse proxy nginx ---
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# --- Cookies de session sécurisés ---
app.config.update(
    SESSION_COOKIE_SECURE=True,        # HTTPS uniquement
    SESSION_COOKIE_HTTPONLY=True,      # inaccessible au JS (anti-XSS)
    SESSION_COOKIE_SAMESITE="Lax",     # anti-CSRF de base
    WTF_CSRF_TIME_LIMIT=3600,
)

# --- Protection CSRF sur tous les formulaires POST ---
csrf = CSRFProtect(app)

# --- Rate-limiting (anti-brute-force) ---
limiter = Limiter(get_remote_address, app=app, default_limits=["200/hour"])

API_URL = os.getenv("API_URL", "http://172.16.10.2:8443")


def api_headers():
    token = session.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


@app.route("/")
def index():
    if "token" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", role=session.get("role"))


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5/minute", methods=["POST"])     # max 5 tentatives login/min
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Validation des entrées côté front
        if not email or not password:
            flash("Veuillez remplir tous les champs.")
            return render_template("login.html")
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            flash("Adresse email invalide.")
            return render_template("login.html")
        if len(password) > 128:
            flash("Identifiants incorrects.")
            return render_template("login.html")

        try:
            r = requests.post(f"{API_URL}/token",
                              json={"email": email, "password": password},
                              timeout=5)
        except requests.RequestException:
            flash("Service indisponible. Réessayez plus tard.")
            return render_template("login.html")

        if r.status_code == 200:
            data = r.json()
            session.clear()                        # nouvelle session propre
            session["token"] = data["access_token"]
            session["role"] = data["role"]
            session["email"] = email
            return redirect(url_for("index"))
        if r.status_code == 429:
            flash("Trop de tentatives. Réessayez dans quelques instants.")
        else:
            flash("Identifiants incorrects.")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])            # POST only (protégé CSRF)
def logout():
    # Révoque le token côté API avant de vider la session
    try:
        requests.post(f"{API_URL}/logout", headers=api_headers(), timeout=5)
    except requests.RequestException:
        pass
    session.clear()
    return redirect(url_for("login"))


@app.route("/mon-dossier")
def mon_dossier():
    if "token" not in session:
        return redirect(url_for("login"))
    try:
        r = requests.get(f"{API_URL}/mon-dossier", headers=api_headers(), timeout=5)
    except requests.RequestException:
        return render_template("erreur.html", message="Service indisponible."), 503
    if r.status_code == 200:
        return render_template("dossier.html", dossier=r.json())
    if r.status_code == 401:
        session.clear()
        return redirect(url_for("login"))
    if r.status_code == 403:
        return render_template("erreur.html", message="Accès réservé aux patients."), 403
    return render_template("erreur.html", message="Dossier indisponible."), r.status_code


@app.route("/patients")
def patients():
    if "token" not in session:
        return redirect(url_for("login"))
    try:
        r = requests.get(f"{API_URL}/patients", headers=api_headers(), timeout=5)
    except requests.RequestException:
        return render_template("erreur.html", message="Service indisponible."), 503
    if r.status_code == 200:
        return render_template("patients.html", patients=r.json(), role=session.get("role"))
    if r.status_code == 401:
        session.clear()
        return redirect(url_for("login"))
    if r.status_code == 403:
        return render_template("erreur.html", message="Accès réservé au personnel."), 403
    return render_template("erreur.html", message="Liste indisponible."), r.status_code


# Handler propre pour les erreurs de rate-limit
@app.errorhandler(429)
def ratelimit_handler(e):
    flash("Trop de requêtes. Patientez un instant.")
    return render_template("login.html"), 429


if __name__ == "__main__":
    # Dev local uniquement — en production, Gunicorn + nginx
    app.run(host="127.0.0.1", port=5000)
