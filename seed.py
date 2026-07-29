"""
APP-01 — Peuplement de démonstration (schéma Approche 1)
À lancer une fois : python3 seed.py
Crée 3 comptes (médecin, secrétaire, patient) + 1 dossier.
"""
from datetime import datetime
from database import (
    SessionLocal, init_db,
    Role, Utilisateur, Medecin, Secretaire, Patient, Dossier,
)
from auth import hash_password

init_db()
db = SessionLocal()

# Rôles (idempotent)
roles = {}
for nom in ["medecin", "secretariat", "patient"]:
    r = db.query(Role).filter(Role.nom_role == nom).first()
    if not r:
        r = Role(nom_role=nom)
        db.add(r); db.commit(); db.refresh(r)
    roles[nom] = r

if db.query(Utilisateur).first():
    print("Utilisateurs déjà présents, seed ignoré.")
    db.close(); raise SystemExit

# --- Médecin ---
u_med = Utilisateur(nom="Martin", prenom="Paul", email="dr.martin@cabinet.fr",
                    mot_de_pass_hash=hash_password("medecin123"), role_id=roles["medecin"].id)
db.add(u_med); db.commit(); db.refresh(u_med)
db.add(Medecin(utilisateur_id=u_med.id, specialite="Généraliste", numero_rpps="10101010101"))

# --- Secrétaire ---
u_sec = Utilisateur(nom="Durand", prenom="Sophie", email="secretaire@cabinet.fr",
                    mot_de_pass_hash=hash_password("secret123"), role_id=roles["secretariat"].id)
db.add(u_sec); db.commit(); db.refresh(u_sec)
db.add(Secretaire(utilisateur_id=u_sec.id, poste="Accueil"))

# --- Patient + dossier ---
u_pat = Utilisateur(nom="Durand", prenom="Jean", email="jean.durand@mail.fr",
                    mot_de_pass_hash=hash_password("patient123"), role_id=roles["patient"].id)
db.add(u_pat); db.commit(); db.refresh(u_pat)
pat = Patient(utilisateur_id=u_pat.id, telephone="0612345678",
              mutuelle="MGEN", prochain_rdv=datetime(2026, 8, 15, 10, 30))
db.add(pat); db.commit(); db.refresh(pat)
db.add(Dossier(patient_id=pat.id, antecedents="Hypertension légère depuis 2022.",
               diagnostics="Contrôle tensionnel de routine.", traitements="Amlodipine 5mg, 1/jour."))
db.commit(); db.close()

print("Base peuplée :")
print("  médecin      -> dr.martin@cabinet.fr / medecin123")
print("  secrétariat  -> secretaire@cabinet.fr / secret123")
print("  patient      -> jean.durand@mail.fr / patient123")
