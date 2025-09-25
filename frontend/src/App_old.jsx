import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [demandes, setDemandes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState({ ville: '', date: '' })
  const [activeTab, setActiveTab] = useState('demandes')
  const [historique, setHistorique] = useState([])
  const [stats, setStats] = useState(null)

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

  // Fonction pour supprimer une demande
  const supprimerDemande = async (id) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette demande ?')) {
      return
    }
    try {
      const response = await fetch(`http://localhost:5001/demandes/${id}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error('Erreur lors de la suppression')
      }
      // Recharger les demandes après suppression
      fetchDemandes()
      alert('Demande supprimée avec succès!')
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  // Fonction pour récupérer l'historique
  const fetchHistorique = async () => {
    try {
      const response = await fetch('http://localhost:5001/historique')
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération de l\'historique')
      }
      const data = await response.json()
      setHistorique(data)
    } catch (err) {
      setError(err.message)
    }
  }

  // Fonction pour récupérer les statistiques
  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:5001/reporting/stats')
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération des statistiques')
      }
      const data = await response.json()
      setStats(data)
    } catch (err) {
      setError(err.message)
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
    if (activeTab === 'demandes') {
      fetchDemandes()
    } else if (activeTab === 'historique') {
      fetchHistorique()
    } else if (activeTab === 'reporting') {
      fetchStats()
    }
  }, [activeTab])

  useEffect(() => {
    fetchDemandes()
  }, [])

  return (
    <div className="app">
            <header className="app-header">
        <h1>🚗 Système de Gestion de Location</h1>
        <p>Automatisation du traitement des demandes par email</p>
        
        {/* Navigation par onglets */}
        <nav className="tabs">
          <button 
            className={`tab ${activeTab === 'demandes' ? 'active' : ''}`}
            onClick={() => setActiveTab('demandes')}
          >
            📋 Demandes
          </button>
          <button 
            className={`tab ${activeTab === 'historique' ? 'active' : ''}`}
            onClick={() => setActiveTab('historique')}
          >
            📚 Historique
          </button>
          <button 
            className={`tab ${activeTab === 'reporting' ? 'active' : ''}`}
            onClick={() => setActiveTab('reporting')}
          >
            📊 Reporting
          </button>
        </nav>
        
        {/* Actions selon l'onglet actif */}
        <div className="header-actions">
          {activeTab === 'demandes' && (
            <>
              <button onClick={fetchEmails} className="btn btn-primary">
                � Récupérer les emails
              </button>
              <a 
                href="http://localhost:5001/demandes/export" 
                className="btn btn-secondary"
                download
              >
                📊 Exporter CSV
              </a>
            </>
          )}
          {activeTab === 'historique' && (
            <a 
              href="http://localhost:5001/reporting/export?type=historique" 
              className="btn btn-secondary"
              download
            >
              📊 Exporter Historique
            </a>
          )}
          {activeTab === 'reporting' && (
            <a 
              href="http://localhost:5001/reporting/export?type=stats" 
              className="btn btn-secondary"
              download
            >
              � Exporter Rapport
            </a>
          )}
        </div>

        {/* Filtres pour les demandes */}
        {activeTab === 'demandes' && (
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
            <button 
              onClick={() => setFilter({ ville: '', date: '' })}
              className="btn btn-outline"
            >
              🔄 Réinitialiser
            </button>
          </div>
        )}
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
                      
                      <div className="demande-actions">
                        {demande.statut === 'en_attente' && (
                          <button 
                            onClick={() => validerDemande(demande.id)}
                            className="btn btn-success"
                          >
                            ✅ Valider la demande
                          </button>
                        )}
                        <button 
                          onClick={() => supprimerDemande(demande.id)}
                          className="btn btn-danger"
                        >
                          🗑️ Supprimer
                        </button>
                      </div>
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
