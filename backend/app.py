from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from db import conn
import email_fetcher
from mailer import send_email_partners_bcc, format_partner_email, send_custom_body_bcc, subject_for_lang
from ai_email import compose_partner_email
from threading import Thread
import csv
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, date
import secrets
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

# Load environment variables from backend/.env if present (won't override real env)
try:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
except Exception:
    pass

# Runtime fetch status
LAST_FETCH = {"mode": None, "inserted": 0, "at": None}

# --- Admin authentication (optional) ---
# Configure via environment:
# - ADMIN_PASSWORD: the password required for login (default: "admin admin")
# - REQUIRE_ADMIN: when 'true', all API routes require a valid admin token, except /auth/login and /health
# - ADMIN_BOOT_PASSWORD: if set, the app will only start when it matches ADMIN_PASSWORD (startup guard)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or "admin admin"
REQUIRE_ADMIN = (os.getenv("REQUIRE_ADMIN", "false").lower() in ("1", "true", "yes", "y"))
_VALID_TOKENS = set()

def _read_admin_from_credentials_file():
    cfg = {}
    try:
        cred_path = os.path.join(os.path.dirname(__file__), 'credentials.txt')
        if os.path.exists(cred_path):
            with open(cred_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if k in ('ADMIN_PASSWORD', 'REQUIRE_ADMIN'):
                            cfg[k] = v
    except Exception:
        pass
    return cfg

adm_cfg = _read_admin_from_credentials_file()
if adm_cfg:
    if not os.getenv('ADMIN_PASSWORD') and adm_cfg.get('ADMIN_PASSWORD'):
        ADMIN_PASSWORD = adm_cfg['ADMIN_PASSWORD']
    if os.getenv('REQUIRE_ADMIN') is None and 'REQUIRE_ADMIN' in adm_cfg:
        REQUIRE_ADMIN = (str(adm_cfg['REQUIRE_ADMIN']).lower() in ("1", "true", "yes", "y"))

# Startup guard: if ADMIN_BOOT_PASSWORD is defined but wrong, exit
BOOT_PW = os.getenv('ADMIN_BOOT_PASSWORD')
if BOOT_PW is not None and BOOT_PW != ADMIN_PASSWORD:
    print("[ERROR] ADMIN_BOOT_PASSWORD incorrect. Application will not start.")
    raise SystemExit(1)

@app.route('/auth/login', methods=['POST'])
def auth_login():
    try:
        data = request.get_json(silent=True) or {}
        pw = data.get('password') or ''
        if pw == ADMIN_PASSWORD:
            token = secrets.token_urlsafe(32)
            _VALID_TOKENS.add(token)
            return jsonify({"token": token, "require_admin": REQUIRE_ADMIN})
        return jsonify({"error": "Mot de passe invalide"}), 401
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "require_admin": REQUIRE_ADMIN})

@app.before_request
def _enforce_admin():
    if not REQUIRE_ADMIN:
        return  # auth disabled
    path = request.path or ''
    if request.method == 'OPTIONS':
        return
    # allowlist of public endpoints
    if path.startswith('/auth/login') or path.startswith('/health'):
        return
    # Check for token in Authorization: Bearer <token> or X-Admin-Token header
    authz = request.headers.get('Authorization', '')
    token = None
    if authz.lower().startswith('bearer '):
        token = authz.split(' ', 1)[1].strip()
    if not token:
        token = request.headers.get('X-Admin-Token', '').strip()
    if token in _VALID_TOKENS:
        return
    return jsonify({"error": "Unauthorized: admin token required"}), 401

# Configuration pour l'upload de fichiers
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# Créer le dossier d'upload s'il n'existe pas
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_days_remaining(date_voyage):
    """Calcule le nombre de jours entre aujourd'hui et la date de voyage"""
    if not date_voyage:
        return None
    try:
        voyage_date = datetime.strptime(date_voyage, '%Y-%m-%d')
        today = datetime.now()
        diff = (voyage_date - today).days
        return diff
    except:
        return None

def format_demande_with_calculations(demande_dict):
    """Ajoute les calculs aux données de demande"""
    # Calculer les jours restants
    jours_restants = calculate_days_remaining(demande_dict.get('date_voyage'))
    demande_dict['jours_restants'] = jours_restants
    
    # Formater les dates
    if demande_dict.get('date_enregistrement'):
        try:
            date_enr = datetime.strptime(demande_dict['date_enregistrement'], '%Y-%m-%d %H:%M:%S')
            demande_dict['date_enr_formatted'] = date_enr.strftime('%d/%m/%Y')
        except:
            demande_dict['date_enr_formatted'] = demande_dict.get('date_enregistrement', '')
    
    # Date du jour
    demande_dict['date_du_jour'] = datetime.now().strftime('%d/%m/%Y')
    
    return demande_dict

# --- Ajout d'une demande (POST) ---
from db import Database
db = Database()

@app.route("/demandes", methods=["POST"])
def add_demande():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Aucune donnée reçue"}), 400
        db.insert_demande(data)
        return jsonify({"message": "Demande ajoutée avec succès"}), 201
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- Helper pour envoyer email asynchrone ---
def send_email_async(ville, subject, gruppe, strecke, entfernung, fahrten, stunden_pro_tag, conn):
    Thread(target=send_email_partners_bcc, args=(ville, subject, gruppe, strecke, entfernung, fahrten, stunden_pro_tag, conn)).start()
# --- Routes ---
@app.route("/demandes", methods=["GET"])
def get_demandes():
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM demandes ORDER BY date_enregistrement DESC")
        rows = c.fetchall()
        demandes = [dict(zip([column[0] for column in c.description], row)) for row in rows]

        # Ajouter les calculs pour chaque demande
        demandes_formatted = []
        for demande in demandes:
            d = format_demande_with_calculations(demande)
            # Ajout des nouveaux champs pour dashboard
            d['email'] = demande.get('email', '')
            d['villes'] = demande.get('villes', '')
            d['adresses'] = demande.get('adresses', '')
            d['type_voyage'] = demande.get('type_voyage', '')
            d['nb_personnes'] = demande.get('nb_personnes', '')  # Ajout du nombre de personnes
            d['corps_mail'] = demande.get('corps_mail', '')  # Ajout du corps du mail

            # Compter les sous-traitants dans la même ville
            c.execute("SELECT COUNT(*) FROM sous_traitants WHERE ville=?", (demande['ville'],))
            d['nb_sous_traitants'] = c.fetchone()[0]

            demandes_formatted.append(d)

        c.close()
        return jsonify(demandes_formatted)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/demandes/valider/<int:id>", methods=["POST"])
def valider_demande(id):
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM demandes WHERE id=?", (id,))
        demande = c.fetchone()
        if not demande:
            c.close()
            return jsonify({"error": "Demande non trouvée"}), 404

        # Vérifier le nombre de sous-traitants dans la même ville
        ville = demande[4]
        c.execute("SELECT COUNT(*) FROM sous_traitants WHERE ville=?", (ville,))
        nb_sous_traitants = c.fetchone()[0]
        if nb_sous_traitants == 0:
            c.close()
            return jsonify({"error": "Aucun sous-traitant disponible dans cette ville"}), 400

        c.execute("UPDATE demandes SET statut='validee' WHERE id=?", (id,))

        # Ajouter à l'historique
        c.execute("""INSERT INTO historique 
                     (demande_id, nom, prenom, telephone, ville, date_debut, date_fin, 
                      type_vehicule, statut, sous_traitant, action, date_action) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'validee', ?, 'validation', datetime('now'))""", 
                  (demande[0], demande[1], demande[2], demande[3], demande[4], 
                   demande[5], demande[6], demande[7], demande[9]))

        conn.commit()

        c.execute("SELECT email, nom FROM sous_traitants WHERE ville=?", (ville,))
        sous_traitants = c.fetchall()
        c.close()

        # Construire les paramètres pour l'envoi aux partenaires de la ville
        subject = "Nouvelle demande de location"
        ville = demande[4]
        # Groupe: nombre de personnes si dispo, sinon inconnu
        try:
            groupe = int(demande[19]) if demande[19] is not None else None
        except Exception:
            groupe = None
        if not groupe:
            groupe = "?"

        # Itinéraire (strecke): préférer la colonne 'villes' si disponible, sinon la ville simple
        strecke = demande[14] if demande[14] else ville

        # Distance (entfernung): inconnue par défaut
        entfernung = "N/A"

        # Fahrten: liste (date, heure). On utilise date_debut si dispo.
        # Construire les trajets: si période (date_debut/date_fin) → un départ par jour à 08:30
        dd = demande[5]  # date_debut
        df = demande[6]  # date_fin
        dv = demande[11]  # date_voyage fallback
        fahrten = []
        default_time = "08:30"
        try:
            if dd and df:
                d0 = datetime.strptime(dd, '%Y-%m-%d').date()
                d1 = datetime.strptime(df, '%Y-%m-%d').date()
                if d1 >= d0:
                    cur = d0
                    while cur <= d1:
                        fahrten.append((cur.isoformat(), default_time))
                        cur += timedelta(days=1)
            elif dd or dv:
                d = dd or dv
                fahrten.append((d, default_time))
        except Exception:
            pass
        if not fahrten:
            fahrten = [("Date à confirmer", default_time)]

        # Temps estimé par jour
        stunden_pro_tag = "à définir"

        # Envoi asynchrone aux partenaires de la ville
        send_email_async(ville, subject, groupe, strecke, entfernung, fahrten, stunden_pro_tag, conn)

        return jsonify({"message": "Demande validée et emails envoyés"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500
@app.route("/demandes/<int:id>/email/preview", methods=["GET"])
def preview_email(id):
    """Construit le corps d'email partenaire sans envoi, pour prévisualisation/édition."""
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM demandes WHERE id=?", (id,))
        demande = c.fetchone()
        if not demande:
            c.close()
            return jsonify({"error": "Demande non trouvée"}), 404

        ville = demande[4]
        # groupe (nb_personnes)
        try:
            groupe = int(demande[19]) if demande[19] is not None and str(demande[19]).strip().isdigit() else ""
        except Exception:
            groupe = ""
        strecke = demande[14] if demande[14] else ville
        entfernung = ""
        dd = demande[5]
        df = demande[6]
        dv = demande[11]
        default_time = "08:30"
        fahrten = []
        try:
            if dd and df:
                d0 = datetime.strptime(dd, '%Y-%m-%d').date()
                d1 = datetime.strptime(df, '%Y-%m-%d').date()
                if d1 >= d0:
                    cur = d0
                    while cur <= d1:
                        fahrten.append((cur.isoformat(), default_time))
                        cur += timedelta(days=1)
            elif dd or dv:
                d = dd or dv
                fahrten.append((d, default_time))
        except Exception:
            pass
        stunden_pro_tag = ""
        # langue via pays
        # Déterminer la langue: d'abord via pays de la demande, sinon via pays des sous-traitants de la ville
        pays = demande[10] if len(demande) > 10 else ""
        lang = "fr"
        p = (pays or '').strip().lower()
        if p in ("germany", "allemagne"):
            lang = "de"
        elif p in ("united kingdom", "angleterre", "england", "uk"):
            lang = "en"
        elif p in ("denmark", "danemark"):
            lang = "da"
        else:
            # fallback: inspecter sous-traitants de la même ville
            try:
                c.execute("SELECT pays FROM sous_traitants WHERE ville=? LIMIT 1", (ville,))
                row = c.fetchone()
                if row and row[0]:
                    pays_st = row[0].strip().lower()
                    if pays_st in ("germany", "allemagne"):
                        lang = "de"
                    elif pays_st in ("united kingdom", "angleterre", "england", "uk"):
                        lang = "en"
                    elif pays_st in ("denmark", "danemark"):
                        lang = "da"
            except Exception:
                pass

        # Try AI composer first, fallback to template
        body_ai = None
        try:
            body_ai = compose_partner_email(lang, groupe, strecke, entfernung, fahrten, stunden_pro_tag)
        except Exception:
            body_ai = None
        body = body_ai or format_partner_email(lang, groupe, strecke, entfernung, fahrten, stunden_pro_tag)
        c.execute("SELECT email FROM sous_traitants WHERE ville=?", (ville,))
        recips = [r[0] for r in c.fetchall() if r[0]]
        c.close()
        return jsonify({
            "subject": subject_for_lang("Nouvelle demande de location", lang),
            "body": body,
            "recipients": recips,
            "lang": lang,
            "ville": ville
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/demandes/<int:id>/email/send", methods=["POST"])
def send_email_with_body(id):
    """Envoie le corps d'email fourni dans la requête à la liste de destinataires donnée."""
    try:
        data = request.get_json() or {}
        body = data.get("body", "")
        recipients = data.get("recipients", [])
        subject = data.get("subject", "Nouvelle demande de location")
        if not body or not recipients:
            return jsonify({"error": "Body et destinataires requis"}), 400
        # envoyer les emails
        send_custom_body_bcc(recipients, subject, body)
        # marquer la demande comme validée et historiser
        c = conn.cursor()
        c.execute("SELECT * FROM demandes WHERE id=?", (id,))
        demande = c.fetchone()
        if demande:
            c.execute("UPDATE demandes SET statut='validee' WHERE id=?", (id,))
            c.execute("""INSERT INTO historique 
                         (demande_id, nom, prenom, telephone, ville, date_debut, date_fin, 
                          type_vehicule, statut, sous_traitant, action, date_action) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'validee', ?, 'validation', datetime('now'))""",
                      (demande[0], demande[1], demande[2], demande[3], demande[4], 
                       demande[5], demande[6], demande[7], demande[9]))
            conn.commit()
        c.close()
        return jsonify({"message": "Email envoyé et demande validée"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/demandes/<int:id>", methods=["DELETE"])
def supprimer_demande(id):
    try:
        c = conn.cursor()
        # Vérifier si la demande existe
        c.execute("SELECT * FROM demandes WHERE id=?", (id,))
        demande = c.fetchone()
        if not demande:
            c.close()
            return jsonify({"error": "Demande non trouvée"}), 404
        
        # Sauvegarder dans l'historique avant suppression
        c.execute("""INSERT INTO historique 
                     (demande_id, nom, prenom, telephone, ville, date_debut, date_fin, 
                      type_vehicule, statut, sous_traitant, action, date_action) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'suppression', datetime('now'))""", 
                  (demande[0], demande[1], demande[2], demande[3], demande[4], 
                   demande[5], demande[6], demande[7], demande[8], demande[9]))
        
        # Supprimer la demande
        c.execute("DELETE FROM demandes WHERE id=?", (id,))
        conn.commit()
        c.close()
        
        return jsonify({"message": "Demande supprimée avec succès"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/fetch_emails", methods=["POST"])
def fetch_emails_route():
    try:
        def run_fetch():
            try:
                count = email_fetcher.fetch_emails()
                print(f"[INFO] fetch_emails terminé: {count} demande(s) insérée(s)")
                # Store status for UI
                from datetime import datetime as _dt
                LAST_FETCH["mode"] = getattr(email_fetcher, "LAST_PARSE_MODE", None)
                LAST_FETCH["inserted"] = count
                LAST_FETCH["at"] = _dt.now().isoformat(timespec='seconds')
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"[ERROR] fetch_emails a échoué: {e}")

        Thread(target=run_fetch).start()
        return jsonify({"message": "Récupération et traitement des emails en cours"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/fetch_status', methods=['GET'])
def fetch_status():
    return jsonify(LAST_FETCH)

@app.route("/demandes/filter", methods=["GET"])
def filter_demandes():
    ville = request.args.get("ville", "")
    date = request.args.get("date", "")
    try:
        c = conn.cursor()
        query = "SELECT * FROM demandes WHERE 1=1"
        params = []
        if ville:
            query += " AND ville=?"
            params.append(ville)
        if date:
            query += " AND date_debut<=? AND date_fin>=?"
            params.extend([date, date])
        c.execute(query, tuple(params))
        rows = c.fetchall()
        demandes = [dict(zip([column[0] for column in c.description], row)) for row in rows]
        c.close()
        return jsonify(demandes)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/demandes/export", methods=["GET"])
def export_csv():
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM demandes")
        rows = c.fetchall()
        header = [column[0] for column in c.description]
        c.close()

        def generate():
            yield ",".join(header) + "\n"
            for row in rows:
                yield ",".join([str(r) for r in row]) + "\n"

        return Response(generate(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment;filename=demandes.csv"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/historique", methods=["GET"])
def get_historique():
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM historique ORDER BY date_action DESC")
        rows = c.fetchall()
        historique = [dict(zip([column[0] for column in c.description], row)) for row in rows]
        c.close()
        return jsonify(historique)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/reporting/stats", methods=["GET"])
def get_stats():
    try:
        c = conn.cursor()
        
        # Statistiques générales
        c.execute("SELECT COUNT(*) FROM demandes")
        total_demandes = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM demandes WHERE statut='validee'")
        demandes_validees = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM demandes WHERE statut='en_attente'")
        demandes_en_attente = c.fetchone()[0]
        
        # Statistiques par ville
        c.execute("SELECT ville, COUNT(*) FROM demandes GROUP BY ville")
        stats_ville = [{"ville": row[0], "count": row[1]} for row in c.fetchall()]
        
        # Statistiques par type de véhicule
        c.execute("SELECT type_vehicule, COUNT(*) FROM demandes GROUP BY type_vehicule")
        stats_vehicule = [{"type": row[0], "count": row[1]} for row in c.fetchall()]
        
        # Statistiques par mois
        c.execute("""SELECT strftime('%Y-%m', date_debut) as mois, COUNT(*) 
                     FROM demandes GROUP BY strftime('%Y-%m', date_debut) 
                     ORDER BY mois DESC LIMIT 12""")
        stats_mois = [{"mois": row[0], "count": row[1]} for row in c.fetchall()]
        
        c.close()
        
        return jsonify({
            "total_demandes": total_demandes,
            "demandes_validees": demandes_validees,
            "demandes_en_attente": demandes_en_attente,
            "taux_validation": round((demandes_validees / total_demandes * 100) if total_demandes > 0 else 0, 2),
            "stats_ville": stats_ville,
            "stats_vehicule": stats_vehicule,
            "stats_mois": stats_mois
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/reporting/export", methods=["GET"])
def export_rapport():
    try:
        type_rapport = request.args.get("type", "complet")
        c = conn.cursor()
        
        if type_rapport == "historique":
            c.execute("SELECT * FROM historique ORDER BY date_action DESC")
            filename = "historique.csv"
        elif type_rapport == "stats":
            # Export des statistiques sous forme de rapport
            c.execute("""SELECT 
                         'Total demandes' as metric, COUNT(*) as value FROM demandes
                         UNION ALL
                         SELECT 'Demandes validées', COUNT(*) FROM demandes WHERE statut='validee'
                         UNION ALL
                         SELECT 'Demandes en attente', COUNT(*) FROM demandes WHERE statut='en_attente'""")
            filename = "rapport_stats.csv"
        else:
            c.execute("SELECT * FROM demandes")
            filename = "rapport_complet.csv"
            
        rows = c.fetchall()
        header = [column[0] for column in c.description]
        c.close()

        def generate():
            yield ",".join(header) + "\n"
            for row in rows:
                yield ",".join([str(r) if r is not None else "" for r in row]) + "\n"

        return Response(generate(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/sous-traitants", methods=["GET"])
def get_sous_traitants():
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM sous_traitants")
        rows = c.fetchall()
        sous_traitants = [dict(zip([column[0] for column in c.description], row)) for row in rows]
        c.close()
        return jsonify(sous_traitants)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/sous-traitants/upload", methods=["POST"])
def upload_sous_traitants():
    try:
        if 'file' not in request.files:
            print("[DEBUG] Aucun fichier trouvé dans la requête.")
            return jsonify({"error": "Aucun fichier fourni"}), 400

        file = request.files['file']
        if file.filename == '':
            print("[DEBUG] Le fichier n'a pas de nom.")
            return jsonify({"error": "Aucun fichier sélectionné"}), 400

        if not allowed_file(file.filename):
            print(f"[DEBUG] Type de fichier non autorisé : {file.filename}")
            return jsonify({"error": "Type de fichier non autorisé. Utilisez .xlsx ou .xls"}), 400

        # Sauvegarder le fichier temporairement
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Lire le fichier Excel
        try:
            df = pd.read_excel(filepath)
            print("[DEBUG] Colonnes trouvées dans le fichier Excel:", list(df.columns))
        except Exception as e:
            os.remove(filepath)  # Supprimer le fichier temporaire
            print(f"[DEBUG] Erreur lors de la lecture du fichier Excel: {str(e)}")
            return jsonify({"error": f"Erreur lors de la lecture du fichier Excel: {str(e)}"}), 400

        # Vérifier les colonnes attendues
        required_columns = ['Nom entreprise', 'Site internet', 'Pays', 'Ville', 'Email', 'Téléphone']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            os.remove(filepath)
            print(f"[DEBUG] Colonnes manquantes: {missing_columns}")
            return jsonify({
                "error": f"Colonnes manquantes dans le fichier Excel: {', '.join(missing_columns)}",
                "colonnes_attendues": required_columns,
                "colonnes_trouvees": list(df.columns)
            }), 400

        # Traiter les données et insérer en base
        c = conn.cursor()
        successful_inserts = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Nettoyer les données
                nom_entreprise = str(row['Nom entreprise']).strip() if pd.notna(row['Nom entreprise']) else ""
                site_internet = str(row['Site internet']).strip() if pd.notna(row['Site internet']) else ""
                pays = str(row['Pays']).strip() if pd.notna(row['Pays']) else ""
                ville = str(row['Ville']).strip() if pd.notna(row['Ville']) else ""
                email = str(row['Email']).strip() if pd.notna(row['Email']) else ""
                telephone = str(row['Téléphone']).strip() if pd.notna(row['Téléphone']) else ""

                # Vérifier que les champs obligatoires ne sont pas vides
                if not nom_entreprise or not email or not ville:
                    error_message = f"Ligne {index + 2}: Nom entreprise, Email et Ville sont obligatoires"
                    print(f"[DEBUG] {error_message}")
                    errors.append(error_message)
                    continue

                # Vérifier si l'email existe déjà
                c.execute("SELECT id FROM sous_traitants WHERE email = ?", (email,))
                if c.fetchone():
                    error_message = f"Ligne {index + 2}: Email {email} existe déjà"
                    print(f"[DEBUG] {error_message}")
                    errors.append(error_message)
                    continue

                # Insérer en base
                c.execute("""INSERT INTO sous_traitants 
                             (nom_entreprise, site_internet, pays, ville, email, telephone)
                             VALUES (?, ?, ?, ?, ?, ?)""",
                          (nom_entreprise, site_internet, pays, ville, email, telephone))
                successful_inserts += 1

            except Exception as e:
                error_message = f"Ligne {index + 2}: Erreur lors de l'insertion - {str(e)}"
                print(f"[DEBUG] {error_message}")
                errors.append(error_message)

        conn.commit()
        c.close()

        # Supprimer le fichier temporaire
        os.remove(filepath)

        print(f"[DEBUG] Import terminé: {successful_inserts} insérés, {len(errors)} erreurs")
        return jsonify({
            "message": f"Import terminé avec succès",
            "sous_traitants_ajoutes": successful_inserts,
            "total_lignes": len(df),
            "erreurs": errors
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[DEBUG] Erreur inattendue: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/sous-traitants/<int:id>", methods=["DELETE"])
def supprimer_sous_traitant(id):
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM sous_traitants WHERE id=?", (id,))
        sous_traitant = c.fetchone()
        
        if not sous_traitant:
            c.close()
            return jsonify({"error": "Sous-traitant non trouvé"}), 404
        
        c.execute("DELETE FROM sous_traitants WHERE id=?", (id,))
        conn.commit()
        c.close()
        
        return jsonify({"message": "Sous-traitant supprimé avec succès"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Endpoint to accept email and API password
@app.route('/save_credentials', methods=['POST'])
def save_credentials():
    try:
        # Support JSON or form-data; accept multiple key aliases
        data = request.get_json(silent=True) or {}
        if not data and request.form:
            data = request.form.to_dict()

        def _first_present(d: dict, keys):
            for k in keys:
                if k in d and d[k]:
                    return d[k]
            return None

        email = _first_present(data, ['email', 'user', 'username', 'EMAIL', 'EMAIL_ADDRESS', 'USER_EMAIL'])
        api_password = _first_present(data, ['apiPassword', 'appPassword', 'password', 'api_password', 'app_password', 'APP_PASSWORD'])
        imap_server = _first_present(data, ['imap_server', 'IMAP_SERVER', 'imapServer']) or 'imap.gmail.com'
        smtp_server = 'smtp.gmail.com'
        smtp_port = '587'
        openai_api_key = _first_present(data, ['OPENAI_API_KEY', 'openai_api_key', 'openaiKey'])
        openai_model = _first_present(data, ['OPENAI_MODEL', 'openai_model', 'openaiModel'])
        admin_password = _first_present(data, ['ADMIN_PASSWORD', 'admin_password', 'adminPassword'])
        require_admin = _first_present(data, ['REQUIRE_ADMIN', 'require_admin'])

        if not email or not api_password:
            return jsonify({"error": "Email and API password are required."}), 400

        # Save credentials next to this backend module so email_fetcher can read them
        cred_path = os.path.join(os.path.dirname(__file__), 'credentials.txt')
        with open(cred_path, 'w') as f:
            f.write(f"EMAIL={email}\nAPP_PASSWORD={api_password}\n")
            f.write(f"IMAP_SERVER={imap_server}\nSMTP_SERVER={smtp_server}\nSMTP_PORT={smtp_port}\n")
            if openai_api_key:
                f.write(f"OPENAI_API_KEY={openai_api_key}\n")
            if openai_model:
                f.write(f"OPENAI_MODEL={openai_model}\n")
            if admin_password:
                f.write(f"ADMIN_PASSWORD={admin_password}\n")
            if require_admin:
                f.write(f"REQUIRE_ADMIN={require_admin}\n")

        # Do not return secrets in response
        return jsonify({
            "message": "Credentials saved successfully.",
            "location": cred_path
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/credentials/status', methods=['GET'])
def credentials_status():
    try:
        cred_path = os.path.join(os.path.dirname(__file__), 'credentials.txt')
        env_present = bool(os.getenv('EMAIL') and os.getenv('APP_PASSWORD'))
        file_present = os.path.exists(cred_path)
        # detect openai and model
        openai_present = False
        openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        if file_present:
            try:
                kv = {}
                with open(cred_path, 'r') as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            kv[k.strip()] = v.strip()
                if kv.get('OPENAI_API_KEY'):
                    openai_present = True
                if kv.get('OPENAI_MODEL'):
                    openai_model = kv.get('OPENAI_MODEL')
            except Exception:
                pass
        if os.getenv('OPENAI_API_KEY'):
            openai_present = True
        return jsonify({
            "env_present": env_present,
            "file_present": file_present,
            "file_path": cred_path,
            "openai_present": openai_present,
            "model": openai_model,
            "require_admin_active": REQUIRE_ADMIN
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
