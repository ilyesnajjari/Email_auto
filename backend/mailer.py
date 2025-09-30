import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
# Import AI email composer (absolute import to work when backend isn't a package)
try:
    import ai_email as ai_email_module
except Exception:
    ai_email_module = None

load_dotenv()

# Reload env from common locations, including repo-root 'env'
try:
    base_dir = os.path.dirname(__file__)
    root_dir = os.path.abspath(os.path.join(base_dir, ".."))
    for p in [
        os.path.join(base_dir, ".env"),
        os.path.join(root_dir, ".env"),
        os.path.join(root_dir, "env"),
    ]:
        if os.path.exists(p):
            load_dotenv(dotenv_path=p, override=True)
except Exception:
    pass

# Load credentials from file if available (backend/credentials.txt preferred)
cred_path = os.path.join(os.path.dirname(__file__), 'credentials.txt')
cred_path_alt = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'credentials.txt'))

def _load_creds_from_file(path):
    kv = {}
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                kv[k.strip()] = v.strip()
    except Exception:
        pass
    return kv

creds = {}
if os.path.exists(cred_path):
    creds = _load_creds_from_file(cred_path)
elif os.path.exists(cred_path_alt):
    creds = _load_creds_from_file(cred_path_alt)

EMAIL = (
    creds.get('EMAIL') or creds.get('email') or os.getenv('EMAIL')
)
APP_PASSWORD = (
    creds.get('APP_PASSWORD') or creds.get('api_password') or os.getenv('APP_PASSWORD')
)

SMTP_SERVER = (
    creds.get('SMTP_SERVER') or os.getenv('SMTP_SERVER') or "smtp.gmail.com"
)
try:
    SMTP_PORT = int(creds.get('SMTP_PORT') or os.getenv('SMTP_PORT') or 587)
except Exception:
    SMTP_PORT = 587

# Mapping pays → langue
COUNTRY_LANGUAGE = {
    "Allemagne": "de",
    "Germany": "de",
    "France": "fr",
    "Belgique": "fr",
    "Belgium": "fr",
    "Danemark": "da",
    "Denmark": "da",
    "Angleterre": "en",
    "England": "en",
    "Canada": "en"
}

SUBJECT_BY_LANG = {
    "de": "Anfrage: Bus mit Fahrer",
    "fr": "Nouvelle demande de location",
    "en": "New transport request",
    "da": "Ny forespørgsel: Bus med chauffør",
}

def subject_for_lang(base_subject: str | None, lang: str) -> str:
    return SUBJECT_BY_LANG.get(lang, base_subject or "New request")

def format_partner_email(lang, gruppe, strecke, entfernung, fahrten, stunden_pro_tag):
    """Formate le mail selon la langue en omettant les infos inconnues."""

    def _known(val: str) -> bool:
        if val is None:
            return False
        if isinstance(val, (int, float)):
            return True
        v = str(val).strip().lower()
        return v not in ("", "n/a", "?", "à définir", "to be defined", "tbd")

    if lang == "de":  # Allemand
        mail = "Guten Tag,\n\n"
        mail += "wir suchen einen Bus mit Fahrer für folgende Transfers:\n\n"
        mail += "Details\n"
        if _known(gruppe):
            mail += f"Gruppe: ca. {gruppe} Personen\n"
        if _known(strecke):
            mail += f"Strecke: {strecke}\n"
        if _known(entfernung):
            mail += f"Entfernung: {entfernung}\n"
        mail += "\nFahrten\n"
        for date, uhrzeit in fahrten:
            mail += f"{date} – Abfahrt {uhrzeit} Uhr\n"
        total_parts = [f"{len(fahrten)} Fahrten"]
        if _known(entfernung):
            total_parts.append(entfernung)
        if _known(stunden_pro_tag):
            total_parts.append(f"geschätzte Einsatzzeit pro Tag ca. {stunden_pro_tag}")
        mail += "\n" + ("Gesamt: " + ", ".join(total_parts) + ".\n\n")
        mail += "Wir bitten um Ihr Verfügbarkeits- und Preisangebot.\n\nVielen Dank im Voraus.\n--------------\n"
    elif lang == "da":  # Danois
        mail = "Goddag,\n\n"
        mail += "Vi søger en bus med chauffør til følgende transporter:\n\n"
        mail += "Detaljer\n"
        if _known(gruppe):
            mail += f"Gruppe: ca. {gruppe} personer\n"
        if _known(strecke):
            mail += f"Rute: {strecke}\n"
        if _known(entfernung):
            mail += f"Afstand: {entfernung}\n"
        mail += "\nTure\n"
        for date, tid in fahrten:
            mail += f"{date} – Afgang {tid} \n"
        total_parts = [f"{len(fahrten)} ture"]
        if _known(entfernung):
            total_parts.append(entfernung)
        if _known(stunden_pro_tag):
            total_parts.append(f"anslået varighed pr. dag ca. {stunden_pro_tag}")
        mail += "\n" + ("I alt: " + ", ".join(total_parts) + ".\n\n")
        mail += "Send venligst jeres tilgængelighed og prisoverslag.\n\nPå forhånd tak.\n--------------\n"
    elif lang == "fr":  # Français
        mail = "Bonjour,\n\n"
        mail += "Nous recherchons un bus avec chauffeur pour les trajets suivants :\n\n"
        mail += "Détails\n"
        if _known(gruppe):
            mail += f"Groupe : environ {gruppe} personnes\n"
        if _known(strecke):
            mail += f"Trajet : {strecke}\n"
        if _known(entfernung):
            mail += f"Distance : {entfernung}\n"
        mail += "\nTrajets\n"
        for date, heure in fahrten:
            mail += f"{date} – Départ {heure} h\n"
        total_parts = [f"{len(fahrten)} trajets"]
        if _known(entfernung):
            total_parts.append(entfernung)
        if _known(stunden_pro_tag):
            total_parts.append(f"durée estimée par jour environ {stunden_pro_tag}")
        mail += "\n" + ("Total : " + ", ".join(total_parts) + ".\n\n")
        mail += "Merci de nous communiquer vos disponibilités et vos tarifs.\n\nCordialement,\n--------------\n"
    else:  # Anglais par défaut
        mail = "Hello,\n\n"
        mail += "We are looking for a bus with driver for the following transfers:\n\n"
        mail += "Details\n"
        if _known(gruppe):
            mail += f"Group: approx. {gruppe} persons\n"
        if _known(strecke):
            mail += f"Route: {strecke}\n"
        if _known(entfernung):
            mail += f"Distance: {entfernung}\n"
        mail += "\nTrips\n"
        for date, time in fahrten:
            mail += f"{date} – Departure {time}\n"
        total_parts = [f"{len(fahrten)} trips"]
        if _known(entfernung):
            total_parts.append(entfernung)
        if _known(stunden_pro_tag):
            total_parts.append(f"estimated duration per day approx. {stunden_pro_tag}")
        mail += "\n" + ("Total: " + ", ".join(total_parts) + ".\n\n")
        mail += "Please send us your availability and quote.\n\nThank you in advance.\n--------------\n"
    return mail

def send_email_partners_bcc(ville, subject, gruppe, strecke, entfernung, fahrten, stunden_pro_tag, conn):
    """
    Envoie le mail aux partenaires d'une ville en CCI, groupés par langue (1 email par langue).
    """
    try:
        c = conn.cursor()
        c.execute("SELECT email, pays FROM sous_traitants WHERE ville=?", (ville,))
        partenaires = [row for row in c.fetchall() if row[0]]
        c.close()
        if not partenaires:
            print(f"[INFO] Aucun partenaire trouvé pour la ville {ville}")
            return

        # Regrouper par langue
        groups = {}
        for email_addr, pays in partenaires:
            lang = COUNTRY_LANGUAGE.get(pays, "en")
            groups.setdefault(lang, []).append(email_addr)

        for lang, recipients in groups.items():
            # Compose body via AI if available, else fallback to template
            body_ai = None
            if ai_email_module is not None:
                try:
                    body_ai = ai_email_module.compose_partner_email(lang, gruppe, strecke, entfernung, fahrten, stunden_pro_tag)
                except Exception:
                    body_ai = None
            body = body_ai or format_partner_email(lang, gruppe, strecke, entfernung, fahrten, stunden_pro_tag)

            # Envoyer un seul email avec tous les destinataires en BCC (CCI)
            try:
                msg = MIMEText(body)
                msg["Subject"] = subject_for_lang(subject, lang)
                msg["From"] = EMAIL
                msg["To"] = EMAIL  # masque les adresses, BCC via enveloppe SMTP

                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(EMAIL, APP_PASSWORD)
                server.sendmail(EMAIL, recipients, msg.as_string())
                server.quit()
                print(f"[INFO] Email envoyé (lang={lang}) en CCI à {len(recipients)} destinataires")
            except Exception as se:
                print(f"[ERROR] Envoi (lang={lang}) échoué: {se}")
    except Exception as e:
        print(f"[ERROR] Impossible d'envoyer email partenaires CCI: {e}")


def send_custom_body_bcc(recipients, subject, body):
    """Envoie un seul email avec tous les destinataires en BCC (CCI)."""
    try:
        if not recipients:
            return
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL
        # Put a neutral To: to avoid exposing addresses; all recipients go to BCC at SMTP level
        msg["To"] = EMAIL

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL, APP_PASSWORD)
        # BCC achieved by passing recipients in sendmail but not listing in headers
        server.sendmail(EMAIL, recipients, msg.as_string())
        server.quit()
        print(f"[INFO] Email personnalisé envoyé en CCI à {len(recipients)} destinataires")
    except Exception as e:
        print(f"[ERROR] Impossible d'envoyer email personnalisé: {e}")
