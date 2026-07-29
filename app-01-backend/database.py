"""
APP-01 — Couche base de données (PostgreSQL)
Cabinet médical — schéma Approche 1 (table par rôle)

Mappe le schéma défini côté DATA-01 :
  roles, utilisateurs, medecins, secretaires, patients, dossiers
Base : cabinet_medical | Utilisateur applicatif : cabinet_user
"""
import os
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean,
    ForeignKey, DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# --- Connexion (compte de service, moindre privilège) ---
DB_USER = os.getenv("DB_USER", "cabinet_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "changeme")
DB_HOST = os.getenv("DB_HOST", "172.16.20.2")   # DATA-01
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "cabinet_medical")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    nom_role = Column(String(50), unique=True, nullable=False)


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    # NB : colonne volontairement 'mot_de_pass_hash' pour coller à la base existante
    mot_de_pass_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"))
    date_creation = Column(DateTime, default=datetime.utcnow)
    actif = Column(Boolean, default=True)

    role = relationship("Role")
    medecin = relationship("Medecin", back_populates="utilisateur", uselist=False)
    secretaire = relationship("Secretaire", back_populates="utilisateur", uselist=False)
    patient = relationship("Patient", back_populates="utilisateur", uselist=False)

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    @property
    def role_nom(self):
        return self.role.nom_role if self.role else None


class Medecin(Base):
    __tablename__ = "medecins"
    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), unique=True)
    specialite = Column(String(100))
    numero_rpps = Column(String(20), unique=True)

    utilisateur = relationship("Utilisateur", back_populates="medecin")


class Secretaire(Base):
    __tablename__ = "secretaires"
    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), unique=True)
    poste = Column(String(100))

    utilisateur = relationship("Utilisateur", back_populates="secretaire")


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), unique=True)
    telephone = Column(String(20))
    mutuelle = Column(String(120))
    prochain_rdv = Column(DateTime, nullable=True)

    utilisateur = relationship("Utilisateur", back_populates="patient")
    dossier = relationship("Dossier", back_populates="patient", uselist=False)


class Dossier(Base):
    """Données CLINIQUES — accès médecin uniquement (art. 9 RGPD)."""
    __tablename__ = "dossiers"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), unique=True)
    antecedents = Column(Text)
    diagnostics = Column(Text)
    traitements = Column(Text)

    patient = relationship("Patient", back_populates="dossier")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crée les tables si absentes (idempotent)."""
    Base.metadata.create_all(bind=engine)
