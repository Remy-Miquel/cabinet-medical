"""
APP-01 — Couche base de données (PostgreSQL)
Cabinet médical — dossier technique section 5.3.4

La base contient les dossiers médicaux. L'accès se fait via un compte de
service dédié (moindre privilège), jamais un compte admin.
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# --- Connexion ---
# Le compte de service (moindre privilège, section 5.3.4) est passé par variable
# d'environnement — jamais en dur dans le code.
DB_USER = os.getenv("DB_USER", "cabinet_service")
DB_PASSWORD = os.getenv("DB_PASSWORD", "changeme")
DB_HOST = os.getenv("DB_HOST", "localhost")   # base locale à APP-01
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "cabinet")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """Comptes : patients, secrétariat, médecins. Le rôle porte le RBAC."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)   # jamais de mot de passe en clair
    role = Column(String(20), nullable=False)             # 'patient' | 'secretariat' | 'medecin'
    full_name = Column(String(120), nullable=False)

    # Un patient est rattaché à son propre dossier
    dossier = relationship("DossierMedical", back_populates="patient", uselist=False)


class DossierMedical(Base):
    """
    Dossier patient. Sépare volontairement :
    - données ADMINISTRATIVES (le secrétariat peut voir)
    - données CLINIQUES (médecin uniquement)
    C'est la traduction du moindre privilège en modèle de données.
    """
    __tablename__ = "dossiers"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # --- Bloc administratif (secrétariat + médecin) ---
    telephone = Column(String(20))
    mutuelle = Column(String(120))
    prochain_rdv = Column(DateTime, nullable=True)

    # --- Bloc clinique (médecin uniquement — art. 9 RGPD) ---
    antecedents = Column(Text)
    diagnostics = Column(Text)
    traitements = Column(Text)

    patient = relationship("User", back_populates="dossier")


def get_db():
    """Fournit une session par requête, fermée proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crée les tables si absentes."""
    Base.metadata.create_all(bind=engine)
