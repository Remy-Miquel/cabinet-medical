-- ============================================================
-- Cabinet Médical — Complément de schéma (Approche 1, table par rôle)
-- À exécuter par la collègue sur DATA-01, base cabinet_medical
-- Complète les tables existantes : roles, utilisateurs, medecins
-- ============================================================
-- Connexion :  sudo -u postgres psql -d cabinet_medical

-- --- Table secretaires (parallèle à medecins) ---
CREATE TABLE IF NOT EXISTS secretaires (
    id             SERIAL PRIMARY KEY,
    utilisateur_id INTEGER UNIQUE REFERENCES utilisateurs(id),
    poste          VARCHAR(100)          -- ex: accueil, facturation
);

-- --- Table patients (données administratives du patient) ---
CREATE TABLE IF NOT EXISTS patients (
    id             SERIAL PRIMARY KEY,
    utilisateur_id INTEGER UNIQUE REFERENCES utilisateurs(id),
    telephone      VARCHAR(20),
    mutuelle       VARCHAR(120),
    prochain_rdv   TIMESTAMP
);

-- --- Table dossiers (données CLINIQUES — médecin uniquement) ---
-- Séparée de patients pour appliquer le moindre privilège :
-- le secrétariat lit patients (admin) mais JAMAIS dossiers (clinique).
CREATE TABLE IF NOT EXISTS dossiers (
    id           SERIAL PRIMARY KEY,
    patient_id   INTEGER UNIQUE REFERENCES patients(id),
    antecedents  TEXT,
    diagnostics  TEXT,
    traitements  TEXT
);

-- --- Rôles de référence (si pas déjà tous présents) ---
INSERT INTO roles (nom_role) VALUES ('medecin')     ON CONFLICT (nom_role) DO NOTHING;
INSERT INTO roles (nom_role) VALUES ('secretariat') ON CONFLICT (nom_role) DO NOTHING;
INSERT INTO roles (nom_role) VALUES ('patient')     ON CONFLICT (nom_role) DO NOTHING;

-- --- Droits pour le compte applicatif ---
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cabinet_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cabinet_user;

-- Vérification
\dt
