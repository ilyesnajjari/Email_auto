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
    sous_traitant TEXT
);
""")

# Table des sous-traitants
c.execute("""
CREATE TABLE IF NOT EXISTS sous_traitants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT,
    email TEXT,
    ville TEXT
);
""")

conn.commit()
c.close()
