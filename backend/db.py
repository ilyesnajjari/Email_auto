import sqlite3

conn = sqlite3.connect("demandes.db", check_same_thread=False)
c = conn.cursor()

# Table des demandes
c.execute("""
CREATE TABLE IF NOT EXISTS demandes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT,
    prenom TEXT,
    telephone TEXT,
    ville TEXT,
    date_debut TEXT,
    date_fin TEXT,
    type_vehicule TEXT,
    statut TEXT DEFAULT 'en_attente',
    sous_traitant TEXT,
    pays TEXT,
    date_enregistrement TEXT DEFAULT (datetime('now')),
    date_voyage TEXT
);
""")

# Table des sous-traitants
c.execute("""
CREATE TABLE IF NOT EXISTS sous_traitants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_entreprise TEXT,
    site_internet TEXT,
    pays TEXT,
    ville TEXT,
    email TEXT,
    telephone TEXT
);
""")

# Table de l'historique
c.execute("""
CREATE TABLE IF NOT EXISTS historique (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demande_id INTEGER,
    nom TEXT,
    prenom TEXT,
    telephone TEXT,
    ville TEXT,
    date_debut TEXT,
    date_fin TEXT,
    type_vehicule TEXT,
    statut TEXT,
    sous_traitant TEXT,
    action TEXT,
    date_action TEXT
);
""")

# Migration pour ajouter les nouveaux champs aux sous-traitants existants
try:
    c.execute("ALTER TABLE sous_traitants ADD COLUMN nom_entreprise TEXT")
except sqlite3.OperationalError:
    pass  # La colonne existe déjà

try:
    c.execute("ALTER TABLE sous_traitants ADD COLUMN site_internet TEXT")
except sqlite3.OperationalError:
    pass

try:
    c.execute("ALTER TABLE sous_traitants ADD COLUMN pays TEXT")
except sqlite3.OperationalError:
    pass

try:
    c.execute("ALTER TABLE sous_traitants ADD COLUMN telephone TEXT")
except sqlite3.OperationalError:
    pass

# Si nom_entreprise est NULL, utiliser la valeur de nom comme fallback
c.execute("UPDATE sous_traitants SET nom_entreprise = nom WHERE nom_entreprise IS NULL AND nom IS NOT NULL")

# Migration pour ajouter les nouveaux champs aux demandes existantes
try:
    c.execute("ALTER TABLE demandes ADD COLUMN pays TEXT")
except sqlite3.OperationalError:
    pass  # La colonne existe déjà

try:
    c.execute("ALTER TABLE demandes ADD COLUMN date_enregistrement TEXT DEFAULT (datetime('now'))")
except sqlite3.OperationalError:
    pass

try:
    c.execute("ALTER TABLE demandes ADD COLUMN date_voyage TEXT")
except sqlite3.OperationalError:
    pass

# Mettre à jour les enregistrements existants sans date_enregistrement
c.execute("UPDATE demandes SET date_enregistrement = datetime('now') WHERE date_enregistrement IS NULL")
c.execute("UPDATE demandes SET date_voyage = date_debut WHERE date_voyage IS NULL")

conn.commit()
c.close()
