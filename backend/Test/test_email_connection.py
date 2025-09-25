#!/usr/bin/env python3
"""
Script de test pour vérifier la connexion email
"""

import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# Configuration email (à ajuster avec vos paramètres)
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
EMAIL = "ilyesnajjarri@gmail.com"
PASSWORD = "vqbc ewty kbzy tyqb"  # Utilisez un mot de passe d'application


def test_imap_connection():
    """Test de la connexion IMAP pour lire les emails"""
    print("🔍 Test de connexion IMAP...")
    
    try:
        # Connexion au serveur IMAP
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        print("✅ Connexion SSL établie")
        
        # Tentative de login
        mail.login(EMAIL, PASSWORD)
        print("✅ Authentification réussie")
        
        # Sélection de la boîte de réception
        status, messages = mail.select("inbox")
        print(f"✅ Boîte de réception sélectionnée: {messages[0].decode()} messages")
        
        # Recherche des emails non lus
        status, messages = mail.search(None, '(UNSEEN)')
        email_ids = messages[0].split()
        print(f"📧 {len(email_ids)} emails non lus trouvés")
        
        # Test de lecture d'un email (s'il y en a)
        if email_ids:
            latest_email_id = email_ids[-1]
            status, data = mail.fetch(latest_email_id, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            print(f"📨 Dernier email non lu:")
            print(f"   De: {msg['From']}")
            print(f"   Objet: {msg['Subject']}")
            print(f"   Date: {msg['Date']}")
        
        # Fermeture de la connexion
        mail.close()
        mail.logout()
        print("✅ Connexion IMAP fermée proprement")
        return True
        
    except imaplib.IMAP4.error as e:
        print(f"❌ Erreur IMAP: {e}")
        if b'Application-specific password required' in str(e).encode():
            print("💡 Solution: Vous devez générer un mot de passe d'application Gmail")
            print("   1. Allez sur https://myaccount.google.com/security")
            print("   2. Activez la validation en 2 étapes")
            print("   3. Générez un mot de passe d'application pour 'Mail'")
        return False
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        return False


def test_smtp_connection():
    """Test de la connexion SMTP pour envoyer des emails"""
    print("\n📤 Test de connexion SMTP...")
    
    try:
        # Connexion au serveur SMTP
        server = smtplib.SMTP(SMTP_SERVER, 587)
        print("✅ Connexion SMTP établie")
        
        # Activation TLS
        server.starttls()
        print("✅ TLS activé")
        
        # Tentative de login
        server.login(EMAIL, PASSWORD)
        print("✅ Authentification SMTP réussie")
        
        # Fermeture de la connexion
        server.quit()
        print("✅ Connexion SMTP fermée proprement")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Erreur d'authentification SMTP: {e}")
        print("💡 Vérifiez votre mot de passe d'application")
        return False
    except Exception as e:
        print(f"❌ Erreur SMTP générale: {e}")
        return False


def test_email_parsing():
    """Test du parsing d'un email de test"""
    print("\n🔍 Test du parsing d'email...")
    
    # Email de test simulé
    test_email_content = """
    Bonjour,
    
    Je souhaite louer un véhicule pour mes vacances.
    
    Nom: Dupont
    Prénom: Jean
    Téléphone: 0123456789
    Ville: Casablanca
    Date de début: 2025-10-01
    Date de fin: 2025-10-07
    Type de véhicule: SUV
    
    Merci d'avance.
    
    Cordialement,
    Jean Dupont
    """
    
    try:
        # Test d'import du parser NLP
        from nlp_parser import extraire_infos
        print("✅ Module nlp_parser importé avec succès")
        
        # Test du parsing
        infos = extraire_infos(test_email_content)
        print("✅ Parsing réussi:")
        for key, value in infos.items():
            print(f"   {key}: {value}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import nlp_parser: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur de parsing: {e}")
        return False


def main():
    """Fonction principale de test"""
    print("🚗 Test de connexion du système de gestion des demandes de location")
    print("=" * 70)
    
    # Tests des connexions
    imap_ok = test_imap_connection()
    smtp_ok = test_smtp_connection()
    parsing_ok = test_email_parsing()
    
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS:")
    print(f"   IMAP (lecture emails):     {'✅ OK' if imap_ok else '❌ ÉCHEC'}")
    print(f"   SMTP (envoi emails):       {'✅ OK' if smtp_ok else '❌ ÉCHEC'}")
    print(f"   Parsing NLP:               {'✅ OK' if parsing_ok else '❌ ÉCHEC'}")
    
    if all([imap_ok, smtp_ok, parsing_ok]):
        print("\n🎉 Tous les tests sont réussis ! Votre système est prêt.")
    else:
        print("\n⚠️  Certains tests ont échoué. Vérifiez la configuration.")
    
    print("\n💡 PROCHAINES ÉTAPES:")
    if not imap_ok or not smtp_ok:
        print("   1. Configurez un mot de passe d'application Gmail")
        print("   2. Mettez à jour le PASSWORD dans email_fetcher.py")
    if parsing_ok:
        print("   3. Testez avec de vrais emails")
    print("   4. Lancez l'application Flask")
    print("   5. Testez l'interface web")


if __name__ == "__main__":
    main()
