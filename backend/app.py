from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from db import conn
import email_fetcher
from mailer import send_email
from threading import Thread
import csv
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

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

# --- Helper pour envoyer email asynchrone ---
def send_email_async(to_email, subject, body):
    Thread(target=send_email, args=(to_email, subject, body)).start()

# --- Routes ---
@app.route("/demandes", methods=["GET"])
def get_demandes():
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM demandes ORDER BY date_enregistrement DESC")
        rows = c.fetchall()
        demandes = [dict(zip([column[0] for column in c.description], row)) for row in rows]
        
        # Ajouter les calculs pour chaque demande
        demandes_formatted = [format_demande_with_calculations(demande) for demande in demandes]
        
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

        c.execute("UPDATE demandes SET statut='validee' WHERE id=?", (id,))
        
        # Ajouter à l'historique
        c.execute("""INSERT INTO historique 
                     (demande_id, nom, prenom, telephone, ville, date_debut, date_fin, 
                      type_vehicule, statut, sous_traitant, action, date_action) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'validee', ?, 'validation', datetime('now'))""", 
                  (demande[0], demande[1], demande[2], demande[3], demande[4], 
                   demande[5], demande[6], demande[7], demande[9]))
        
        conn.commit()

        ville = demande[4]
        c.execute("SELECT email, nom FROM sous_traitants WHERE ville=?", (ville,))
        sous_traitants = c.fetchall()
        c.close()

        for email_dest, nom_st in sous_traitants:
            body = f"""Nouvelle demande de location :
Client : {demande[1]} {demande[2]}
Téléphone : {demande[3]}
Ville : {demande[4]}
Date : {demande[5]} au {demande[6]}
Véhicule : {demande[7]}
"""
            send_email_async(email_dest, "Nouvelle demande de location", body)

        return jsonify({"message": "Demande validée et emails envoyés"})
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
        Thread(target=email_fetcher.fetch_emails).start()
        return jsonify({"message": "Récupération et traitement des emails en cours"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
            return jsonify({"error": "Aucun fichier fourni"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Aucun fichier sélectionné"}), 400
            
        if not allowed_file(file.filename):
            return jsonify({"error": "Type de fichier non autorisé. Utilisez .xlsx ou .xls"}), 400
        
        # Sauvegarder le fichier temporairement
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Lire le fichier Excel
        try:
            df = pd.read_excel(filepath)
        except Exception as e:
            os.remove(filepath)  # Supprimer le fichier temporaire
            return jsonify({"error": f"Erreur lors de la lecture du fichier Excel: {str(e)}"}), 400
        
        # Vérifier les colonnes attendues
        required_columns = ['Nom entreprise', 'Site internet', 'Pays', 'Ville', 'Email', 'Téléphone']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            os.remove(filepath)
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
                    errors.append(f"Ligne {index + 2}: Nom entreprise, Email et Ville sont obligatoires")
                    continue
                
                # Vérifier si l'email existe déjà
                c.execute("SELECT id FROM sous_traitants WHERE email = ?", (email,))
                if c.fetchone():
                    errors.append(f"Ligne {index + 2}: Email {email} existe déjà")
                    continue
                
                # Insérer en base
                c.execute("""INSERT INTO sous_traitants 
                             (nom_entreprise, site_internet, pays, ville, email, telephone)
                             VALUES (?, ?, ?, ?, ?, ?)""",
                          (nom_entreprise, site_internet, pays, ville, email, telephone))
                successful_inserts += 1
                
            except Exception as e:
                errors.append(f"Ligne {index + 2}: Erreur lors de l'insertion - {str(e)}")
        
        conn.commit()
        c.close()
        
        # Supprimer le fichier temporaire
        os.remove(filepath)
        
        return jsonify({
            "message": f"Import terminé avec succès",
            "sous_traitants_ajoutes": successful_inserts,
            "total_lignes": len(df),
            "erreurs": errors
        })
        
    except Exception as e:
        import traceback; traceback.print_exc()
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
