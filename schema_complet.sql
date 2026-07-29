-- ============================================================
-- Cabinet Médical — Schéma COMPLET (6 tables, Approche 1)
-- À lancer dans la base cabinet_medical :
--   sudo -u postgres psql -d cabinet_medical -f schema_complet.sql
-- Recrée proprement l'ensemble du modèle. Idempotent (IF NOT EXISTS).
-- ============================================================

-- --- roles ---
CREATE TABLE IF NOT EXISTS roles (
    id       SERIAL PRIMARY KEY,
    nom_role VARCHAR(50) NOT NULL UNIQUE
);

-- --- utilisateurs (colonne mot_de_pass_hash conservée telle quelle) ---
CREATE TABLE IF NOT EXISTS utilisateurs (
    id               SERIAL PRIMARY KEY,
    nom              VARCHAR(100) NOT NULL,
    prenom           VARCHAR(100) NOT NULL,
    email            VARCHAR(150) NOT NULL UNIQUE,
    mot_de_pass_hash VARCHAR(255) NOT NULL,
    role_id          INTEGER REFERENCES roles(id),
    date_creation    TIMESTAMP DEFAULT NOW(),
    actif            BOOLEAN DEFAULT TRUE
);

-- --- medecins ---
CREATE TABLE IF NOT EXISTS medecins (
    id             SERIAL PRIMARY KEY,
    utilisateur_id INTEGER UNIQUE REFERENCES utilisateurs(id),
    specialite     VARCHAR(100),
    numero_rpps    VARCHAR(20) UNIQUE
);

-- --- secretaires ---
CREATE TABLE IF NOT EXISTS secretaires (
    id             SERIAL PRIMARY KEY,
    utilisateur_id INTEGER UNIQUE REFERENCES utilisateurs(id),
    poste          VARCHAR(100)
);

-- --- patients (données administratives) ---
CREATE TABLE IF NOT EXISTS patients (
    id             SERIAL PRIMARY KEY,
    utilisateur_id INTEGER UNIQUE REFERENCES utilisateurs(id),
    telephone      VARCHAR(20),
    mutuelle       VARCHAR(120),
    prochain_rdv   TIMESTAMP
);

-- --- dossiers (données CLINIQUES — médecin uniquement) ---
CREATE TABLE IF NOT EXISTS dossiers (
    id          SERIAL PRIMARY KEY,
    patient_id  INTEGER UNIQUE REFERENCES patients(id),
    antecedents TEXT,
    diagnostics TEXT,
    traitements TEXT
);

-- --- Rôles de référence ---
INSERT INTO roles (nom_role) VALUES ('medecin')     ON CONFLICT (nom_role) DO NOTHING;
INSERT INTO roles (nom_role) VALUES ('secretariat') ON CONFLICT (nom_role) DO NOTHING;
INSERT INTO roles (nom_role) VALUES ('patient')     ON CONFLICT (nom_role) DO NOTHING;

-- --- Droits du compte applicatif (moindre privilège : DML, pas DDL) ---
GRANT CONNECT ON DATABASE cabinet_medical TO cabinet_user;
GRANT USAGE ON SCHEMA public TO cabinet_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cabinet_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cabinet_user;
-- S'applique aussi aux futures tables/séquences
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cabinet_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO cabinet_user;

\dt
