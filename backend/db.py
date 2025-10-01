import sqlite3
import datetime
import re
import os

# Connexion globale à SQLite (chemin configurable)
DB_PATH = os.getenv("SQLITE_PATH", "demandes.db")
print(f"[BOOT] db.py version 2025-10-01 | DB_PATH={DB_PATH}")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

class Database:
    def __init__(self, db_path="demandes.db"):
        self.conn = conn  # Utiliser la connexion globale
        self.c = self.conn.cursor()
        self.create_tables()
        self.add_missing_columns()
        self.add_missing_columns_sous_traitants()

    # --- Création des tables ---
    def create_tables(self):
        self.c.execute("""
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

        self.c.execute("""
        CREATE TABLE IF NOT EXISTS sous_traitants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            email TEXT,
            ville TEXT
        );
        """)

        self.c.execute("""
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

    # --- Vérifier si une colonne existe ---
    def column_exists(self, table_name, column_name):
        self.c.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in self.c.fetchall()]
        return column_name in columns

    # --- Ajouter les colonnes manquantes pour 'demandes' ---
    def add_missing_columns(self):
        for col, col_type in [
            ("date_enregistrement", "TEXT"),
            ("date_voyage", "TEXT"),
            ("pays", "TEXT"),
            ("email", "TEXT"),
            ("villes", "TEXT"),
            ("adresses", "TEXT"),
            ("type_voyage", "TEXT"),
            ("infos_libres", "TEXT"),
            ("corps_mail", "TEXT"),
            ("nb_personnes", "INTEGER")
        ]:
            if not self.column_exists("demandes", col):
                self.c.execute(f"ALTER TABLE demandes ADD COLUMN {col} {col_type}")
        self.conn.commit()

    # --- Ajouter les colonnes manquantes pour 'sous_traitants' ---
    def add_missing_columns_sous_traitants(self):
        # Ensure sous_traitants has the columns used by the API upload endpoint
        columns_to_add = [
            ("nom_entreprise", "TEXT"),
            ("site_internet", "TEXT"),
            ("pays", "TEXT"),
            # 'ville' and 'email' are created in base schema; keep guard anyway
            ("ville", "TEXT"),
            ("email", "TEXT"),
            ("telephone", "TEXT"),
        ]
        for name, ctype in columns_to_add:
            if not self.column_exists("sous_traitants", name):
                try:
                    self.c.execute(f"ALTER TABLE sous_traitants ADD COLUMN {name} {ctype}")
                except Exception:
                    # Ignore if ALTER not applicable in some environments
                    pass



        self.conn.commit()

    # --- Insert demande ---
    def insert_demande(self, data):
        def _to_csv(val):
            if isinstance(val, list):
                return ", ".join([str(x) for x in val])
            if isinstance(val, str):
                return val
            return ""

        def _nb_personnes_to_int(val):
            if val is None:
                return None
            try:
                if isinstance(val, int):
                    return val
                s = str(val).strip()
                if not s:
                    return None
                m = re.search(r"(\d{1,4})", s)
                if m:
                    return int(m.group(1))
            except Exception:
                pass
            return None

        query = """
        INSERT INTO demandes (
            nom, prenom, telephone, ville, date_debut, date_fin,
            type_vehicule, date_enregistrement, date_voyage, pays,
            email, villes, adresses, type_voyage, infos_libres, corps_mail, nb_personnes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.c.execute(query, (
            data.get("nom"),
            data.get("prenom"),
            data.get("telephone"),
            data.get("ville"),
            data.get("date_debut"),
            data.get("date_fin"),
            data.get("type_vehicule"),
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data.get("date_voyage"),
            data.get("pays"),
            data.get("email"),
            _to_csv(data.get("villes", [])),
            _to_csv(data.get("adresses", [])),
            data.get("type_voyage"),
            data.get("infos_libres"),
            data.get("corps_mail"),
            _nb_personnes_to_int(data.get("nb_personnes"))
        ))
        self.conn.commit()

    # --- Copier nom dans nom_entreprise si vide ---
    def sync_sous_traitants_nom(self):
        """Fonction désactivée : la colonne 'nom' n'est pas utilisée dans le schéma actuel."""
        pass

    # --- Fermer la connexion ---
    def close(self):
        self.c.close()
        self.conn.close()
