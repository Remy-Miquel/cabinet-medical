"""
APP-01 — Peuplement initial de la base (comptes de démonstration)
À exécuter une fois après la création de la base : python3 seed.py

En production ces comptes seraient créés via une procédure d'enrôlement
sécurisée, pas par un script. Ici c'est pour tester le RBAC.
"""
from datetime import datetime
from database import SessionLocal, init_db, User, DossierMedical
from auth import hash_password

init_db()
db = SessionLocal()

# Évite les doublons si on relance le script
if db.query(User).first():
    print("Base déjà peuplée, rien à faire.")
    db.close()
    raise SystemExit

# --- Comptes ---
medecin = User(username="dr_martin", password_hash=hash_password("medecin123"),
               role="medecin", full_name="Dr Martin")
secretaire = User(username="secretaire", password_hash=hash_password("secret123"),
                  role="secretariat", full_name="Secrétariat")
patient = User(username="patient_durand", password_hash=hash_password("patient123"),
               role="patient", full_name="Jean Durand")

db.add_all([medecin, secretaire, patient])
db.commit()
db.refresh(patient)

# --- Dossier du patient (admin + clinique séparés) ---
dossier = DossierMedical(
    patient_id=patient.id,
    telephone="06 12 34 56 78",
    mutuelle="MGEN",
    prochain_rdv=datetime(2026, 8, 15, 10, 30),
    antecedents="Hypertension légère depuis 2022.",
    diagnostics="Contrôle tensionnel de routine.",
    traitements="Amlodipine 5mg, 1/jour.",
)
db.add(dossier)
db.commit()
db.close()

print("Base peuplée :")
print("  médecin      -> dr_martin / medecin123   (accès complet)")
print("  secrétariat  -> secretaire / secret123   (administratif seulement)")
print("  patient      -> patient_durand / patient123 (son dossier)")
