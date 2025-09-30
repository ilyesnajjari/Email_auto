import os
import json
# Optional dependency: dotenv
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False
# Optional dependency: requests
try:
    import requests
except Exception:
    requests = None

# Load env from common locations
load_dotenv()
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


def _load_openai_from_credentials_file():
    """Load OPENAI_API_KEY and OPENAI_MODEL from backend/credentials.txt if not set."""
    try:
        cred_path = os.path.join(os.path.dirname(__file__), 'credentials.txt')
        cred_path_alt = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'credentials.txt'))
        path = cred_path if os.path.exists(cred_path) else (cred_path_alt if os.path.exists(cred_path_alt) else None)
        if not path:
            return
        kv = {}
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                kv[k.strip()] = v.strip()
        if not os.getenv('OPENAI_API_KEY') and kv.get('OPENAI_API_KEY'):
            os.environ['OPENAI_API_KEY'] = kv.get('OPENAI_API_KEY')
        if not os.getenv('OPENAI_MODEL') and kv.get('OPENAI_MODEL'):
            os.environ['OPENAI_MODEL'] = kv.get('OPENAI_MODEL')
    except Exception:
        pass


def _build_prompt(lang: str, gruppe, strecke, entfernung, fahrten, stunden_pro_tag):
    """Build an instruction to compose the partner email in the specified language and structure.

    Parameters:
      - lang: 'de' | 'fr' | 'en'
      - gruppe: int|str|None → number of persons (approx). Omit if unknown.
      - strecke: str|None → route description (e.g., City A → City B). Omit if unknown.
      - entfernung: str|None → distance and duration (free text). Omit if unknown.
      - fahrten: list[(date_str, time_str)] → date and departure time per line. Skip section if list empty.
      - stunden_pro_tag: str|None → estimated duration per day. Omit if unknown.
    """
    # Normalize inputs
    def known(x):
        return x is not None and str(x).strip() not in ("", "?", "N/A", "n/a")

    lines_fahrten = []
    if isinstance(fahrten, (list, tuple)):
        for it in fahrten:
            try:
                d, t = it
            except Exception:
                continue
            d = (d or "").strip()
            t = (t or "").strip()
            if d:
                lines_fahrten.append((d, t))

    templates = {
        'de': {
            'greeting': "Guten Tag,",
            'intro': "wir suchen einen Bus mit Fahrer für folgende Transfers:",
            'details': "Details",
            'group': lambda g: f"Gruppe: ca. {g} Personen",
            'route': lambda s: f"Strecke: {s}",
            'distance': lambda e: f"Entfernung: {e}",
            'trips': "Fahrten",
            'trip_line': lambda d, t: f"{d} – Abfahrt {t or '00:00'} Uhr",
            'total': "Gesamt",
            'total_line': lambda n, e, spt: ", ".join([
                f"{n} Fahrten",
                *([e] if known(e) else []),
                *([f"geschätzte Einsatzzeit pro Tag ca. {spt}"] if known(spt) else []),
            ]) + ".",
            'request': "Wir bitten um Ihr Verfügbarkeits- und Preisangebot.",
            'thanks': "Vielen Dank im Voraus.",
        },
        'da': {
            'greeting': "Goddag,",
            'intro': "Vi søger en bus med chauffør til følgende transporter:",
            'details': "Detaljer",
            'group': lambda g: f"Gruppe: ca. {g} personer",
            'route': lambda s: f"Rute: {s}",
            'distance': lambda e: f"Afstand: {e}",
            'trips': "Ture",
            'trip_line': lambda d, t: f"{d} – Afgang {t or '00:00'}",
            'total': "I alt",
            'total_line': lambda n, e, spt: ", ".join([
                f"{n} ture",
                *([e] if known(e) else []),
                *([f"anslået varighed pr. dag ca. {spt}"] if known(spt) else []),
            ]) + ".",
            'request': "Send venligst jeres tilgængelighed og prisoverslag.",
            'thanks': "På forhånd tak.",
        },
        'fr': {
            'greeting': "Bonjour,",
            'intro': "Nous recherchons un bus avec chauffeur pour les trajets suivants :",
            'details': "Détails",
            'group': lambda g: f"Groupe : environ {g} personnes",
            'route': lambda s: f"Trajet : {s}",
            'distance': lambda e: f"Distance : {e}",
            'trips': "Trajets",
            'trip_line': lambda d, t: f"{d} – Départ {t or '00:00'} h",
            'total': "Total",
            'total_line': lambda n, e, spt: ", ".join([
                f"{n} trajets",
                *([e] if known(e) else []),
                *([f"durée estimée par jour environ {spt}"] if known(spt) else []),
            ]) + ".",
            'request': "Merci de nous communiquer vos disponibilités et vos tarifs.",
            'thanks': "Cordialement,",
        },
        'en': {
            'greeting': "Hello,",
            'intro': "We are looking for a bus with driver for the following transfers:",
            'details': "Details",
            'group': lambda g: f"Group: approx. {g} persons",
            'route': lambda s: f"Route: {s}",
            'distance': lambda e: f"Distance: {e}",
            'trips': "Trips",
            'trip_line': lambda d, t: f"{d} – Departure {t or '00:00'}",
            'total': "Total",
            'total_line': lambda n, e, spt: ", ".join([
                f"{n} trips",
                *([e] if known(e) else []),
                *([f"estimated duration per day approx. {spt}"] if known(spt) else []),
            ]) + ".",
            'request': "Please send us your availability and quote.",
            'thanks': "Thank you in advance.",
        }
    }

    t = templates.get(lang or 'fr', templates['fr'])

    # Provide the LLM with explicit instructions and a JSON with the facts.
    instructions = (
        "Compose a short, professional partner inquiry email in the specified language and layout.\n"
        "Strictly follow this structure and wording style (do not add extra sections):\n"
        "<GREETING>\n\n"
        "<INTRO>\n\n"
        "<DETAILS>\n"
        "[Group line if known]\n"
        "[Route line if known]\n"
        "[Distance line if known]\n\n"
        "<TRIPS>\n"
        "One line per trip: '<DATE> – Departure <TIME>' (adapt language), skip section if no trips.\n\n"
        "<TOTAL>: '<N trips>[, <distance>][, <per-day estimate>].'\n\n"
        "<REQUEST>\n\n"
        "<THANKS>\n"
        "Use only plain text. Do not invent unknown values. Keep it concise.\n"
    )

    # Facts given to model
    facts = {
        "language": lang,
        "group_size": str(gruppe) if known(gruppe) else None,
        "route": strecke if known(strecke) else None,
        "distance": entfernung if known(entfernung) else None,
        "trips": [
            {"date": d, "time": (t or "00:00")}
            for d, t in lines_fahrten
        ],
        "per_day_estimate": stunden_pro_tag if known(stunden_pro_tag) else None,
        "phrases": {
            "GREETING": t['greeting'],
            "INTRO": t['intro'],
            "DETAILS": t['details'],
            "TRIPS": t['trips'],
            "TOTAL": t['total'],
            "REQUEST": t['request'],
            "THANKS": t['thanks'],
        }
    }

    return instructions, facts


def compose_partner_email(lang: str, gruppe, strecke, entfernung, fahrten, stunden_pro_tag):
    """Compose the partner email using OpenAI when possible. Returns text or None on failure."""
    # Ensure key/model present (load from credentials file if needed)
    _load_openai_from_credentials_file()
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    if not api_key or requests is None:
        return None

    instructions, facts = _build_prompt(lang, gruppe, strecke, entfernung, fahrten, stunden_pro_tag)

    # Try Responses API first (text output)
    try:
        url = 'https://api.openai.com/v1/responses'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': model,
            'input': [
                {"role": "system", "content": "You are a helpful assistant that composes emails."},
                {"role": "user", "content": instructions + "\nFacts (JSON):\n" + json.dumps(facts, ensure_ascii=False)}
            ],
            'modalities': ['text'],
            'text': { 'format': 'plain' }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            # Extract text from responses API
            # It may return data['output'][0]['content'][0]['text'] depending on API; try common paths
            text = None
            try:
                text = data['output'][0]['content'][0]['text']
            except Exception:
                # fallback: choices like structure
                text = data.get('content', '') or data.get('output_text')
            if text and isinstance(text, str):
                return text.strip()
        else:
            # Non-200: try fallback
            pass
    except Exception:
        pass

    # Fallback to Chat Completions (plain text)
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        messages = [
            {"role": "system", "content": "You are a helpful assistant that composes emails."},
            {"role": "user", "content": instructions + "\nFacts (JSON):\n" + json.dumps(facts, ensure_ascii=False)}
        ]
        payload = {
            'model': model,
            'messages': messages,
            'temperature': 0.2
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data['choices'][0]['message']['content']
            if text:
                return text.strip()
    except Exception:
        pass

    return None
