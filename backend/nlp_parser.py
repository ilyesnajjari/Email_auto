import spacy
import re
import unicodedata
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dateparser import parse
from dateparser.search import search_dates

try:
    from langdetect import detect as langdetect_detect
except Exception:  # langdetect facultatif
    langdetect_detect = None

try:
    from email_validator import validate_email, EmailNotValidError
except Exception:
    validate_email = None
    EmailNotValidError = Exception

# Modèles spaCy chargés à la demande pour éviter les erreurs si non installés
_NLP_CACHE: Dict[str, Optional[spacy.language.Language]] = {"fr": None, "en": None, "da": None}


def _load_spacy(lang: str) -> spacy.language.Language:
    if _NLP_CACHE.get(lang) is not None:
        return _NLP_CACHE[lang]  # type: ignore
    model_name = {
        "fr": "fr_core_news_sm",
        "en": "en_core_web_sm",
        "da": "da_core_news_sm",
    }.get(lang, "fr_core_news_sm")
    try:
        nlp = spacy.load(model_name)
    except Exception:
        # Fallback minimal si le modèle manque
        try:
            nlp = spacy.blank({"fr": "fr", "en": "en", "da": "da"}.get(lang, "fr"))
        except Exception:
            nlp = spacy.blank("xx")
    _NLP_CACHE[lang] = nlp
    return nlp


def _clean_city_name(val: str) -> str:
    """Nettoie une valeur de ville: coupe sur formules de politesse, sauts de ligne, et ponctuation."""
    if not val:
        return ""
    v = str(val)
    # couper aux formules de politesse fréquentes
    v = re.split(r"\b(cordialement|merci|bien\s*à\s*vous|salutations|regards|best\s*regards|thanks)\b", v, flags=re.IGNORECASE)[0]
    # couper à la première ligne
    v = v.split('\n')[0]
    # nettoyer ponctuation/espaces
    v = v.strip(" \t,;:.!\-_")
    return v


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    # uniformiser les tirets/fleches pour parcours
    text = text.replace("→", "->").replace("—", "-").replace("–", "-")
    # réduire espaces
    text = re.sub(r"[ \t\x0b\x0c\r]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_language(text: str) -> str:
    """Détecte FR/EN/DA via langdetect si dispo, sinon heuristique."""
    t = (text or "").strip()
    if not t:
        return "fr"
    if langdetect_detect:
        try:
            code = langdetect_detect(t)
            if code.startswith("fr"):
                return "fr"
            if code.startswith("en"):
                return "en"
            if code.startswith("da"):
                return "da"
        except Exception:
            pass
    # Heuristique simple en fallback
    french_words = ['bonjour', 'merci', 'voiture', 'location', 'réservation', 'demande', 'personnes']
    english_words = ['hello', 'thank', 'car', 'rental', 'booking', 'request', 'people']
    danish_words = ['hej', 'tak', 'bil', 'leje', 'booking']
    tl = t.lower()
    fr_c = sum(1 for w in french_words if w in tl)
    en_c = sum(1 for w in english_words if w in tl)
    da_c = sum(1 for w in danish_words if w in tl)
    if fr_c >= en_c and fr_c >= da_c:
        return 'fr'
    if en_c >= da_c:
        return 'en'
    return 'da'


def extract_email(text: str) -> str:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if not m:
        return ""
    addr = m.group(0)
    if validate_email:
        try:
            return validate_email(addr, check_deliverability=False).email
        except EmailNotValidError:
            return addr
    return addr


def normalize_phone(raw: str) -> str:
    # Conserver + et chiffres
    digits = re.sub(r"[^0-9+]", "", raw)
    # Simplifier ++ et formats bizarres
    digits = re.sub(r"\+{2,}", "+", digits)
    return digits


def extract_phone(text: str) -> str:
    # Capte diverses formes: +33 6 12 34 56 78, 06-12-34-56-78, +45 12 34 56 78
    pattern = r"(\+?\d{1,3}[\s.-]?)?(\d[\d\s.-]{7,14})"
    for m in re.finditer(pattern, text):
        candidate = m.group(0)
        cand_norm = normalize_phone(candidate)
        if len(re.sub(r"\D", "", cand_norm)) >= 8:
            return cand_norm
    return ""


WORD_NUM_FR = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11,
    "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16,
}
WORD_NUM_EN = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16,
}


def extract_nb_personnes(text: str) -> str:
    # 1) Expressions directes
    direct_patterns = [
        r"(?:\bfor|pour)\s+(\d{1,3})\s+(?:people|persons|personnes|personne|passagers|pax)",
        r"\b(\d{1,3})\s*(?:personnes|personne|people|voyageurs|participants|coaches|boys|passagers|pax)\b",
        r"There will be\s+(\d{1,3})\s+of us",
        r"\b(\d{1,3})\s*x\s*(?:people|personnes|pax)\b",
        r"\bgroup of\s*(\d{1,3})\b",
        r"\b(\d{1,3})\s*(?:adults|adultes)\b",
        r"\b(\d{1,3})\s*(?:children|kids|enfants)\b",
    ]
    for rgx in direct_patterns:
        m = re.search(rgx, text, re.IGNORECASE)
        if m:
            return m.group(1)

    # 2) Nombres en lettres FR/EN
    tl = text.lower()
    for w, n in {**WORD_NUM_FR, **WORD_NUM_EN}.items():
        if re.search(fr"\b{re.escape(w)}\b\s+(?:personnes|people|passagers)", tl):
            return str(n)

    # 3) Intervalles 20-30 personnes -> 20-30
    m = re.search(r"(\d{1,3})\s*[-àto]{1,2}\s*(\d{1,3})\s*(?:personnes|people|pax)", tl)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return ""


def parse_dates_block(text: str) -> Tuple[str, str]:
    """Extrait (date_debut, date_fin) au format YYYY-MM-DD.
    Utilise d'abord patterns explicites de périodes, puis search_dates comme fallback.
    """
    t = text
    current_year = datetime.now().year

    # Injecter l'année courante quand elle est omise (ex: 12/10 -> 12/10/2025)
    def _inject_year_ymd(s: str) -> str:
        # dd/mm or dd-mm or dd.mm without trailing year
        def repl(m):
            d, mth, sep = m.group(1), m.group(2), m.group(3)
            return f"{d}{sep}{mth}{sep}{current_year}"
        s = re.sub(r"\b(\d{1,2})([\/\-.])(\d{1,2})(?![\/\-.]\d{2,4})\b", lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(2)}{current_year}", s)
        # 12 Oct/Octobre sans année -> ajouter année
        months = [
            'jan', 'janv', 'janvier', 'feb', 'fev', 'févr', 'février', 'february', 'march', 'mars', 'apr', 'avr', 'avril', 'april',
            'may', 'mai', 'jun', 'juin', 'june', 'jul', 'juillet', 'july', 'aug', 'août', 'aout', 'august', 'sep', 'sept', 'septembre',
            'oct', 'octobre', 'october', 'nov', 'novembre', 'november', 'dec', 'déc', 'décembre', 'december',
            # NL/DA short
            'januar', 'januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'december',
            'januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december'
        ]
        month_re = r"(" + "|".join(sorted(set(months), key=len, reverse=True)) + r")"
        # 12 Oct -> 12 Oct 2025
        s = re.sub(fr"\b(\d{{1,2}})\s+{month_re}\b(?!\s*\d{{2,4}})", lambda m: f"{m.group(1)} {m.group(2)} {current_year}", s, flags=re.IGNORECASE)
        # Oct 12 -> Oct 12 2025
        s = re.sub(fr"\b{month_re}\s+(\d{{1,2}})\b(?!\s*\d{{2,4}})", lambda m: f"{m.group(1)} {m.group(2)} {current_year}", s, flags=re.IGNORECASE)
        return s

    t_inj = _inject_year_ymd(t)

    # 0) Expressions relatives: "la semaine prochaine à partir de lundi", "next monday", "à partir de lundi"
    days_fr = {"lundi":0, "mardi":1, "mercredi":2, "jeudi":3, "vendredi":4, "samedi":5, "dimanche":6}
    days_en = {"monday":0, "tuesday":1, "wednesday":2, "thursday":3, "friday":4, "saturday":5, "sunday":6}

    def _next_weekday(base: datetime, weekday: int) -> datetime:
        # next occurrence on/after base
        days_ahead = (weekday - base.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        return base + timedelta(days=days_ahead)

    tl = t.lower()
    # semaine prochaine + jour
    m_rel = re.search(r"semaine\s+prochaine.*?\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b", tl)
    if m_rel:
        wd = days_fr[m_rel.group(1)]
        base = datetime.now() + timedelta(days=7)
        base = base.replace(hour=0, minute=0, second=0, microsecond=0)
        # find the target weekday in/after next week baseline
        start_dt = base + timedelta(days=(wd - base.weekday()) % 7)
        return start_dt.strftime('%Y-%m-%d'), ""

    # "next monday" (EN)
    m_rel_en = re.search(r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", tl)
    if m_rel_en:
        wd = days_en[m_rel_en.group(1)]
        base = datetime.now()
        start_dt = _next_weekday(base, wd)
        return start_dt.strftime('%Y-%m-%d'), ""

    # "à partir de lundi"
    m_from = re.search(r"\b(?:a|à)\s*partir\s*de\s*(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b", tl)
    if m_from:
        wd = days_fr[m_from.group(1)]
        base = datetime.now()
        start_dt = _next_weekday(base, wd)
        return start_dt.strftime('%Y-%m-%d'), ""
    # Périodes explicites: du 12/10 au 15/10, from 1 Nov to 3 Nov
    period_patterns = [
        r"(?:du|from|van)\s+([^\n;]+?)\s+(?:au|to|till|until|tot)\s+([^\n;]+)",
        r"(\d{1,2}[\/.\-]\d{1,2}(?:[\/.\-]\d{2,4})?)\s*(?:au|to|-)\s*(\d{1,2}[\/.\-]\d{1,2}(?:[\/.\-]\d{2,4})?)",
    ]
    for rgx in period_patterns:
        m = re.search(rgx, t, re.IGNORECASE)
        if m:
            start_raw, end_raw = m.group(1), m.group(2)
            start_raw = _inject_year_ymd(start_raw)
            end_raw = _inject_year_ymd(end_raw)
            s = parse(start_raw, languages=['fr', 'en', 'da', 'nl'], settings={"PREFER_DAY_OF_MONTH": "first", "RELATIVE_BASE": datetime.now()})
            e = parse(end_raw, languages=['fr', 'en', 'da', 'nl'], settings={"PREFER_DAY_OF_MONTH": "last", "RELATIVE_BASE": datetime.now()})
            if s and e:
                return s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d')

    # Fallback: chercher toutes les dates, garder fenêtre la plus plausible (préférez futur)
    found = search_dates(t_inj, languages=['fr', 'en', 'da', 'nl'], settings={"RETURN_AS_TIMEZONE_AWARE": False, "RELATIVE_BASE": datetime.now()})
    if found:
        today = datetime.now().date()
        dates = sorted([d[1].date() for d in found])
        # garder seulement >= aujourd'hui si dispo, sinon original
        future = [d for d in dates if d >= today]
        chosen = future if future else dates
        if chosen:
            start = chosen[0].strftime('%Y-%m-%d')
            end = chosen[-1].strftime('%Y-%m-%d') if len(chosen) > 1 else ""
            return start, end
    return "", ""


CITY_COUNTRY_MAP = {
    # Common cities
    "paris": "France", "lyon": "France", "marseille": "France",
    "london": "United Kingdom", "londres": "United Kingdom",
    "bruxelles": "Belgium", "brussels": "Belgium",
    "amsterdam": "Netherlands", "rotterdam": "Netherlands",
    "københavn": "Denmark", "copenhagen": "Denmark",
    "madrid": "Spain", "barcelona": "Spain",
    "rome": "Italy", "milano": "Italy", "milan": "Italy",
    "berlin": "Germany", "munich": "Germany", "münchen": "Germany",
}

PHONE_CODE_COUNTRY = {
    '+33': 'France', '+44': 'United Kingdom', '+32': 'Belgium', '+31': 'Netherlands', '+34': 'Spain', '+39': 'Italy',
    '+49': 'Germany', '+45': 'Denmark', '+41': 'Switzerland', '+352': 'Luxembourg', '+351': 'Portugal'
}

def extract_places(text: str, doc: spacy.language.Language) -> Tuple[str, List[str], str, str]:
    """Retourne (ville_principale, villes, pays, itineraire) où itineraire peut être 'A->B'."""
    villes: List[str] = []
    pays = ""
    itinerary = ""

    # Champs étiquetés
    labeled_patterns = [
        r"(?:Ville\s*(?:de)?\s*départ|Départ|From|Pickup|Vertrekstad)\s*[:\-]?\s*([A-Za-zÀ-ÿ'\- ]+)",
        r"(?:Ville\s*(?:d')?arriv[ée]e|Arrivée|To|Dropoff|Aankomststad)\s*[:\-]?\s*([A-Za-zÀ-ÿ'\- ]+)",
        r"(?:Ville|City|Lieu)\s*[:\-]?\s*([A-Za-zÀ-ÿ'\- ]+)",
    ]
    for rgx in labeled_patterns:
        for m in re.finditer(rgx, text, re.IGNORECASE):
            val = _clean_city_name(m.group(1).strip())
            if val and val not in villes:
                villes.append(val)

    # Itinéraire A -> B
    m = re.search(r"([A-Za-zÀ-ÿ'\- ]{2,})\s*(?:->|to|vers|\-)\s*([A-Za-zÀ-ÿ'\- ]{2,})", text, re.IGNORECASE)
    if m:
        a, b = _clean_city_name(m.group(1).strip()), _clean_city_name(m.group(2).strip())
        itinerary = f"{a}->{b}"
        for v in (a, b):
            if v and v not in villes:
                villes.append(v)

    # NER spaCy
    for ent in doc.ents:
        if ent.label_ in ("LOC", "GPE"):
            v = _clean_city_name(ent.text.strip())
            if v and v not in villes:
                villes.append(v)

    # Pays
    pm = re.search(r"(?:Pays|Country)\s*[:\-]?\s*([A-Za-zÀ-ÿ'\- ]+)", text, re.IGNORECASE)
    if pm:
        pays = pm.group(1).strip()

    # Heuristique: ville primaire = première ville plausible (exclure lieux non villes basiques)
    def _plausible_city(name: str) -> bool:
        # Exclure termes comme "aéroport", "gare", "hôtel"
        lower = name.lower()
        banned = ['airport', 'aéroport', 'gare', 'station', 'hotel', 'hôtel', 'venue', 'centre', 'center']
        return all(w not in lower for w in banned) and len(lower) >= 2

    villes = [v for v in villes if _plausible_city(v)]
    ville = villes[0] if villes else ""

    # Pays déduit de la ville, sinon via indicatif téléphonique, sinon vide
    if not pays and ville:
        pays = CITY_COUNTRY_MAP.get(ville.lower(), "")
    if not pays:
        tel = extract_phone(text)
        if tel.startswith('+'):
            for code, cname in PHONE_CODE_COUNTRY.items():
                if tel.startswith(code):
                    pays = cname
                    break

    return ville, villes, pays, itinerary


def extract_vehicle(text: str) -> str:
    vocab = [
        # FR
        "bus", "autocar", "minibus", "voiture", "van", "minivan", "minibus", "suv",
        # EN
        "car", "coach", "bus", "minibus", "van", "minivan", "suv",
        # DA/NL keywords
        "bil", "lastbil", "bus", "minibus",
    ]
    t = text.lower()
    for v in vocab:
        if v in t:
            return v
    return ""


def extract_trip_type(text: str) -> str:
    patterns = [
        (r"aller\s*retour|aller-retour|a/r|ar|retourreis|heen en terug|round\s*trip", "aller-retour"),
        (r"aller\s*simple|one\s*way|one-way", "aller simple"),
    ]
    for rgx, label in patterns:
        if re.search(rgx, text, re.IGNORECASE):
            return label
    return ""


def extract_name(doc: spacy.language.Language, text: str) -> Tuple[str, str]:
    nom, prenom = "", ""
    nom_patterns = [
        r"(?:Naam|Nom|Name)\s*[:\-]?\s*([A-Za-zÀ-ÿ'\- ]+)",
        r"(?:Je m'appelle|My name is|Mijn naam is|Mon nom est)\s+([A-Za-zÀ-ÿ'\- ]+)",
    ]
    for rgx in nom_patterns:
        m = re.search(rgx, text, re.IGNORECASE)
        if m:
            parts = m.group(1).split()
            if len(parts) > 1:
                prenom, nom = parts[0], parts[-1]
            else:
                nom = parts[0]
            return nom, prenom
    personnes = [ent.text for ent in doc.ents if ent.label_ in ("PER", "PERSON")]
    if personnes:
        parts = personnes[0].split()
        prenom, nom = (parts[0], parts[-1]) if len(parts) > 1 else ("", parts[0])
    return nom, prenom


def extraire_infos(email_text: str) -> List[Dict[str, str]]:
    """Analyse multi-langues (FR, EN, NL, DA), multi-blocs et retourne une liste de demandes structurées

    Champs retournés minimum (compatibles existants):
    - nom, prenom, email, telephone, ville, villes, pays,
    - date_debut, date_fin, type_vehicule, type_voyage, nb_personnes,
    - infos_libres, corps_mail, langue_detectee
    + Extras non bloquants: itinerary
    """
    text = clean_text(email_text or "")
    # Si le texte provient d'un tableau HTML transformé, on peut avoir des lignes "Label | Valeur"
    # Essayons d'aplatir les lignes en clés/valeurs pour enrichir le bloc avant extraction
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    kv_map: Dict[str, str] = {}
    for ln in lines:
        # Forme 1: Label | Valeur | (+ éventuel reste)
        if '|' in ln:
            parts = [p.strip() for p in ln.split('|') if p.strip()]
            if len(parts) >= 2 and len(parts[0]) <= 40:  # plausible label
                kv_map[parts[0].lower()] = parts[1]
                continue
        # Forme 2: Label: Valeur
        m = re.match(r"^([A-Za-zÀ-ÿ' \-]{2,40})\s*[:\-]\s*(.+)$", ln)
        if m:
            kv_map[m.group(1).lower()] = m.group(2).strip()
    # Construire un texte enrichi avec les alias multi-langues pour aider les regex
    alias_pairs = []  # list of normalized "Key: Value" lines
    def add_aliases(label: str, value: str):
        if not value:
            return
        alias_pairs.append(f"{label}: {value}")
    for k, v in kv_map.items():
        kl = k.lower()
        # Email
        if any(w in kl for w in ["email", "e-mail", "mail", "courriel"]):
            add_aliases("Email", v)
        # Nom/Name/Naam
        if any(w in kl for w in ["nom", "name", "naam"]):
            add_aliases("Nom", v)
        # Téléphone/Phone
        if any(w in kl for w in ["téléphone", "telephone", "tel", "phone", "tlf", "tlf.", "telefon"]):
            add_aliases("Telephone", v)
        # Départ/From/Vertrekstad
        if any(w in kl for w in ["départ", "depart", "from", "pickup", "vertrek", "vertrekstad", "pickup city", "pickup location", "abfahrt", "startort"]):
            add_aliases("Départ", v)
        # Arrivée/To/Aankomststad
        if any(w in kl for w in ["arriv", "to", "dropoff", "aankomst", "aankomststad", "destination", "ankunft", "zielort"]):
            add_aliases("Arrivée", v)
        # Ville/City
        if any(w in kl for w in ["ville", "city", "lieu", "plaats"]):
            add_aliases("Ville", v)
        # Dates: départ/retour
        if any(w in kl for w in ["date de départ", "départ le", "vertrekdatum", "start date", "from date", "datum vertrek", "startdatum", "abfahrtsdatum"]):
            add_aliases("Date de départ", v)
        if any(w in kl for w in ["date de retour", "retour", "terugkeer", "return date", "einddatum", "end date", "datum terugkeer", "rückreisedatum", "rueckreisedatum"]):
            add_aliases("Date de retour", v)
        # Nb personnes
        if any(w in kl for w in ["personnes", "pax", "people", "participants", "voyageurs", "passagers", "personen", "personen"]):
            add_aliases("Personnes", v)
        # Type de véhicule
        if any(w in kl for w in ["véhicule", "vehicule", "vehicle", "fahrzeug", "voiture", "bus", "autocar", "coach", "van", "minibus", "suv"]):
            add_aliases("Véhicule", v)
        # Aller/retour
        if any(w in kl for w in ["aller", "retour", "round", "one-way", "one way", "retourreis", "heen en terug", "hin und rück", "hin-und-rück", "einfache fahrt"]):
            add_aliases("Type voyage", v)

    if alias_pairs:
        text = text + "\n\n" + "\n".join(alias_pairs)
    # Séparer par doubles sauts de ligne mais conserver blocs raisonnables
    blocs = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    demandes: List[Dict[str, str]] = []

    for bloc in blocs:
        langue = detect_language(bloc)
        nlp = _load_spacy(langue)
        doc = nlp(bloc)

        # Nom/prénom
        nom, prenom = extract_name(doc, bloc)
        # Email
        email = extract_email(bloc)
        # Téléphone
        telephone = extract_phone(bloc)
        # Nb personnes
        nb_personnes = extract_nb_personnes(bloc)
        # Dates
        date_debut, date_fin = parse_dates_block(bloc)
        # Lieux
        ville, villes, pays, itinerary = extract_places(bloc, doc)
        # Type de véhicule
        type_vehicule = extract_vehicle(bloc)
        # Type de voyage
        type_voyage = extract_trip_type(bloc)

        demandes.append({
            "nom": nom,
            "prenom": prenom,
            "email": email,
            "telephone": telephone,
            "ville": ville,
            "villes": villes,
            "pays": pays,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "type_vehicule": type_vehicule,
            "type_voyage": type_voyage,
            "nb_personnes": nb_personnes,
            "infos_libres": bloc,
            "corps_mail": bloc,
            "langue_detectee": langue,
            "itinerary": itinerary,
        })

    return demandes
