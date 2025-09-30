import imaplib
import email
import re
import html as html_module
from db import Database
from nlp_parser import extraire_infos as extraire_infos_nlp
try:
    from ai_parser import extraire_infos_ai
except Exception:
    extraire_infos_ai = None
from dotenv import load_dotenv
import os

load_dotenv()

IMAP_SERVER_DEFAULT = "imap.gmail.com"
LAST_PARSE_MODE = "nlp"  # updated each fetch: 'ai' or 'nlp'

def _load_openai_from_credentials_file() -> bool:
    """Load OPENAI_API_KEY, OPENAI_MODEL and optional flags from credentials.txt into environment if present."""
    try:
        base_dir = os.path.dirname(__file__)
        candidates = [
            os.path.join(base_dir, 'credentials.txt'),
            os.path.abspath(os.path.join(base_dir, '..', 'credentials.txt')),
        ]
        for p in candidates:
            if os.path.exists(p):
                with open(p, 'r') as f:
                    kv = {}
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            kv[k.strip()] = v.strip()
                changed = False
                if kv.get('OPENAI_API_KEY') and not os.getenv('OPENAI_API_KEY'):
                    os.environ['OPENAI_API_KEY'] = kv['OPENAI_API_KEY']
                    changed = True
                if kv.get('OPENAI_MODEL') and not os.getenv('OPENAI_MODEL'):
                    os.environ['OPENAI_MODEL'] = kv['OPENAI_MODEL']
                    changed = True
                if kv.get('ALLOW_MULTIPLE_DEMANDES_PER_EMAIL') and not os.getenv('ALLOW_MULTIPLE_DEMANDES_PER_EMAIL'):
                    os.environ['ALLOW_MULTIPLE_DEMANDES_PER_EMAIL'] = kv['ALLOW_MULTIPLE_DEMANDES_PER_EMAIL']
                    changed = True
                if changed:
                    print("[DEBUG] Loaded OPENAI_* from credentials.txt")
                return kv.get('OPENAI_API_KEY') is not None
    except Exception:
        pass
    return False

def _get_credentials():
    """Récupère EMAIL et APP_PASSWORD depuis .env, puis fallback credentials.txt si manquants."""
    # Recharger .env à chaque appel pour prendre en compte les changements sans redémarrer
    try:
        # 1) Standard .env lookup
        load_dotenv(override=True)
        # 2) Explicit fallback paths: backend/.env, repo/.env, repo/env
        base_dir = os.path.dirname(__file__)
        root_dir = os.path.abspath(os.path.join(base_dir, ".."))
        candidate_envs = [
            os.path.join(base_dir, ".env"),
            os.path.join(root_dir, ".env"),
            os.path.join(root_dir, "env"),  # file named "env" without dot
        ]
        for p in candidate_envs:
            if os.path.exists(p):
                load_dotenv(dotenv_path=p, override=True)
                print(f"[DEBUG] Loaded environment file: {p}")
    except Exception:
        pass
    # Accepter quelques alias d'env
    email_env = os.getenv("EMAIL") or os.getenv("USER_EMAIL") or os.getenv("EMAIL_ADDRESS")
    app_pw_env = os.getenv("APP_PASSWORD") or os.getenv("API_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")
    imap_server = os.getenv("IMAP_SERVER", IMAP_SERVER_DEFAULT)

    if email_env and app_pw_env:
        print("[DEBUG] Credentials source: .env variables")
        return email_env, app_pw_env, imap_server

    # Fallback: credentials.txt (format: email=...\napi_password=...)
    cred_path = os.path.join(os.path.dirname(__file__), "credentials.txt")
    exists_primary = os.path.exists(cred_path)
    print(f"[DEBUG] Looking for credentials file at: {cred_path} | exists={exists_primary}")
    if exists_primary:
        try:
            with open(cred_path, "r") as f:
                lines = f.read().splitlines()
            kv = {}
            for line in lines:
                if "=" in line:
                    k, v = line.split("=", 1)
                    kv[k.strip()] = v.strip()
            # Accept lower/upper and common aliases
            email_file = (
                kv.get("email")
                or kv.get("EMAIL")
                or kv.get("user")
                or kv.get("username")
                or kv.get("USER")
                or kv.get("USERNAME")
            )
            app_pw_file = (
                kv.get("api_password")
                or kv.get("API_PASSWORD")
                or kv.get("app_password")
                or kv.get("APP_PASSWORD")
                or kv.get("apiPassword")
                or kv.get("appPassword")
                or kv.get("password")
                or kv.get("PASSWORD")
            )
            # Optional IMAP server from file
            file_imap = kv.get("imap_server") or kv.get("IMAP_SERVER")
            if file_imap:
                imap_server = file_imap
            if email_file and app_pw_file:
                print("[DEBUG] Credentials source: credentials.txt")
                return email_file, app_pw_file, imap_server
            else:
                print(f"[DEBUG] credentials.txt found but keys missing. Keys present: {list(kv.keys())}")
        except Exception:
            pass
    # Fallback: parent directory (repo root)
    cred_path_alt = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.txt"))
    exists_alt = os.path.exists(cred_path_alt)
    print(f"[DEBUG] Looking for credentials file at (alt): {cred_path_alt} | exists={exists_alt}")
    if exists_alt:
        try:
            with open(cred_path_alt, "r") as f:
                lines = f.read().splitlines()
            kv = {}
            for line in lines:
                if "=" in line:
                    k, v = line.split("=", 1)
                    kv[k.strip()] = v.strip()
            email_file = (
                kv.get("email")
                or kv.get("EMAIL")
                or kv.get("user")
                or kv.get("username")
                or kv.get("USER")
                or kv.get("USERNAME")
            )
            app_pw_file = (
                kv.get("api_password")
                or kv.get("API_PASSWORD")
                or kv.get("app_password")
                or kv.get("APP_PASSWORD")
                or kv.get("apiPassword")
                or kv.get("appPassword")
                or kv.get("password")
                or kv.get("PASSWORD")
            )
            file_imap = kv.get("imap_server") or kv.get("IMAP_SERVER")
            if file_imap:
                imap_server = file_imap
            if email_file and app_pw_file:
                print("[DEBUG] Credentials source: credentials.txt (alt path)")
                return email_file, app_pw_file, imap_server
            else:
                print(f"[DEBUG] alt credentials.txt found but keys missing. Keys present: {list(kv.keys())}")
        except Exception:
            pass
    return None, None, imap_server

# Créer une instance de la classe Database
db = Database()

def _extract_email_from_header(header_val: str) -> str:
    if not header_val:
        return ""
    # Exemples: "John <john@example.com>", "john@example.com"
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", header_val)
    return m.group(0) if m else ""


def fetch_emails() -> int:
    """Récupère les emails non lus, extrait les demandes, insère via Database.
    Retourne le nombre de demandes insérées.
    """
    global LAST_PARSE_MODE
    inserted = 0
    try:
        EMAIL, APP_PASSWORD, IMAP_SERVER = _get_credentials()
        if not EMAIL or not APP_PASSWORD:
            print("[ERROR] EMAIL ou APP_PASSWORD non configurés. Mettez-les dans .env ou via /save_credentials.")
            return inserted

        mail = imaplib.IMAP4_SSL(IMAP_SERVER or IMAP_SERVER_DEFAULT)
        mail.login(EMAIL, APP_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, '(UNSEEN)')
        email_ids = messages[0].split() if messages and messages[0] else []
        for num in email_ids:
            status, data = mail.fetch(num, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Récupérer le corps de l’email (texte brut prioritaire, sinon HTML converti)
            def _html_to_text(h: str) -> str:
                try:
                    # Préserver une structure lisible pour les tableaux et paragraphes
                    # 1) Normaliser les fin de lignes pour tables
                    # Table sections
                    h = re.sub(r'</\s*(thead|tbody|tfoot)\s*>', '\n', h, flags=re.I)
                    h = re.sub(r'<\s*(thead|tbody|tfoot)[^>]*>', '', h, flags=re.I)
                    h = re.sub(r'</\s*tr\s*>', '\n', h, flags=re.I)
                    h = re.sub(r'<\s*tr[^>]*>', '', h, flags=re.I)
                    # Convertir cellules en séparateurs " | "
                    h = re.sub(r'</\s*t[dh]\s*>', ' | ', h, flags=re.I)
                    h = re.sub(r'<\s*t[dh][^>]*>', '', h, flags=re.I)

                    # 2) Sauts de ligne pour br/p/div
                    h = re.sub(r'<\s*br\s*/?>', '\n', h, flags=re.I)
                    h = re.sub(r'</\s*p\s*>', '\n\n', h, flags=re.I)
                    h = re.sub(r'</\s*div\s*>', '\n', h, flags=re.I)
                    # list items to lines
                    h = re.sub(r'</\s*li\s*>', '\n', h, flags=re.I)
                    h = re.sub(r'<\s*li[^>]*>', '- ', h, flags=re.I)
                    # supprimer scripts/styles
                    h = re.sub(r'<script[\s\S]*?</script>', '', h, flags=re.I)
                    h = re.sub(r'<style[\s\S]*?</style>', '', h, flags=re.I)
                    # 3) Enlever le reste des balises
                    h = re.sub(r'<[^>]+>', '', h)
                    # 4) Nettoyer séparateurs superflus
                    # remplacer suites de " | " et espaces
                    h = re.sub(r'(\s*\|\s*){2,}', ' | ', h)
                    # trim chaque ligne
                    h = '\n'.join([ln.strip(' |\t ') for ln in h.splitlines()])
                    # décoder entités HTML
                    return html_module.unescape(h)
                except Exception:
                    return h

            def _is_attachment(part) -> bool:
                try:
                    cd = (part.get("Content-Disposition") or "").lower()
                    if 'attachment' in cd:
                        return True
                    filename = part.get_filename()
                    return bool(filename)
                except Exception:
                    return False

            def _decode_payload(part) -> str:
                try:
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        return ""
                    charset = part.get_content_charset() or "utf-8"
                    for enc in [charset, 'utf-8', 'latin-1', 'windows-1252']:
                        try:
                            return payload.decode(enc, errors='ignore')
                        except Exception:
                            continue
                    return payload.decode(errors='ignore')
                except Exception:
                    return ""

            body = ""
            html_body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = (part.get_content_type() or '').lower()
                    if _is_attachment(part):
                        continue
                    if ctype == "text/plain":
                        text = _decode_payload(part)
                        if text:
                            body += text
                    elif ctype == "text/html":
                        text = _decode_payload(part)
                        if text:
                            html_body += text
            else:
                ctype = (msg.get_content_type() or '').lower()
                part = msg
                if ctype == "text/plain" and not _is_attachment(part):
                    body = _decode_payload(part)
                elif ctype == "text/html" and not _is_attachment(part):
                    html_body = _decode_payload(part)
            # Heuristique: si text/plain est vide ou anémique, utiliser le HTML
            if html_body:
                html_text = _html_to_text(html_body)
                def _is_meaningful(s: str) -> bool:
                    s = (s or '').strip()
                    if len(s) < 30:
                        return False
                    # doit contenir quelques lettres
                    return bool(re.search(r'[A-Za-zÀ-ÿ]{5,}', s))
                if not _is_meaningful(body) or (len(html_text) > len(body) * 2):
                    body = html_text

            # Ensure OPENAI credentials are available from file if not in env
            if not (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_TOKEN")):
                _load_openai_from_credentials_file()

            # Prefer AI parsing if OPENAI_API_KEY is configured
            demandes = []
            use_ai = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_TOKEN")
            if use_ai and extraire_infos_ai:
                try:
                    demandes = extraire_infos_ai(body)
                    print(f"[INFO] Parsed with AI, demandes: {len(demandes)}")
                    LAST_PARSE_MODE = "ai"
                except Exception:
                    # Fallback to NLP parser on any AI failure
                    demandes = extraire_infos_nlp(body)
                    print(f"[INFO] Fallback to NLP parser, demandes: {len(demandes)}")
                    LAST_PARSE_MODE = "nlp"
            else:
                demandes = extraire_infos_nlp(body)
                print(f"[INFO] Parsed with NLP, demandes: {len(demandes)}")
                LAST_PARSE_MODE = "nlp"

            # Post-process: by default, avoid inserting multiple demandes per email.
            raw_count = len(demandes)
            allow_multi = (os.getenv('ALLOW_MULTIPLE_DEMANDES_PER_EMAIL', 'false').lower() in ('1', 'true', 'yes', 'y'))

            def _score_demande(d: dict) -> int:
                score = 0
                if d.get('email'): score += 2
                if d.get('telephone'): score += 2
                if d.get('ville'): score += 2
                if d.get('date_debut'): score += 2
                if d.get('date_fin'): score += 1
                if d.get('type_vehicule'): score += 1
                if d.get('nb_personnes'): score += 1
                return score

            def _unique_key(d: dict):
                return (
                    (d.get('email') or '').lower().strip(),
                    re.sub(r'\D', '', d.get('telephone') or ''),
                    (d.get('ville') or '').lower().strip(),
                    d.get('date_debut') or '',
                    d.get('date_fin') or '',
                )

            # de-duplicate likely duplicates
            uniq = []
            seen = set()
            for d in demandes:
                k = _unique_key(d)
                if k not in seen:
                    seen.add(k)
                    uniq.append(d)

            if not allow_multi and uniq:
                # pick the best single demande
                uniq.sort(key=lambda d: (_score_demande(d), len((d.get('infos_libres') or d.get('corps_mail') or ''))), reverse=True)
                demandes = [uniq[0]]
            else:
                demandes = uniq
            print(f"[INFO] Selected demandes: {len(demandes)} from extracted {raw_count} (allow_multiple={allow_multi})")

            sender_email = _extract_email_from_header(msg.get('From', ''))
            subject = msg.get('Subject', '')

            for d in demandes:
                # fallback email depuis l'entête si manquant
                if not d.get('email') and sender_email:
                    d['email'] = sender_email
                # ajouter sujet dans infos_libres si utile
                if subject and 'infos_libres' in d and subject not in d['infos_libres']:
                    d['infos_libres'] = f"Subject: {subject}\n\n" + d['infos_libres']
                # toujours conserver le corps complet
                d['corps_mail'] = body
                # insertion
                db.insert_demande(d)
                inserted += 1

            # Marquer comme vu
            mail.store(num, '+FLAGS', '\\Seen')

        mail.logout()
        print(f"[INFO] Emails traités: {len(email_ids)}, demandes insérées: {inserted}")
        return inserted

    except Exception as e:
        print(f"[ERROR] Impossible de récupérer les emails: {e}")
        return inserted
