"""
APP-01 — Script de peuplement de la base cabinet_medical
- Renforce les mots de passe des comptes existants (aléatoires forts)
- Crée 3 médecins, 4 secrétaires, 70 patients avec dossiers cliniques
- Affiche TOUS les identifiants générés UNE SEULE FOIS à la fin

Usage (sur APP-01, venv actif, variables DB_* exportées) :
    python3 peupler.py
"""
import os
import sys
import random
import secrets
import string
from datetime import datetime, timedelta

from database import (
    SessionLocal, init_db,
    Role, Utilisateur, Medecin, Secretaire, Patient, Dossier,
)
from auth import hash_password

# ---------- Génération de mots de passe forts ----------
_ALPHABET = string.ascii_letters + string.digits + "!@#%*-_?"

def mot_de_passe_fort(longueur=16) -> str:
    """Génère un mot de passe aléatoire fort (secrets = cryptographiquement sûr)."""
    while True:
        pw = "".join(secrets.choice(_ALPHABET) for _ in range(longueur))
        # garantit au moins 1 minuscule, 1 majuscule, 1 chiffre, 1 spécial
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw) and any(c in "!@#%*-_?" for c in pw)):
            return pw

# ---------- Données réalistes ----------
PRENOMS_M = ["Lucas","Hugo","Léo","Louis","Raphaël","Arthur","Jules","Adam","Nathan","Gabriel",
             "Ethan","Paul","Tom","Noah","Aaron","Marius","Victor","Antoine","Baptiste","Clément"]
PRENOMS_F = ["Emma","Jade","Louise","Alice","Chloé","Lina","Léa","Rose","Anna","Mila",
             "Julia","Inès","Zoé","Camille","Sarah","Manon","Eva","Nina","Juliette","Clara"]
NOMS = ["Martin","Bernard","Dubois","Thomas","Robert","Richard","Petit","Durand","Leroy","Moreau",
        "Simon","Laurent","Lefebvre","Michel","Garcia","David","Bertrand","Roux","Vincent","Fournier",
        "Morel","Girard","André","Lefevre","Mercier","Dupont","Lambert","Bonnet","François","Martinez",
        "Legrand","Garnier","Faure","Rousseau","Blanc","Guerin","Muller","Henry","Roussel","Nicolas"]
MUTUELLES = ["MGEN","Harmonie Mutuelle","MAAF Santé","AXA Santé","Malakoff Humanis",
             "Groupama","Matmut","MACIF","Aucune","MNH"]
SPECIALITES = ["Médecine générale","Cardiologie","Pédiatrie","Dermatologie","Gériatrie"]
POSTES_SECR = ["Accueil","Gestion des rendez-vous","Facturation","Secrétariat médical"]

ANTECEDENTS = ["Aucun antécédent notable","Hypertension artérielle","Diabète de type 2",
               "Asthme","Allergie à la pénicilline","Cholestérol élevé","Antécédent de fracture",
               "Migraines chroniques","Reflux gastro-œsophagien","Aucun"]
DIAGNOSTICS = ["Contrôle de routine — RAS","Rhinopharyngite","Suivi tension artérielle",
               "Lombalgie","Otite moyenne","Bilan sanguin annuel","Syndrome grippal",
               "Suivi diabète","Eczéma","Renouvellement d'ordonnance"]
TRAITEMENTS = ["Aucun","Paracétamol 1g si douleur","Amoxicilline 7 jours","Repos + anti-inflammatoire",
               "Antihypertenseur quotidien","Metformine","Sirop antitussif","Crème corticoïde",
               "Suivi diététique","Renouvellement traitement de fond"]

def tel():
    return "0" + random.choice("67") + "".join(random.choice("0123456789") for _ in range(8))

def rdv_futur():
    return datetime.utcnow() + timedelta(days=random.randint(1, 90),
                                         hours=random.randint(8, 17))

# ---------- Peuplement ----------
def main():
    init_db()
    db = SessionLocal()
    identifiants = []   # (role, nom complet, email, mot de passe en clair) — affiché 1x

    # Rôles (récupère ou crée)
    roles = {}
    for nom in ["medecin", "secretariat", "patient"]:
        r = db.query(Role).filter(Role.nom_role == nom).first()
        if not r:
            r = Role(nom_role=nom); db.add(r); db.commit(); db.refresh(r)
        roles[nom] = r

    # 1) Renforcer les mots de passe des comptes EXISTANTS
    print("Renforcement des comptes existants...")
    for u in db.query(Utilisateur).all():
        pw = mot_de_passe_fort()
        u.mot_de_pass_hash = hash_password(pw)
        role_nom = next((n for n, r in roles.items() if r.id == u.role_id), "?")
        identifiants.append((role_nom, f"{u.prenom} {u.nom}", u.email, pw))
    db.commit()

    emails_utilises = {u.email for u in db.query(Utilisateur).all()}

    def cree_utilisateur(prenom, nom, role_nom, domaine="cabinet.fr"):
        base = f"{prenom.lower()}.{nom.lower()}".replace(" ", "")
        email = f"{base}@{domaine}"
        n = 1
        while email in emails_utilises:
            email = f"{base}{n}@{domaine}"; n += 1
        emails_utilises.add(email)
        pw = mot_de_passe_fort()
        u = Utilisateur(nom=nom, prenom=prenom, email=email,
                        mot_de_pass_hash=hash_password(pw), role_id=roles[role_nom].id)
        db.add(u); db.commit(); db.refresh(u)
        identifiants.append((role_nom, f"{prenom} {nom}", email, pw))
        return u

    # 2) 3 médecins
    print("Création des médecins...")
    for i in range(3):
        prenom = random.choice(PRENOMS_M + PRENOMS_F); nom = random.choice(NOMS)
        u = cree_utilisateur(prenom, nom, "medecin")
        db.add(Medecin(utilisateur_id=u.id, specialite=random.choice(SPECIALITES),
                       numero_rpps="".join(random.choice("0123456789") for _ in range(11))))
    db.commit()

    # 3) 4 secrétaires
    print("Création des secrétaires...")
    for i in range(4):
        prenom = random.choice(PRENOMS_F + PRENOMS_M); nom = random.choice(NOMS)
        u = cree_utilisateur(prenom, nom, "secretariat")
        db.add(Secretaire(utilisateur_id=u.id, poste=random.choice(POSTES_SECR)))
    db.commit()

    # 4) 70 patients + dossiers
    print("Création des 70 patients et dossiers...")
    for i in range(70):
        est_f = random.random() < 0.5
        prenom = random.choice(PRENOMS_F if est_f else PRENOMS_M)
        nom = random.choice(NOMS)
        u = cree_utilisateur(prenom, nom, "patient", domaine="mail.fr")
        p = Patient(utilisateur_id=u.id, telephone=tel(),
                    mutuelle=random.choice(MUTUELLES),
                    prochain_rdv=rdv_futur() if random.random() < 0.6 else None)
        db.add(p); db.commit(); db.refresh(p)
        db.add(Dossier(patient_id=p.id,
                       antecedents=random.choice(ANTECEDENTS),
                       diagnostics=random.choice(DIAGNOSTICS),
                       traitements=random.choice(TRAITEMENTS)))
    db.commit()
    db.close()

    # ---------- Affichage des identifiants (UNE SEULE FOIS) ----------
    print("\n" + "=" * 70)
    print("IDENTIFIANTS GÉNÉRÉS — À NOTER MAINTENANT (non ré-affichés)")
    print("=" * 70)
    for role_nom in ["medecin", "secretariat", "patient"]:
        lignes = [x for x in identifiants if x[0] == role_nom]
        print(f"\n--- {role_nom.upper()} ({len(lignes)}) ---")
        for _, nom_complet, email, pw in lignes:
            print(f"  {nom_complet:<28} {email:<40} {pw}")
    print("\n" + "=" * 70)
    print(f"TOTAL : {len(identifiants)} comptes")
    print("=" * 70)

if __name__ == "__main__":
    main()
