"""
APP-01 — API back-end du cabinet médical (FastAPI) — version durcie
Sécurité applicative : rate-limiting, validation stricte des entrées,
JWT anti-rejeu, révocation à la déconnexion.
"""
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import (
    get_db, init_db,
    Utilisateur, Role, Medecin, Secretaire, Patient, Dossier,
)
from auth import (
    hash_password, verify_password, create_access_token,
    decode_token, require_role, revoke_token,
)

# --- Rate limiter (limitation de débit anti-brute-force) ---
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Cabinet Médical — API interne (APP-01)")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Trop de tentatives. Réessayez plus tard."},
    )


@app.on_event("startup")
def startup():
    init_db()


# ---------- Schémas de réponse (vues différenciées par rôle) ----------

class VueAdministrative(BaseModel):
    patient: str
    telephone: Optional[str]
    mutuelle: Optional[str]
    prochain_rdv: Optional[str]


class VueComplete(VueAdministrative):
    antecedents: Optional[str]
    diagnostics: Optional[str]
    traitements: Optional[str]


# ---------- Validation stricte des entrées ----------

class LoginBody(BaseModel):
    email: EmailStr                       # format email validé automatiquement
    password: str

    @field_validator("password")
    @classmethod
    def password_non_vide(cls, v: str) -> str:
        if not v or len(v) < 1 or len(v) > 128:
            raise ValueError("Mot de passe invalide")
        return v


class LoginResult(BaseModel):
    access_token: str
    token_type: str
    role: str


# ---------- Authentification ----------

@app.post("/token", response_model=LoginResult)
@limiter.limit("5/minute")                # max 5 tentatives/minute/IP (anti-brute-force)
def login(request: Request, body: LoginBody, db: Session = Depends(get_db)):
    """Login par email. Rate-limité. Renvoie un JWT anti-rejeu."""
    user = db.query(Utilisateur).filter(Utilisateur.email == body.email).first()
    # Message d'erreur identique que l'utilisateur existe ou non (anti-énumération)
    if not user or not user.actif or not verify_password(body.password, user.mot_de_pass_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
        )
    role = user.role_nom
    token = create_access_token(user.email, role, user.id)
    return LoginResult(access_token=token, token_type="bearer", role=role)


@app.post("/logout")
def logout(payload: dict = Depends(decode_token)):
    """Déconnexion : révoque le token courant (anti-rejeu après logout)."""
    revoke_token(payload.get("jti"))
    return {"detail": "Déconnecté"}


# ---------- Endpoints métier avec RBAC ----------

@app.get("/mon-dossier", response_model=VueComplete)
def mon_dossier(payload: dict = Depends(require_role("patient")),
                db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.utilisateur_id == payload["uid"]).first()
    if not patient:
        raise HTTPException(404, "Profil patient introuvable")
    return _vue_complete(patient)


@app.get("/patients")
def liste_patients(payload: dict = Depends(require_role("secretariat", "medecin")),
                   db: Session = Depends(get_db)):
    patients = db.query(Patient).all()
    if payload["role"] == "secretariat":
        return [_vue_admin(p) for p in patients]
    return [_vue_complete(p) for p in patients]


@app.get("/patient/{patient_id}", response_model=VueComplete)
def dossier_patient(patient_id: int,
                    payload: dict = Depends(require_role("medecin")),
                    db: Session = Depends(get_db)):
    if patient_id < 1:
        raise HTTPException(400, "Identifiant invalide")
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient introuvable")
    return _vue_complete(patient)


@app.get("/health")
def health():
    return {"status": "ok", "service": "APP-01"}


# ---------- Projections RBAC ----------

def _vue_admin(p: Patient) -> VueAdministrative:
    return VueAdministrative(
        patient=p.utilisateur.nom_complet if p.utilisateur else f"patient#{p.id}",
        telephone=p.telephone, mutuelle=p.mutuelle,
        prochain_rdv=str(p.prochain_rdv) if p.prochain_rdv else None,
    )


def _vue_complete(p: Patient) -> VueComplete:
    d = p.dossier
    return VueComplete(
        patient=p.utilisateur.nom_complet if p.utilisateur else f"patient#{p.id}",
        telephone=p.telephone, mutuelle=p.mutuelle,
        prochain_rdv=str(p.prochain_rdv) if p.prochain_rdv else None,
        antecedents=d.antecedents if d else None,
        diagnostics=d.diagnostics if d else None,
        traitements=d.traitements if d else None,
    )
