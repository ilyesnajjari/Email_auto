#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour créer des données de test
"""
from db import conn

def create_test_data():
    c = conn.cursor()
    
    # Ajouter des sous-traitants de test
    sous_traitants = [
        ("Location Express", "express@email.com", "Casablanca"),
        ("Auto Rent", "autorent@email.com", "Rabat"),
        ("Car Services", "carservices@email.com", "Marrakech"),
        ("Speed Rent", "speedrent@email.com", "Casablanca"),
        ("Morocco Cars", "moroccocars@email.com", "Fès")
    ]
    
    print("🚀 Ajout des sous-traitants de test...")
    for nom, email, ville in sous_traitants:
        c.execute("""
            INSERT OR IGNORE INTO sous_traitants (nom, email, ville)
            VALUES (?, ?, ?)
        """, (nom, email, ville))
    
    # Ajouter des demandes de test
    demandes = [
        ("Dupont", "Marie", "0612345678", "Casablanca", "2025-10-01", "2025-10-05", "Voiture compacte"),
        ("Martin", "Pierre", "0623456789", "Rabat", "2025-10-10", "2025-10-15", "SUV"),
        ("Bernard", "Sophie", "0634567890", "Marrakech", "2025-10-20", "2025-10-25", "Berline"),
        ("Moreau", "Jean", "0645678901", "Casablanca", "2025-11-01", "2025-11-07", "Monospace"),
        ("Petit", "Claire", "0656789012", "Fès", "2025-11-15", "2025-11-20", "Citadine")
    ]
    
    print("📋 Ajout des demandes de test...")
    for nom, prenom, tel, ville, debut, fin, vehicule in demandes:
        c.execute("""
            INSERT INTO demandes (nom, prenom, telephone, ville, date_debut, date_fin, type_vehicule, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nom, prenom, tel, ville, debut, fin, vehicule, "en_attente"))
    
    conn.commit()
    
    # Vérifier les données créées
    c.execute("SELECT COUNT(*) FROM sous_traitants")
    nb_st = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM demandes")
    nb_demandes = c.fetchone()[0]
    
    print(f"✅ Données de test créées avec succès !")
    print(f"   - {nb_st} sous-traitants")
    print(f"   - {nb_demandes} demandes")
    
    return True

def show_test_data():
    c = conn.cursor()
    
    print("\n📊 DONNÉES DE TEST ACTUELLES:")
    print("=" * 50)
    
    # Afficher les sous-traitants
    print("\n👥 SOUS-TRAITANTS:")
    c.execute("SELECT * FROM sous_traitants")
    sous_traitants = c.fetchall()
    for st in sous_traitants:
        print(f"  • {st[1]} - {st[2]} ({st[3]})")
    
    # Afficher les demandes
    print("\n📋 DEMANDES:")
    c.execute("SELECT * FROM demandes")
    demandes = c.fetchall()
    for d in demandes:
        print(f"  • {d[2]} {d[1]} - {d[4]} ({d[5]} au {d[6]}) - {d[8]}")

def clear_test_data():
    """Supprimer toutes les données de test"""
    c = conn.cursor()
    c.execute("DELETE FROM demandes")
    c.execute("DELETE FROM sous_traitants")
    conn.commit()
    print("🗑️ Données de test supprimées")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "clear":
            clear_test_data()
        elif sys.argv[1] == "show":
            show_test_data()
    else:
        create_test_data()
        show_test_data()
