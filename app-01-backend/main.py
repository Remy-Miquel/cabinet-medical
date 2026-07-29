"""
APP-01 — API back-end du cabinet médical (FastAPI)
Cabinet médical — dossier technique sections 5.3.3 / 5.3.4

Cette API est INTERNE : elle n'est jamais exposée directement aux patients.
Seul WEB-01 (front en DMZ) l'appelle, sur un port filtré par pfSense.
Elle porte le RBAC : chaque endpoint vérifie le rôle avant de répondre.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db, init_db, User, DossierMedical
from auth import (
    hash_password, verify_password, create_access_token,
    decode_token, require_role,
)

app = FastAPI(title="Cabinet Médical — API interne (APP-01)")


@app.on_event("startup")
def startup():
    init_db()


# ---------- Schémas de réponse (Pydantic) ----------
# On expose des vues DIFFÉRENTES selon le rôle : c'est la minimisation
# des données (art. 5 RGPD) appliquée au niveau de l'API.

class DossierAdministratif(BaseModel):
    """Vue secrétariat : PAS de contenu clinique."""
    patient: str
    telephone: Optional[str]
    mutuelle: Optional[str]
    prochain_rdv: Optional[str]


class DossierComplet(DossierAdministratif):
    """Vue médecin : administratif + clinique (art. 9 RGPD)."""
    antecedents: Optional[str]
    diagnostics: Optional[str]
    traitements: Optional[str]


class LoginResult(BaseModel):
    access_token: str
    token_type: str
    role: str


# ---------- Authentification ----------

class LoginBody(BaseModel):
    username: str
    password: str


@app.post("/token", response_model=LoginResult)
def login(body: LoginBody, db: Session = Depends(get_db)):
    """Login : renvoie un JWT portant le rôle. Point d'entrée de tout accès."""
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
        )
    token = create_access_token(user.username, user.role, user.id)
    return LoginResult(access_token=token, token_type="bearer", role=user.role)


# ---------- Endpoints métier avec RBAC ----------

@app.get("/mon-dossier", response_model=DossierComplet)
def mon_dossier(payload: dict = Depends(require_role("patient")),
                db: Session = Depends(get_db)):
    """
    PATIENT : voit UNIQUEMENT son propre dossier, complet.
    Le uid vient du token — impossible de demander le dossier d'un autre.
    """
    dossier = db.query(DossierMedical).filter(
        DossierMedical.patient_id == payload["uid"]
    ).first()
    if not dossier:
        raise HTTPException(404, "Aucun dossier trouvé")
    return _to_complet(dossier)


@app.get("/patients")
def liste_patients(payload: dict = Depends(require_role("secretariat", "medecin")),
                   db: Session = Depends(get_db)):
    """
    SECRÉTARIAT + MÉDECIN : liste des patients.
    Mais la VUE diffère selon le rôle (voir ci-dessous).
    """
    dossiers = db.query(DossierMedical).all()
    if payload["role"] == "secretariat":
        # Secrétariat : administratif seulement (moindre privilège)
        return [_to_admin(d) for d in dossiers]
    # Médecin : accès complet
    return [_to_complet(d) for d in dossiers]


@app.get("/patient/{patient_id}", response_model=DossierComplet)
def dossier_patient(patient_id: int,
                    payload: dict = Depends(require_role("medecin")),
                    db: Session = Depends(get_db)):
    """
    MÉDECIN UNIQUEMENT : dossier clinique complet d'un patient donné.
    Le secrétariat ne peut PAS atteindre cet endpoint (403).
    """
    dossier = db.query(DossierMedical).filter(
        DossierMedical.patient_id == patient_id
    ).first()
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")
    return _to_complet(dossier)


@app.get("/health")
def health():
    """Sonde de disponibilité (utilisée par WEB-01 et la supervision)."""
    return {"status": "ok", "service": "APP-01"}


# ---------- Helpers de projection (RBAC → vue) ----------

def _to_admin(d: DossierMedical) -> DossierAdministratif:
    return DossierAdministratif(
        patient=d.patient.full_name,
        telephone=d.telephone,
        mutuelle=d.mutuelle,
        prochain_rdv=str(d.prochain_rdv) if d.prochain_rdv else None,
    )


def _to_complet(d: DossierMedical) -> DossierComplet:
    return DossierComplet(
        patient=d.patient.full_name,
        telephone=d.telephone,
        mutuelle=d.mutuelle,
        prochain_rdv=str(d.prochain_rdv) if d.prochain_rdv else None,
        antecedents=d.antecedents,
        diagnostics=d.diagnostics,
        traitements=d.traitements,
    )
