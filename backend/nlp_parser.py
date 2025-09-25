import spacy, re
from dateparser import parse

nlp = spacy.load("fr_core_news_sm")

def extraire_infos(email_text):
    doc = nlp(email_text)
    
    # Nom et prénom
    nom_prenom = [ent.text for ent in doc.ents if ent.label_ == "PER"]
    nom, prenom = (nom_prenom[0].split() + ["", ""])[:2] if nom_prenom else ("", "")
    
    # Ville
    ville = [ent.text for ent in doc.ents if ent.label_ == "LOC"]
    ville = ville[0] if ville else ""
    
    # Téléphone
    telephone = re.search(r"\b\d{10}\b", email_text)
    telephone = telephone.group() if telephone else ""
    
    # Date (simple, à améliorer selon les formats)
    dates = [parse(s) for s in re.findall(r"\d{1,2} [a-zéû]+", email_text)]
    date_debut = dates[0].isoformat() if dates else ""
    date_fin = dates[1].isoformat() if len(dates) > 1 else ""
    
    # Type de véhicule (exemple)
    vehicules = ["voiture", "van", "camionette", "SUV"]
    type_vehicule = next((v for v in vehicules if v.lower() in email_text.lower()), "")
    
    return {
        "nom": nom,
        "prenom": prenom,
        "telephone": telephone,
        "ville": ville,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "type_vehicule": type_vehicule
    }
