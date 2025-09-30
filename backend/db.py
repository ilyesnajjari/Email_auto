import sqlite3
import datetime

# Connexion globale
conn = sqlite3.connect("demandes.db", check_same_thread=False)
c = conn.cursor()

class Database:
    def __init__(self, db_path="demandes.db"):
        self.conn = conn  # Utiliser la connexion globale
        self.c = self.conn.cursor()
        self.create_tables()
        self.add_missing_columns()

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

    def column_exists(self, table_name, column_name):
        self.c.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in self.c.fetchall()]
        return column_name in columns

    def add_missing_columns(self):
        # Colonnes supplémentaires pour 'demandes'
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
                # Already an int-like value
                if isinstance(val, int):
                    return val
                s = str(val).strip()
                if not s:
                    return None
                # Pure digits
                if s.isdigit():
                    return int(s)
                # Extract first integer from ranges like "10-20", "10 à 20", "10 to 20", or labels like "12 pax"
                import re
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

    def close(self):
        self.c.close()
        self.conn.close()
