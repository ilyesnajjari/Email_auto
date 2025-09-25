from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from db import conn
import email_fetcher
from mailer import send_email
from threading import Thread
import csv

app = Flask(__name__)
CORS(app)

# --- Helper pour envoyer email asynchrone ---
def send_email_async(to_email, subject, body):
    Thread(target=send_email, args=(to_email, subject, body)).start()

# --- Routes ---
@app.route("/demandes", methods=["GET"])
def get_demandes():
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM demandes")
        rows = c.fetchall()
        demandes = [dict(zip([column[0] for column in c.description], row)) for row in rows]
        c.close()
        return jsonify(demandes)
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
