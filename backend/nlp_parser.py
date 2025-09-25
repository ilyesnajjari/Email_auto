import spacy
import re
from dateparser import parse

# Charger le modèle français
nlp_fr = spacy.load("fr_core_news_sm")

# Charger le modèle anglais
nlp_en = spacy.load("en_core_web_sm")

# Charger le modèle danois
nlp_da = spacy.load("da_core_news_sm")

def detect_language(text):
    """Détecte la langue du texte pour choisir le bon modèle NLP"""
    # Simple heuristique basée sur des mots-clés
    french_words = ['bonjour', 'merci', 'voiture', 'location', 'réservation', 'demande']
    english_words = ['hello', 'thank', 'car', 'rental', 'booking', 'request']
    danish_words = ['hej', 'tak', 'bil', 'leje', 'booking']
    
    text_lower = text.lower()
    
    french_count = sum(1 for word in french_words if word in text_lower)
    english_count = sum(1 for word in english_words if word in text_lower)
    danish_count = sum(1 for word in danish_words if word in text_lower)
    
    if french_count >= english_count and french_count >= danish_count:
        return 'fr'
    elif english_count >= danish_count:
        return 'en'
    else:
        return 'da'

def extraire_infos(email_text):
    # Détecter la langue et choisir le bon modèle
    langue = detect_language(email_text)
    if langue == 'en':
        doc = nlp_en(email_text)
    elif langue == 'da':
        doc = nlp_da(email_text)
    else:
        doc = nlp_fr(email_text)
    
    # Nom et prénom
    nom_prenom = [ent.text for ent in doc.ents if ent.label_ == "PER"]
    nom, prenom = (nom_prenom[0].split() + ["", ""])[:2] if nom_prenom else ("", "")
    
    # Ville et pays
    locations = [ent.text for ent in doc.ents if ent.label_ == "LOC"]
    ville = ""
    pays = ""
    
    # Liste des pays courants
    pays_liste = ["France", "Danemark", "Denmark", "Angleterre", "England", "Belgique", "Belgium", 
                  "Allemagne", "Germany", "Espagne", "Spain", "Italie", "Italy"]
    
    for loc in locations:
        if any(p.lower() in loc.lower() for p in pays_liste):
            pays = loc
        else:
            ville = loc if not ville else ville
    
    # Si pas de pays détecté, essayer de deviner par la langue
    if not pays:
        if langue == 'fr':
            pays = "France"
        elif langue == 'en':
            pays = "Angleterre"
        elif langue == 'da':
            pays = "Danemark"
    
    # Téléphone (formats internationaux)
    telephone_patterns = [
        r"\b\+?\d{1,3}[-.\s]?\d{8,10}\b",  # Format international
        r"\b\d{10}\b",  # Format français
        r"\b\d{2}[-.\s]\d{2}[-.\s]\d{2}[-.\s]\d{2}[-.\s]\d{2}\b"  # Format avec séparateurs
    ]
    
    telephone = ""
    for pattern in telephone_patterns:
        match = re.search(pattern, email_text)
        if match:
            telephone = match.group()
            break
    
    # Dates améliorées avec différents formats
    import datetime
    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # 01/02/2024
        r"\b\d{1,2}\s+[a-zéû]+\s+\d{2,4}\b",   # 1 janvier 2024
        r"\b[a-zéû]+\s+\d{1,2},?\s+\d{2,4}\b"  # janvier 1, 2024
    ]
    
    dates_trouvees = []
    for pattern in date_patterns:
        matches = re.findall(pattern, email_text, re.IGNORECASE)
        for match in matches:
            parsed_date = parse(match, languages=['fr', 'en', 'da'])
            if parsed_date:
                dates_trouvees.append(parsed_date)
    
    # Trier les dates
    dates_trouvees.sort()
    
    date_debut = dates_trouvees[0].strftime('%Y-%m-%d') if dates_trouvees else ""
    date_fin = dates_trouvees[1].strftime('%Y-%m-%d') if len(dates_trouvees) > 1 else ""
    date_voyage = date_debut  # Date de voyage = date de début
    
    # Type de véhicule multilingue
    vehicules_fr = ["voiture", "van", "camionette", "SUV", "berline", "citadine"]
    vehicules_en = ["car", "van", "truck", "SUV", "sedan", "hatchback"]
    vehicules_da = ["bil", "van", "lastbil", "SUV"]
    
    all_vehicules = vehicules_fr + vehicules_en + vehicules_da
    type_vehicule = next((v for v in all_vehicules if v.lower() in email_text.lower()), "")
    
    return {
        "nom": nom,
        "prenom": prenom, 
        "telephone": telephone,
        "ville": ville,
        "pays": pays,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "date_voyage": date_voyage,
        "type_vehicule": type_vehicule,
        "langue_detectee": langue
    }
