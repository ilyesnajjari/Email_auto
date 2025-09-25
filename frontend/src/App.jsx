import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [demandes, setDemandes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState({ ville: '', date: '' })
  const [activeTab, setActiveTab] = useState('sous-traitants')
  const [historique, setHistorique] = useState([])
  const [stats, setStats] = useState(null)
  const [sousTraitants, setSousTraitants] = useState([])
  const [uploadStatus, setUploadStatus] = useState(null)
  const [sousTraitantsFilter, setSousTraitantsFilter] = useState({ 
    ville: '', 
    pays: '', 
    recherche: '' 
  })
  const [lastUpdate, setLastUpdate] = useState(null)

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
      setLoading(true)
      const response = await fetch('http://localhost:5001/historique')
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération de l\'historique')
      }
      const data = await response.json()
      setHistorique(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Fonction pour récupérer les statistiques
  const fetchStats = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:5001/reporting/stats')
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération des statistiques')
      }
      const data = await response.json()
      setStats(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Fonction pour récupérer les sous-traitants
  const fetchSousTraitants = async (showNotification = false) => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:5001/sous-traitants')
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération des sous-traitants')
      }
      const data = await response.json()
      setSousTraitants(data)
      setLastUpdate(new Date())
      
      if (showNotification) {
        setUploadStatus({
          type: 'success',
          message: `${data.length} sous-traitants chargés avec succès`,
          details: { count: data.length }
        })
        // Masquer la notification après 3 secondes
        setTimeout(() => setUploadStatus(null), 3000)
      }
    } catch (err) {
      setError(err.message)
      if (showNotification) {
        setUploadStatus({
          type: 'error',
          message: err.message
        })
      }
    } finally {
      setLoading(false)
    }
  }

  // Fonction pour upload du fichier Excel
  const uploadExcel = async (file) => {
    try {
      setLoading(true)
      setUploadStatus(null)
      
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch('http://localhost:5001/sous-traitants/upload', {
        method: 'POST',
        body: formData
      })
      
      const result = await response.json()
      
      if (!response.ok) {
        throw new Error(result.error || 'Erreur lors de l\'upload')
      }
      
      setUploadStatus({
        type: 'success',
        message: result.message,
        details: result
      })
      
      // Recharger la liste des sous-traitants
      fetchSousTraitants()
      
    } catch (err) {
      setUploadStatus({
        type: 'error',
        message: err.message
      })
    } finally {
      setLoading(false)
    }
  }

  // Fonction pour supprimer un sous-traitant
  const supprimerSousTraitant = async (id) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce sous-traitant ?')) {
      return
    }
    try {
      const response = await fetch(`http://localhost:5001/sous-traitants/${id}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error('Erreur lors de la suppression')
      }
      // Recharger la liste après suppression
      fetchSousTraitants()
      alert('Sous-traitant supprimé avec succès!')
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
      alert('Récupération des emails en cours...')
      // Recharger les demandes après un délai
      setTimeout(() => {
        fetchDemandes()
      }, 3000)
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  useEffect(() => {
    if (activeTab === 'demandes') {
      fetchDemandes()
    } else if (activeTab === 'historique') {
      fetchHistorique()
    } else if (activeTab === 'reporting') {
      fetchStats()
    } else if (activeTab === 'sous-traitants') {
      fetchSousTraitants()
    }
  }, [activeTab])

  useEffect(() => {
    // Charger toutes les données au démarrage pour affichage permanent
    fetchSousTraitants()
    fetchDemandes()
    fetchHistorique()
    fetchStats()

    // Rafraîchissement automatique toutes les 5 minutes pour maintenir les données à jour
    const interval = setInterval(() => {
      fetchSousTraitants()
      if (activeTab === 'demandes') fetchDemandes()
      if (activeTab === 'historique') fetchHistorique()
      if (activeTab === 'reporting') fetchStats()
    }, 5 * 60 * 1000) // 5 minutes

    return () => clearInterval(interval)
  }, [])

  // Calculs pour le filtrage des sous-traitants
  const sousTraitantsFiltres = sousTraitants.filter(st => {
    const matchRecherche = !sousTraitantsFilter.recherche || 
      (st.nom_entreprise || st.nom || '').toLowerCase().includes(sousTraitantsFilter.recherche.toLowerCase()) ||
      (st.email || '').toLowerCase().includes(sousTraitantsFilter.recherche.toLowerCase());
    
    const matchVille = !sousTraitantsFilter.ville || st.ville === sousTraitantsFilter.ville;
    const matchPays = !sousTraitantsFilter.pays || st.pays === sousTraitantsFilter.pays;
    
    return matchRecherche && matchVille && matchPays;
  });

  // Statistiques pour les sous-traitants
  const statsVilles = sousTraitants.reduce((acc, st) => {
    if (st.ville) {
      acc[st.ville] = (acc[st.ville] || 0) + 1;
    }
    return acc;
  }, {});

  const statsPays = sousTraitants.reduce((acc, st) => {
    if (st.pays) {
      acc[st.pays] = (acc[st.pays] || 0) + 1;
    }
    return acc;
  }, {});

  return (
    <div className="app">
      <header className="app-header">
        <h1><i className="fas fa-car"></i> Système de Gestion de Location</h1>
        <p>Automatisation du traitement des demandes par email</p>
        
        {/* Navigation par onglets */}
        <nav className="tabs">
          <button 
            className={`tab ${activeTab === 'demandes' ? 'active' : ''}`}
            onClick={() => setActiveTab('demandes')}
          >
            <i className="fas fa-clipboard-list"></i> Demandes
          </button>
          <button 
            className={`tab ${activeTab === 'historique' ? 'active' : ''}`}
            onClick={() => setActiveTab('historique')}
          >
            <i className="fas fa-history"></i> Historique
          </button>
          <button 
            className={`tab ${activeTab === 'reporting' ? 'active' : ''}`}
            onClick={() => setActiveTab('reporting')}
          >
            <i className="fas fa-chart-bar"></i> Reporting
          </button>
          <button 
            className={`tab ${activeTab === 'sous-traitants' ? 'active' : ''}`}
            onClick={() => setActiveTab('sous-traitants')}
          >
            <i className="fas fa-users"></i> Sous-traitants
          </button>
        </nav>
        
        {/* Actions selon l'onglet actif */}
        <div className="header-actions">
          {activeTab === 'demandes' && (
            <>
              <button onClick={fetchEmails} className="btn btn-primary">
                <i className="fas fa-envelope"></i> Récupérer les emails
              </button>
              <a 
                href="http://localhost:5001/demandes/export" 
                className="btn btn-secondary"
                download
              >
                <i className="fas fa-download"></i> Exporter CSV
              </a>
            </>
          )}
          {activeTab === 'historique' && (
            <a 
              href="http://localhost:5001/reporting/export?type=historique" 
              className="btn btn-secondary"
              download
            >
              <i className="fas fa-download"></i> Exporter Historique
            </a>
          )}
          {activeTab === 'reporting' && (
            <a 
              href="http://localhost:5001/reporting/export?type=stats" 
              className="btn btn-secondary"
              download
            >
              <i className="fas fa-download"></i> Exporter Rapport
            </a>
          )}
          {activeTab === 'sous-traitants' && (
            <>
              <button 
                onClick={() => fetchSousTraitants(true)} 
                className="btn btn-outline"
                title="Rafraîchir les données"
              >
                <i className="fas fa-sync-alt"></i> Actualiser
              </button>
              <label className="btn btn-primary file-upload-btn">
                <i className="fas fa-file-excel"></i> Importer Excel
                <input 
                  type="file" 
                  accept=".xlsx,.xls" 
                  onChange={(e) => {
                    if (e.target.files[0]) {
                      uploadExcel(e.target.files[0])
                      e.target.value = '' // Reset input
                    }
                  }}
                  style={{ display: 'none' }}
                />
              </label>
            </>
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
              <i className="fas fa-redo"></i> Réinitialiser
            </button>
          </div>
        )}


      </header>

      <main className="app-main">
        {loading && <div className="loading">Chargement...</div>}
        {error && <div className="error">Erreur: {error}</div>}
        
        {/* Onglet Demandes */}
        {activeTab === 'demandes' && !loading && !error && (
          <div className="demandes-container">
            <h2>Demandes de location ({demandes.length})</h2>
            
            {demandes.length === 0 ? (
              <div className="empty-state">
                <p>Aucune demande trouvée.</p>
                <p>Cliquez sur "Récupérer les emails" pour analyser les nouveaux emails.</p>
              </div>
            ) : (
              <div className="demandes-table">
                <table>
                  <thead>
                    <tr>
                      <th>N° Demande</th>
                      <th>Status</th>
                      <th>Jours restants</th>
                      <th>Date enr</th>
                      <th>Date du jour</th>
                      <th>Date voy</th>
                      <th>Client</th>
                      <th>Pays</th>
                      <th>Ville</th>
                      <th>Téléphone</th>
                      <th>Véhicule</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {demandes
                      .filter(demande => 
                        (!filter.ville || demande.ville?.toLowerCase().includes(filter.ville.toLowerCase())) &&
                        (!filter.date || (demande.date_debut <= filter.date && demande.date_fin >= filter.date))
                      )
                      .map(demande => (
                        <tr key={demande.id} className={`demande-row ${demande.statut}`}>
                          <td><strong>#{demande.id}</strong></td>
                          <td>
                            <span className={`status-badge ${demande.statut}`}>
                              {demande.statut === 'en_attente' ? <><i className="fas fa-clock"></i> En attente</> : 
                               demande.statut === 'validee' ? <><i className="fas fa-check"></i> Validée</> : 
                               demande.statut}
                            </span>
                          </td>
                          <td>
                            <span className={`jours-restants ${
                              demande.jours_restants !== null ? 
                                (demande.jours_restants < 0 ? 'expire' : 
                                 demande.jours_restants <= 7 ? 'urgent' : 'normal') 
                                : ''
                            }`}>
                              {demande.jours_restants !== null ? 
                                `${demande.jours_restants} j` : 
                                '-'}
                            </span>
                          </td>
                          <td>{demande.date_enr_formatted || '-'}</td>
                          <td>{demande.date_du_jour}</td>
                          <td>{demande.date_voyage || demande.date_debut}</td>
                          <td>
                            <strong>{demande.prenom} {demande.nom}</strong>
                          </td>
                          <td>{demande.pays || '-'}</td>
                          <td>{demande.ville}</td>
                          <td>
                            {demande.telephone ? (
                              <a href={`tel:${demande.telephone}`}><i className="fas fa-phone"></i> {demande.telephone}</a>
                            ) : '-'}
                          </td>
                          <td>{demande.type_vehicule}</td>
                          <td>
                            <div className="action-buttons">
                              {demande.statut === 'en_attente' && (
                                <button 
                                  onClick={() => validerDemande(demande.id)}
                                  className="btn btn-success btn-small"
                                  title="Valider la demande"
                                >
                                  <i className="fas fa-check"></i>
                                </button>
                              )}
                              <button 
                                onClick={() => supprimerDemande(demande.id)}
                                className="btn btn-danger btn-small"
                                title="Supprimer la demande"
                              >
                                <i className="fas fa-trash"></i>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Onglet Historique */}
        {activeTab === 'historique' && !loading && !error && (
          <div className="historique-container">
            <h2>Historique des actions ({historique.length})</h2>
            
            {historique.length === 0 ? (
              <div className="empty-state">
                <p>Aucune action dans l'historique.</p>
              </div>
            ) : (
              <div className="historique-table">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Action</th>
                      <th>Client</th>
                      <th>Ville</th>
                      <th>Véhicule</th>
                      <th>Statut</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historique.map(item => (
                      <tr key={item.id}>
                        <td>{new Date(item.date_action).toLocaleString('fr-FR')}</td>
                        <td>
                          <span className={`action-badge ${item.action}`}>
                            {item.action === 'validation' ? <><i className="fas fa-check"></i> Validation</> : 
                             item.action === 'suppression' ? <><i className="fas fa-trash"></i> Suppression</> : 
                             item.action}
                          </span>
                        </td>
                        <td>{item.prenom} {item.nom}</td>
                        <td>{item.ville}</td>
                        <td>{item.type_vehicule}</td>
                        <td>{item.statut}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Onglet Reporting */}
        {activeTab === 'reporting' && !loading && !error && (
          <div className="reporting-container">
            <h2>Tableau de bord et statistiques</h2>
            
            {stats && (
              <div className="stats-grid">
                <div className="stat-card">
                  <h3><i className="fas fa-chart-pie"></i> Vue d'ensemble</h3>
                  <div className="stat-item">
                    <span className="stat-label">Total des demandes:</span>
                    <span className="stat-value">{stats.total_demandes}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Demandes validées:</span>
                    <span className="stat-value success">{stats.demandes_validees}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">En attente:</span>
                    <span className="stat-value warning">{stats.demandes_en_attente}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Taux de validation:</span>
                    <span className="stat-value">{stats.taux_validation}%</span>
                  </div>
                </div>

                <div className="stat-card">
                  <h3><i className="fas fa-city"></i> Demandes par ville</h3>
                  {stats.stats_ville.map(item => (
                    <div key={item.ville} className="stat-item">
                      <span className="stat-label">{item.ville}:</span>
                      <span className="stat-value">{item.count}</span>
                    </div>
                  ))}
                </div>

                <div className="stat-card">
                  <h3><i className="fas fa-car"></i> Demandes par véhicule</h3>
                  {stats.stats_vehicule.map(item => (
                    <div key={item.type} className="stat-item">
                      <span className="stat-label">{item.type}:</span>
                      <span className="stat-value">{item.count}</span>
                    </div>
                  ))}
                </div>

                <div className="stat-card">
                  <h3>📅 Évolution mensuelle</h3>
                  {stats.stats_mois.map(item => (
                    <div key={item.mois} className="stat-item">
                      <span className="stat-label">{item.mois}:</span>
                      <span className="stat-value">{item.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Onglet Sous-traitants */}
        {activeTab === 'sous-traitants' && (
            <div className="sous-traitants-container">
              {/* Affichage des erreurs */}
              {error && (
                <div className="error-message">
                  <i className="fas fa-exclamation-triangle"></i>
                  <p>Erreur : {error}</p>
                  <button onClick={() => {setError(null); fetchSousTraitants(true);}} className="btn btn-outline">
                    <i className="fas fa-redo"></i> Réessayer
                  </button>
                </div>
              )}

              <div className="sous-traitants-header">
                <h2>Gestion des sous-traitants</h2>
                <p className="sous-traitants-description">
                  <i className="fas fa-info-circle"></i> 
                  Gérez votre réseau de sous-traitants partenaires. Importez, filtrez et consultez les informations de contact.
                  {lastUpdate && (
                    <span className="last-update">
                      <i className="fas fa-sync-alt"></i> 
                      Dernière mise à jour : {lastUpdate.toLocaleString('fr-FR')}
                    </span>
                  )}
                </p>
                <div className="sous-traitants-stats">
                  {loading && (
                    <div className="stat-badge loading">
                      <i className="fas fa-spinner fa-spin"></i>
                      <span className="stat-label">Actualisation...</span>
                    </div>
                  )}
                  <div className="stat-badge">
                    <span className="stat-number">{sousTraitantsFiltres.length}</span>
                    <span className="stat-label">Affichés</span>
                  </div>
                  <div className="stat-badge">
                    <span className="stat-number">{sousTraitants.length}</span>
                    <span className="stat-label">Total</span>
                  </div>
                  <div className="stat-badge">
                    <span className="stat-number">{Object.keys(statsVilles).length}</span>
                    <span className="stat-label">Villes</span>
                  </div>
                  <div className="stat-badge">
                    <span className="stat-number">{Object.keys(statsPays).length}</span>
                    <span className="stat-label">Pays</span>
                  </div>
                </div>
              </div>

              {/* Section de filtres et recherche */}
              <div className="filters-section">
                <h3><i className="fas fa-search"></i> Filtres</h3>
                <div className="filters-grid">
                  <div className="filter-group">
                    <label>Recherche :</label>
                    <input
                      type="text"
                      placeholder="Nom, email, téléphone..."
                      value={sousTraitantsFilter.recherche}
                      onChange={(e) => setSousTraitantsFilter({...sousTraitantsFilter, recherche: e.target.value})}
                      className="form-input"
                    />
                  </div>
                  <div className="filter-group">
                    <label>Pays :</label>
                    <select
                      value={sousTraitantsFilter.pays}
                      onChange={(e) => setSousTraitantsFilter({...sousTraitantsFilter, pays: e.target.value})}
                      className="form-select"
                    >
                      <option value="">Tous les pays</option>
                      {Object.keys(statsPays).map(pays => (
                        <option key={pays} value={pays}>{pays}</option>
                      ))}
                    </select>
                  </div>
                  <div className="filter-group">
                    <label>Ville :</label>
                    <select
                      value={sousTraitantsFilter.ville}
                      onChange={(e) => setSousTraitantsFilter({...sousTraitantsFilter, ville: e.target.value})}
                      className="form-select"
                    >
                      <option value="">Toutes les villes</option>
                      {Object.keys(statsVilles).map(ville => (
                        <option key={ville} value={ville}>{ville}</option>
                      ))}
                    </select>
                  </div>
                  <div className="filter-group">
                    <button
                      onClick={() => setSousTraitantsFilter({recherche: '', pays: '', ville: ''})}
                      className="btn btn-outline"
                    >
                      <i className="fas fa-redo"></i> Réinitialiser
                    </button>
                  </div>
                </div>
              </div>

              {/* Tableau des sous-traitants */}
              {sousTraitantsFiltres.length === 0 && sousTraitants.length === 0 ? (
                <div className="empty-state">
                  <i className="fas fa-users" style={{fontSize: '3rem', color: '#bdc3c7', marginBottom: '1rem'}}></i>
                  <h3>Aucun sous-traitant</h3>
                  <p>Utilisez le bouton "Importer Excel" pour ajouter des sous-traitants à votre réseau.</p>
                </div>
              ) : sousTraitantsFiltres.length === 0 ? (
                <div className="empty-state">
                  <i className="fas fa-search" style={{fontSize: '3rem', color: '#bdc3c7', marginBottom: '1rem'}}></i>
                  <h3>Aucun résultat</h3>
                  <p>Aucun sous-traitant ne correspond à vos critères de recherche.</p>
                  <button
                    onClick={() => setSousTraitantsFilter({recherche: '', pays: '', ville: ''})}
                    className="btn btn-primary"
                  >
                    <i className="fas fa-redo"></i> Réinitialiser les filtres
                  </button>
                </div>
              ) : (
                <div className="sous-traitants-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Entreprise</th>
                        <th>Site web</th>
                        <th>Pays</th>
                        <th>Ville</th>
                        <th>Email</th>
                        <th>Téléphone</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sousTraitantsFiltres.map(st => (
                        <tr key={st.id}>
                          <td><strong>{st.nom_entreprise || st.nom}</strong></td>
                          <td>
                            {st.site_internet ? (
                              <a href={st.site_internet} target="_blank" rel="noopener noreferrer">
                                <i className="fas fa-external-link-alt"></i> {st.site_internet}
                              </a>
                            ) : '-'}
                          </td>
                          <td>{st.pays || '-'}</td>
                          <td>{st.ville}</td>
                          <td>
                            <a href={`mailto:${st.email}`}><i className="fas fa-envelope"></i> {st.email}</a>
                          </td>
                          <td>
                            {st.telephone ? (
                              <a href={`tel:${st.telephone}`}><i className="fas fa-phone"></i> {st.telephone}</a>
                            ) : '-'}
                          </td>
                          <td>
                            <button 
                              onClick={() => supprimerSousTraitant(st.id)}
                              className="btn btn-danger btn-small"
                              title="Supprimer ce sous-traitant"
                            >
                              <i className="fas fa-trash"></i>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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