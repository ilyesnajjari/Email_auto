import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [demandes, setDemandes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState({ ville: '', date: '' })

  // Fonction pour récupérer les demandes
  const fetchDemandes = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:5001/demandes')
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération des demandes')
      }
      const data = await response.json()
      setDemandes(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Fonction pour valider une demande
  const validerDemande = async (id) => {
    try {
      const response = await fetch(`http://localhost:5001/demandes/valider/${id}`, {
        method: 'POST'
      })
      if (!response.ok) {
        throw new Error('Erreur lors de la validation')
      }
      // Recharger les demandes après validation
      fetchDemandes()
      alert('Demande validée et emails envoyés aux sous-traitants!')
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  // Fonction pour récupérer les emails
  const fetchEmails = async () => {
    try {
      const response = await fetch('http://localhost:5001/fetch_emails', {
        method: 'POST'
      })
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération des emails')
      }
      // Recharger les demandes après récupération
      fetchDemandes()
      alert('Emails récupérés et analysés avec succès!')
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  // Charger les demandes au montage du composant
  useEffect(() => {
    fetchDemandes()
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>🚗 Dashboard Demandes de Location</h1>
        <p>Système de gestion automatisé des demandes de location de véhicules</p>
        
        <div className="actions">
          <button onClick={fetchEmails} className="btn btn-primary">
            📧 Récupérer les emails
          </button>
          <button onClick={fetchDemandes} className="btn btn-secondary">
            🔄 Actualiser
          </button>
        </div>
      </header>

      <main className="app-main">
        {/* Filtres */}
        <div className="filters">
          <input
            type="text"
            placeholder="Filtrer par ville..."
            value={filter.ville}
            onChange={(e) => setFilter({...filter, ville: e.target.value})}
            className="filter-input"
          />
          <input
            type="date"
            value={filter.date}
            onChange={(e) => setFilter({...filter, date: e.target.value})}
            className="filter-input"
          />
        </div>

        {/* Contenu principal */}
        {loading && <div className="loading">Chargement des demandes...</div>}
        {error && <div className="error">Erreur: {error}</div>}
        
        {!loading && !error && (
          <div className="demandes-container">
            <h2>Demandes de location ({demandes.length})</h2>
            
            {demandes.length === 0 ? (
              <div className="empty-state">
                <p>Aucune demande trouvée.</p>
                <p>Cliquez sur "Récupérer les emails" pour analyser les nouveaux emails.</p>
              </div>
            ) : (
              <div className="demandes-grid">
                {demandes
                  .filter(demande => 
                    (!filter.ville || demande.ville?.toLowerCase().includes(filter.ville.toLowerCase())) &&
                    (!filter.date || (demande.date_debut <= filter.date && demande.date_fin >= filter.date))
                  )
                  .map(demande => (
                    <div key={demande.id} className={`demande-card ${demande.statut}`}>
                      <div className="demande-header">
                        <h3>{demande.prenom} {demande.nom}</h3>
                        <span className={`status ${demande.statut}`}>
                          {demande.statut === 'en_attente' ? '⏳ En attente' : 
                           demande.statut === 'validee' ? '✅ Validée' : 
                           demande.statut}
                        </span>
                      </div>
                      
                      <div className="demande-details">
                        <p><strong>📞 Téléphone:</strong> {demande.telephone}</p>
                        <p><strong>🏙️ Ville:</strong> {demande.ville}</p>
                        <p><strong>📅 Période:</strong> {demande.date_debut} au {demande.date_fin}</p>
                        <p><strong>🚗 Véhicule:</strong> {demande.type_vehicule}</p>
                        {demande.sous_traitant && (
                          <p><strong>👤 Sous-traitant:</strong> {demande.sous_traitant}</p>
                        )}
                      </div>
                      
                      {demande.statut === 'en_attente' && (
                        <div className="demande-actions">
                          <button 
                            onClick={() => validerDemande(demande.id)}
                            className="btn btn-success"
                          >
                            ✅ Valider la demande
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>&copy; 2025 Système de Gestion de Location - Automatisation des emails</p>
      </footer>
    </div>
  )
}

export default App
