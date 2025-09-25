import imaplib
import email
from db import conn
from nlp_parser import extraire_infos
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL = os.getenv("EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")

def fetch_emails():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, APP_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, '(UNSEEN)')
        for num in messages[0].split():
            status, data = mail.fetch(num, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Récupérer le corps
            if msg.is_multipart():
                body = ""
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode()
            else:
                body = msg.get_payload(decode=True).decode()

            infos = extraire_infos(body)

            # Insérer dans la DB
            c = conn.cursor()
            c.execute("""
                INSERT INTO demandes (nom, prenom, telephone, ville, date_debut, date_fin, type_vehicule)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (infos['nom'], infos['prenom'], infos['telephone'], infos['ville'],
                  infos['date_debut'], infos['date_fin'], infos['type_vehicule']))
            conn.commit()
            c.close()

        mail.logout()
        print("[INFO] Emails récupérés et traités avec succès")
    except Exception as e:
        print(f"[ERROR] Impossible de récupérer les emails: {e}")
