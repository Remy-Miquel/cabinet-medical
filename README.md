# Cabinet Médical — Application deux étages (WEB-01 / APP-01)

Application de démonstration fidèle au dossier technique : front-end en DMZ,
back-end interne, RBAC 3 rôles, PostgreSQL. La séparation front/back est la
base de la segmentation réseau (moindre privilège, section 5.3.2).

## Architecture

```
Navigateur (patient/médecin)
      │ HTTPS 443
      ▼
  WEB-01 (DMZ)  ── Flask ── sert les pages, détient le JWT en session
      │ HTTPS 8443 (appel API, filtré par pfSense)
      ▼
  APP-01 (interne) ── FastAPI ── RBAC + logique métier
      │ 5432 (local)
      ▼
  PostgreSQL (dossiers médicaux)
```

WEB-01 ne parle JAMAIS à la base. APP-01 porte le contrôle d'accès.

## RBAC — qui voit quoi

| Action              | patient | secrétariat | médecin |
|---------------------|:-------:|:-----------:|:-------:|
| login               |   ✓     |     ✓       |   ✓     |
| son propre dossier  |   ✓     |     ✗       |   ✓     |
| liste patients      |   ✗     |  ✓ (admin)  | ✓ (complet) |
| contenu clinique    |   ✗     |     ✗       |   ✓     |

---

## Déploiement APP-01 (172.16.10.2 — serveur interne)

### 1. PostgreSQL
```bash
sudo apt update && sudo apt install -y postgresql
sudo -u postgres psql <<'SQL'
CREATE DATABASE cabinet;
CREATE USER cabinet_service WITH PASSWORD 'un_mot_de_passe_fort';
GRANT ALL PRIVILEGES ON DATABASE cabinet TO cabinet_service;
\c cabinet
GRANT ALL ON SCHEMA public TO cabinet_service;
SQL
```
> Le compte `cabinet_service` est un compte de service à privilèges limités
> (section 5.3.4), distinct de `postgres` (admin).

### 2. Application
```bash
cd app-01-backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export DB_USER=cabinet_service
export DB_PASSWORD=un_mot_de_passe_fort
export DB_NAME=cabinet
export JWT_SECRET=$(openssl rand -hex 32)   # clé de signature forte

python3 seed.py            # crée les comptes de démo
uvicorn main:app --host 0.0.0.0 --port 8443
```

Comptes de démo créés par `seed.py` :
- médecin : `dr_martin` / `medecin123`
- secrétariat : `secretaire` / `secret123`
- patient : `patient_durand` / `patient123`

---

## Déploiement WEB-01 (192.168.30.2 — DMZ)

```bash
cd web-01-frontend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export API_URL=http://172.16.10.2:8443     # vers APP-01
export FLASK_SECRET=$(openssl rand -hex 32)

python3 app.py                             # écoute sur :5000 (dev)
```

Ouvre `http://192.168.30.2:5000` et connecte-toi avec un des comptes.

---

## Étape suivante : sécurisation (une fois l'appli fonctionnelle)

- TLS partout : HTTPS 443 sur WEB-01, HTTPS 8443 sur APP-01 (chiffrement en transit).
- Règles pfSense : WEB-01 → APP-01:8443 uniquement, DMZ isolée du LAN interne.
- NAT port-forward WAN:443 → WEB-01 pour l'accès patients.
- MFA sur les comptes médecins.
- Journalisation vers Wazuh (traçabilité art. 5§2 RGPD).
