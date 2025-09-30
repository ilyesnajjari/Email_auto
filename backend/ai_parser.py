import os
import json
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()

def _build_prompt(email_text: str) -> str:
    return (
        "You are an information extraction assistant for ground transport bookings. Extract details precisely. "
        "Return STRICT JSON with an array named 'demandes'. Each item must contain these keys: "
        "nom, prenom, email, telephone, ville, villes (array), pays, date_debut (YYYY-MM-DD or ''), date_fin (YYYY-MM-DD or ''), "
        "type_vehicule, type_voyage, nb_personnes, infos_libres, corps_mail, langue_detectee, itinerary. "
        "Rules: "
        "1) ville: pick the single primary city of service (the city where the customer wants to rent the vehicle). Do not return venues or landmarks. "
        "2) villes: include other mentioned cities, but do not add venues/addresses. "
        "3) pays: deduce from the primary city (use common knowledge, e.g., Paris->France, London->United Kingdom, København->Denmark). If unsure, use phone country code to infer. "
    "4) dates: interpret as travel dates; if a year is missing, assume the current year. Prefer the next future date(s) relative to today. Normalize to YYYY-MM-DD; if only one day, put date_debut and leave date_fin empty. "
        "   Accept formats like DD-MM-YYYY, YYYY-MM-DD, MM-DD-YYYY, and entries with time (e.g., '27-09-2025 17:30'). "
        "5) nb_personnes: robustly capture passengers/group size (people, pax, passengers, participants, adults/children if total is provided). Return just the number or range (e.g., '10-20'). "
        "6) itinerary: only A->B city-to-city. If addresses are present (street, postcode, country), reduce them to the city names for the itinerary and to populate 'ville' and 'villes'. "
        "7) If a field is unknown, return empty string or empty array. Use the input language for detection labels. "
        "8) The input may be an HTML table or quote with label/value rows. Interpret lines like 'Label | Value' or 'Label: Value' "
        "   as potential fields (e.g., Email, Nom/Name/Naam, Départ/From/Vertrekstad, Arrivée/To/Aankomststad, "
        "   Date de départ/Vertrekdatum, Date de retour/Terugkeer, Personnes/PAX, Véhicule, Type de voyage). "
        "9) If the input is a form-like structure with labels in Dutch (NL), map them as follows: "
        "   - 'Naam' -> prenom/nom (split on first/last token if possible), 'E-mailadres' -> email, "
        "     'Vertrekstad' -> ville (primary), 'Aankomststad' -> include in 'villes', "
        "     'Vertrekdatum' -> date_debut, 'Terugkeerdatum' -> date_fin, "
        "     'Hoeveel reizigers nemen deel aan deze reis?' -> nb_personnes (support ranges like '10 - 20'), "
        "     'Voor wat voor type reis wilt u een offerte?' -> type_voyage (e.g., 'Retourreis (Heen en terug)' -> 'retour'). "
        "   Also capture any free-text details under additional info into 'infos_libres' and 'corps_mail'. "
        "10) Keep 'type_vehicule' empty unless a vehicle type is explicitly stated.\n\n"
        "Input email text:\n\n" + email_text
    )

def _parse_json_strict(s: str) -> Dict:
    # Attempt to find the first and last curly braces and parse JSON
    try:
        start = s.find('{')
        end = s.rfind('}')
        if start != -1 and end != -1 and end > start:
            s = s[start:end+1]
        return json.loads(s)
    except Exception:
        # Fallback minimal structure
        return {"demandes": []}


def extraire_infos_ai(email_text: str) -> List[Dict[str, str]]:
    # Read key dynamically at call time in case it was loaded after import
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_TOKEN")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")

    try:
        # Prefer the OpenAI Responses API; on error, fall back to Chat Completions for compatibility
        import requests

        def call_responses(prompt: str) -> str:
            url = "https://api.openai.com/v1/responses"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
                # Some deployments require this beta header for responses
                "OpenAI-Beta": "assistants=v2",
            }
            body = {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "input": prompt,
                "temperature": 0.0,
                "max_output_tokens": 800,
                "modalities": ["text"],
                "text": {"format": "json_object"}
            }
            r = requests.post(url, headers=headers, json=body, timeout=30)
            if r.status_code >= 400:
                # surface detailed server message to logs
                try:
                    print(f"[DEBUG] Responses API error {r.status_code}: {r.text[:1000]}")
                except Exception:
                    pass
                r.raise_for_status()
            data = r.json()
            return (
                data.get("output_text")
                or (data.get("output") and len(data["output"]) and data["output"][0].get("content") and len(data["output"][0]["content"]) and data["output"][0]["content"][0].get("text"))
                or "{}"
            )

        def call_chat(prompt: str) -> str:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            body = {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "temperature": 0.0,
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You are a helpful JSON-only information extraction assistant."},
                    {"role": "user", "content": prompt}
                ]
            }
            r = requests.post(url, headers=headers, json=body, timeout=30)
            if r.status_code >= 400:
                try:
                    print(f"[DEBUG] Chat API error {r.status_code}: {r.text[:1000]}")
                except Exception:
                    pass
                r.raise_for_status()
            data = r.json()
            # Chat returns in choices[0].message.content
            choices = data.get("choices") or []
            if choices and choices[0].get("message"):
                return choices[0]["message"].get("content", "{}")
            return "{}"

        prompt = _build_prompt(email_text)
        try:
            text = call_responses(prompt)
        except Exception:
            # Fallback to Chat Completions
            text = call_chat(prompt)

        obj = _parse_json_strict(text)
        demandes = obj.get("demandes") or []

        # Normalize structures and ensure keys exist
        normalized: List[Dict[str, str]] = []
        for d in demandes:
            normalized.append({
                "nom": d.get("nom", ""),
                "prenom": d.get("prenom", ""),
                "email": d.get("email", ""),
                "telephone": d.get("telephone", ""),
                "ville": d.get("ville", ""),
                "villes": d.get("villes", []) or [],
                "pays": d.get("pays", ""),
                "date_debut": d.get("date_debut", ""),
                "date_fin": d.get("date_fin", ""),
                "type_vehicule": d.get("type_vehicule", ""),
                "type_voyage": d.get("type_voyage", ""),
                "nb_personnes": d.get("nb_personnes", ""),
                "infos_libres": d.get("infos_libres", email_text),
                "corps_mail": d.get("corps_mail", email_text),
                "langue_detectee": d.get("langue_detectee", ""),
                "itinerary": d.get("itinerary", ""),
            })
        if not normalized:
            # Guarantee at least one entry with raw content
            normalized = [{
                "nom": "", "prenom": "", "email": "", "telephone": "",
                "ville": "", "villes": [], "pays": "",
                "date_debut": "", "date_fin": "",
                "type_vehicule": "", "type_voyage": "",
                "nb_personnes": "", "infos_libres": email_text, "corps_mail": email_text,
                "langue_detectee": "", "itinerary": "",
            }]
        return normalized
    except Exception as e:
        print(f"[WARN] AI parsing failed, falling back to NLP: {e}")
        # Signal caller to fallback to classic NLP
        raise
