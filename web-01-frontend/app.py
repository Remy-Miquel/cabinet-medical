"""
WEB-01 — Front-end du cabinet médical (Flask, zone DMZ)
Cabinet médical — dossier technique section 5.3.1

RÔLE : servir l'interface web et relayer vers l'API APP-01.
Ce serveur NE contient AUCUNE donnée médicale et NE parle JAMAIS à la base.
Il détient uniquement le JWT de l'utilisateur (en session) et le présente
à l'API. Compromis, il ne donne accès à rien de plus que l'API n'autorise.
"""
import os
import requests
from flask import Flask, request, session, redirect, url_for, render_template, flash

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-front-a-changer")

# Adresse de l'API interne APP-01. En prod : HTTPS 8443 vers 172.16.10.2,
# flux autorisé par pfSense uniquement depuis WEB-01.
API_URL = os.getenv("API_URL", "http://172.16.10.2:8443")


def api_headers():
    """Ajoute le token JWT de l'utilisateur connecté aux appels API."""
    token = session.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


@app.route("/")
def index():
    if "token" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", role=session.get("role"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            r = requests.post(f"{API_URL}/token",
                              json={"username": username, "password": password},
                              timeout=5)
        except requests.RequestException:
            flash("API indisponible. Réessayez plus tard.")
            return render_template("login.html")

        if r.status_code == 200:
            data = r.json()
            session["token"] = data["access_token"]
            session["role"] = data["role"]
            session["username"] = username
            return redirect(url_for("index"))
        flash("Identifiants incorrects.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/mon-dossier")
def mon_dossier():
    """Patient : consulte son propre dossier via l'API."""
    r = requests.get(f"{API_URL}/mon-dossier", headers=api_headers(), timeout=5)
    if r.status_code == 200:
        return render_template("dossier.html", dossier=r.json())
    if r.status_code == 403:
        return render_template("erreur.html", message="Accès réservé aux patients."), 403
    return render_template("erreur.html", message="Dossier indisponible."), r.status_code


@app.route("/patients")
def patients():
    """Secrétariat / médecin : liste des patients (vue selon rôle côté API)."""
    r = requests.get(f"{API_URL}/patients", headers=api_headers(), timeout=5)
    if r.status_code == 200:
        return render_template("patients.html",
                               patients=r.json(), role=session.get("role"))
    if r.status_code == 403:
        return render_template("erreur.html",
                               message="Accès réservé au personnel du cabinet."), 403
    return render_template("erreur.html", message="Liste indisponible."), r.status_code


if __name__ == "__main__":
    # En DMZ, WEB-01 écoute en HTTPS 443 (TLS ajouté à l'étape sécurisation).
    # Pour le dev local on écoute en 5000.
    app.run(host="0.0.0.0", port=5000, debug=True)
