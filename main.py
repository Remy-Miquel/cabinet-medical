"""
APP-01 — API back-end du cabinet médical (FastAPI)
Schéma Approche 1 (table par rôle). API interne, appelée uniquement par WEB-01.
Porte le RBAC : chaque endpoint vérifie le rôle avant de répondre.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import (
    get_db, init_db,
    Utilisateur, Role, Medecin, Secretaire, Patient, Dossier,
)
from auth import (
    hash_password, verify_password, create_access_token,
    decode_token, require_role,
)

app = FastAPI(title="Cabinet Médical — API interne (APP-01)")


@app.on_event("startup")
def startup():
    init_db()


# ---------- Schémas de réponse (vues différenciées par rôle) ----------

class VueAdministrative(BaseModel):
    """Vue secrétariat : PAS de contenu clinique."""
    patient: str
    telephone: Optional[str]
    mutuelle: Optional[str]
    prochain_rdv: Optional[str]


class VueComplete(VueAdministrative):
    """Vue médecin/patient : administratif + clinique."""
    antecedents: Optional[str]
    diagnostics: Optional[str]
    traitements: Optional[str]


class LoginBody(BaseModel):
    email: str
    password: str


class LoginResult(BaseModel):
    access_token: str
    token_type: str
    role: str


# ---------- Authentification ----------

@app.post("/token", response_model=LoginResult)
def login(body: LoginBody, db: Session = Depends(get_db)):
    """Login par email. Renvoie un JWT portant le rôle."""
    user = db.query(Utilisateur).filter(Utilisateur.email == body.email).first()
    if not user or not user.actif or not verify_password(body.password, user.mot_de_pass_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
        )
    role = user.role_nom
    token = create_access_token(user.email, role, user.id)
    return LoginResult(access_token=token, token_type="bearer", role=role)


# ---------- Endpoints métier avec RBAC ----------

@app.get("/mon-dossier", response_model=VueComplete)
def mon_dossier(payload: dict = Depends(require_role("patient")),
                db: Session = Depends(get_db)):
    """PATIENT : uniquement son propre dossier."""
    patient = db.query(Patient).filter(Patient.utilisateur_id == payload["uid"]).first()
    if not patient:
        raise HTTPException(404, "Profil patient introuvable")
    return _vue_complete(patient)


@app.get("/patients")
def liste_patients(payload: dict = Depends(require_role("secretariat", "medecin")),
                   db: Session = Depends(get_db)):
    """SECRÉTARIAT + MÉDECIN : liste, mais vue selon le rôle."""
    patients = db.query(Patient).all()
    if payload["role"] == "secretariat":
        return [_vue_admin(p) for p in patients]      # admin seulement
    return [_vue_complete(p) for p in patients]       # médecin : complet


@app.get("/patient/{patient_id}", response_model=VueComplete)
def dossier_patient(patient_id: int,
                    payload: dict = Depends(require_role("medecin")),
                    db: Session = Depends(get_db)):
    """MÉDECIN UNIQUEMENT : dossier clinique complet d'un patient."""
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
        telephone=p.telephone,
        mutuelle=p.mutuelle,
        prochain_rdv=str(p.prochain_rdv) if p.prochain_rdv else None,
    )


def _vue_complete(p: Patient) -> VueComplete:
    d = p.dossier
    return VueComplete(
        patient=p.utilisateur.nom_complet if p.utilisateur else f"patient#{p.id}",
        telephone=p.telephone,
        mutuelle=p.mutuelle,
        prochain_rdv=str(p.prochain_rdv) if p.prochain_rdv else None,
        antecedents=d.antecedents if d else None,
        diagnostics=d.diagnostics if d else None,
        traitements=d.traitements if d else None,
    )
