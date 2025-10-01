import { useState, useEffect } from 'react'
import './App.css'

function App() {
  // Config API base (set VITE_API_BASE in production, e.g., https://email-ghxt.onrender.com)
  const RAW_API_BASE = import.meta.env.VITE_API_BASE || ''
  const API_BASE = (RAW_API_BASE || '').replace(/\/+$/, '')
  const url = (path) => `${API_BASE}${path}`

  const [demandes, setDemandes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState({ ville: '', date: '' })
  const [activeTab, setActiveTab] = useState('demandes')
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
  const [darkMode, setDarkMode] = useState(false)
  const [popupContent, setPopupContent] = useState(null) // État pour le contenu de la popup
  const [email, setEmail] = useState(localStorage.getItem('email') || '')
  const [apiPassword, setApiPassword] = useState(localStorage.getItem('apiPassword') || '')
  const [openaiKey, setOpenaiKey] = useState('')
  const [openaiModel, setOpenaiModel] = useState(localStorage.getItem('OPENAI_MODEL') || 'gpt-4o-mini')
  const [aiEnabled, setAiEnabled] = useState(false)
  const [aiModelStatus, setAiModelStatus] = useState('')
  const [lastFetch, setLastFetch] = useState({ mode: null, inserted: 0, at: null })
  const [showCredentialsForm, setShowCredentialsForm] = useState(false); // État pour afficher/masquer le formulaire d'identifiants
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewData, setPreviewData] = useState({ subject: '', body: '', recipients: [], ville: '', lang: '', id: null })
  const [sendingPreview, setSendingPreview] = useState(false)

  // Admin auth state
  const [adminRequired, setAdminRequired] = useState(false)
  const [adminToken, setAdminToken] = useState(localStorage.getItem('adminToken') || '')
  const [showLogin, setShowLogin] = useState(false)
  const [adminPw, setAdminPw] = useState('')
  const [loginError, setLoginError] = useState('')
  // Auth gate to avoid early dashboard requests before we know if auth is required
  const [authChecked, setAuthChecked] = useState(false)

  // State pour le formulaire d'ajout de demande
  const [newDemande, setNewDemande] = useState({
    nom: '',
    prenom: '',
    telephone: '',
    ville: '',
    date_debut: '',
    date_fin: '',
    type_vehicule: '',
    pays: '',
    email: '',
    nb_personnes: '',
    infos_libres: '',
    date_voyage: ''
  });

  // Fonction pour récupérer les demandes
  const fetchDemandes = async () => {
    try {
      if (adminRequired && !adminToken) return
      setLoading(true)
  const response = await fetch(url('/demandes'))
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

  // Prévisualiser l'email avant envoi
  const openEmailPreview = async (id) => {
    try {
      if (adminRequired && !adminToken) { setShowLogin(true); return }
  const resp = await fetch(url(`/demandes/${id}/email/preview`))
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.error || 'Erreur lors de la prévisualisation')
      setPreviewData({
        subject: data.subject || 'Nouvelle demande de location',
        body: data.body || '',
        recipients: data.recipients || [],
        ville: data.ville || '',
        lang: data.lang || 'fr',
        id
      })
      setPreviewOpen(true)
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  const sendEmailWithEdits = async () => {
    if (!previewData.id) return
    if (!previewData.body.trim() || !previewData.recipients?.length) {
      alert('Corps du mail et destinataires requis')
      return
    }
    try {
      if (adminRequired && !adminToken) { setShowLogin(true); return }
      setSendingPreview(true)
  const resp = await fetch(url(`/demandes/${previewData.id}/email/send`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: previewData.subject,
          body: previewData.body,
          recipients: previewData.recipients,
        })
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.error || 'Erreur lors de l\'envoi')
      setPreviewOpen(false)
      fetchDemandes()
      alert('Email envoyé et demande validée')
    } catch (err) {
      alert('Erreur: ' + err.message)
    } finally {
      setSendingPreview(false)
    }
  }

  // Fonction pour supprimer une demande
  const supprimerDemande = async (id) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette demande ?')) {
      return
    }
    try {
      if (adminRequired && !adminToken) { setShowLogin(true); return }
      const response = await fetch(url(`/demandes/${id}`), {
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
      if (adminRequired && !adminToken) return
      setLoading(true)
  const response = await fetch(url('/historique'))
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
      if (adminRequired && !adminToken) return
      setLoading(true)
  const response = await fetch(url('/reporting/stats'))
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
      if (adminRequired && !adminToken) return
      setLoading(true)
  const response = await fetch(url('/sous-traitants'))
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
      if (adminRequired && !adminToken) { setShowLogin(true); return }
      setLoading(true)
      setUploadStatus(null)
      
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch(url('/sous-traitants/upload'), {
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
      if (adminRequired && !adminToken) { setShowLogin(true); return }
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
      if (adminRequired && !adminToken) { setShowLogin(true); return }
      const response = await fetch(url('/fetch_emails'), {
        method: 'POST'
      })
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération des emails')
      }
      alert('Récupération des emails en cours...')
      // Recharger les demandes après un délai
      setTimeout(() => {
        fetchDemandes()
        // Récupérer l'état du dernier fetch (mode AI/NLP, inserted)
        fetch(url('/fetch_status'))
          .then(r => r.json())
          .then(setLastFetch)
      }, 3000)
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  const saveCredentials = async () => {
    try {
      if (adminRequired && !adminToken) { setShowLogin(true); return }
      const response = await fetch(url('/save_credentials'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, api_password: apiPassword, OPENAI_API_KEY: openaiKey, OPENAI_MODEL: openaiModel })
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || 'Erreur lors de la sauvegarde des identifiants');
      }
      localStorage.setItem('email', email);
      localStorage.setItem('apiPassword', apiPassword);
      localStorage.setItem('OPENAI_MODEL', openaiModel);
      alert('Identifiants enregistrés côté serveur !');
      // Rafraîchir le statut IA
      fetch(url('/credentials/status'))
        .then(r=>r.json())
        .then(d => {
          setAiEnabled(!!d.openai_present)
          if (d.model) setAiModelStatus(d.model)
        })
    } catch (err) {
      alert('Erreur: ' + err.message);
    }
  }

  useEffect(() => {
    // Ne lance pas de requêtes tant que l'auth n'est pas vérifiée
    if (!authChecked) return
    if (adminRequired && !adminToken) return
    if (activeTab === 'demandes') {
      fetchDemandes()
    } else if (activeTab === 'historique') {
      fetchHistorique()
    } else if (activeTab === 'reporting') {
      fetchStats()
    } else if (activeTab === 'sous-traitants') {
      fetchSousTraitants()
    }
  }, [activeTab, authChecked, adminRequired, adminToken])

  useEffect(() => {
    // Global fetch wrapper to inject admin token and handle 401
    const originalFetch = window.fetch
    window.fetch = async (input, init = {}) => {
      const headers = new Headers(init.headers || {})
      if (adminToken) headers.set('Authorization', `Bearer ${adminToken}`)
      const nextInit = { ...init, headers }
      const resp = await originalFetch(input, nextInit)
      if (resp.status === 401) {
        setShowLogin(true)
        setAdminToken('')
        localStorage.removeItem('adminToken')
      }
      return resp
    }
    return () => { window.fetch = originalFetch }
  }, [adminToken])

  useEffect(() => {
    // Découvrir si l'API exige un login admin avant d'afficher quoi que ce soit
    let interval
    const init = async () => {
      try {
        const h = await fetch(url('/health'))
        const d = await h.json()
        const req = !!d.require_admin
        setAdminRequired(req)
        if (req && !adminToken) setShowLogin(true)
      } catch (e) {
        // ignore
      } finally {
        setAuthChecked(true)
      }
      // Charger statut IA et données seulement si accès autorisé
      if (!adminRequired || adminToken) {
        try {
          const r = await fetch(url('/credentials/status'))
          if (r.ok) {
            const d2 = await r.json()
            setAiEnabled(!!d2.openai_present)
            if (d2.model) setAiModelStatus(d2.model)
          }
        } catch {}
        fetchSousTraitants()
        fetchDemandes()
        fetchHistorique()
        fetchStats()
      }
      interval = setInterval(() => {
        if (!adminRequired || adminToken) {
          fetchSousTraitants()
          if (activeTab === 'demandes') fetchDemandes()
          if (activeTab === 'historique') fetchHistorique()
          if (activeTab === 'reporting') fetchStats()
        }
      }, 5 * 60 * 1000)
    }
    init()
    return () => { if (interval) clearInterval(interval) }
  }, [])

  // Une fois le token présent (page rechargée avec token en localStorage), charger les données
  useEffect(() => {
    if (!authChecked) return
    if (adminRequired && adminToken) {
      fetchSousTraitants()
      fetchDemandes()
      fetchHistorique()
      fetchStats()
    }
  }, [adminToken, adminRequired, authChecked])

  const doLogin = async (e) => {
    e?.preventDefault()
    setLoginError('')
    try {
      const resp = await fetch(url('/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: adminPw })
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.error || 'Mot de passe invalide')
      if (data.token) {
        setAdminToken(data.token)
        localStorage.setItem('adminToken', data.token)
        setAdminRequired(!!data.require_admin)
        setShowLogin(false)
        setAdminPw('')
        // Charger les données après connexion
        fetchSousTraitants()
        fetchDemandes()
        fetchHistorique()
        fetchStats()
      }
    } catch (err) {
      setLoginError(err.message)
    }
  }

  const doLogout = () => {
    setAdminToken('')
    localStorage.removeItem('adminToken')
    if (adminRequired) setShowLogin(true)
  }

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

  useEffect(() => {
    document.body.classList.toggle('dark-mode', darkMode);
  }, [darkMode]);

  // Actualisation automatique des sous-traitants après une erreur
  useEffect(() => {
    if (activeTab === 'demandes' && error) {
      const timer = setTimeout(() => {
        setError(null);
        fetchDemandes();
      }, 2500); // 2,5 secondes avant de réessayer
      return () => clearTimeout(timer);
    }
  }, [activeTab, error]);

  // Écran d'attente pendant la vérification d'auth
  if (!authChecked) {
    return (
      <div className="app" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading">Initialisation...</div>
      </div>
    )
  }
  // Page de connexion dédiée
  if ((adminRequired && !adminToken) || showLogin) {
    return (
      <div className="app" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f4f6f8' }}>
        <form onSubmit={doLogin} style={{ background: '#fff', padding: 28, borderRadius: 10, width: 360, boxShadow: '0 10px 30px rgba(0,0,0,0.08)' }}>
          <h2 style={{ marginTop: 0, marginBottom: 6, color: '#2c3e50' }}>Connexion admin</h2>
          <p style={{ marginTop: 0, color: '#666', fontSize: 14 }}>Veuillez entrer le mot de passe administrateur pour accéder au tableau de bord.</p>
          <input type="password" placeholder="Mot de passe admin" value={adminPw} onChange={e => setAdminPw(e.target.value)} style={{ width: '100%', padding: 12, marginTop: 12, marginBottom: 10, borderRadius: 8, border: '1px solid #dfe6e9' }} />
          {loginError && <div style={{ color: '#c0392b', marginBottom: 10, fontSize: 14 }}>{loginError}</div>}
          <button type="submit" style={{ width: '100%', padding: 12, border: 'none', borderRadius: 8, background: '#2c3e50', color: '#fff', cursor: 'pointer', fontWeight: 600 }}>Se connecter</button>
        </form>
      </div>
    )
  }

  return (
    <div className="app">
      <header className={`app-header ${darkMode ? 'dark-mode' : ''}`}>
        <h1><i className="fas fa-car"></i> Système de Gestion de Location</h1>
        <p>Automatisation du traitement des demandes par email</p>
  <div style={{ marginTop: '8px', display: 'flex', gap: '8px', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap' }}>
          <span
            className="badge"
            style={{
              background: aiEnabled ? '#27ae60' : '#7f8c8d',
              color: '#fff',
              padding: '4px 8px',
              borderRadius: '6px',
              fontSize: '0.85rem'
            }}
          >
            {aiEnabled ? `IA activée (${aiModelStatus || openaiModel})` : 'IA désactivée'}
          </span>
           {(adminRequired && adminToken) && (
             <button onClick={doLogout} style={{ padding: '4px 12px', borderRadius: 6, border: 'none', background: '#c0392b', color: '#fff', fontWeight: 'bold', cursor: 'pointer' }}>Se déconnecter</button>
           )}
          {lastFetch?.at && (
            <span
              className="badge"
              style={{ background: '#34495e', color: '#ecf0f1', padding: '4px 8px', borderRadius: '6px', fontSize: '0.85rem' }}
              title={`Mode: ${lastFetch.mode || 'N/A'}`}
            >
              Dernier fetch: {new Date(lastFetch.at).toLocaleString('fr-FR')} • insérés: {lastFetch.inserted}
            </span>
          )}
        </div>
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
          <button 
            onClick={() => setDarkMode(!darkMode)} 
            className="btn btn-outline"
            title={darkMode ? "Mode clair" : "Mode sombre"}
          >
            {darkMode ? (
              <>
                <i className="fas fa-sun"></i> {/* Icône soleil */}
              </>
            ) : (
              <>
                <i className="fas fa-moon"></i> {/* Icône lune */}
              </>
            )}
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
                href={`${API_BASE}/demandes/export`} 
                className="btn btn-secondary"
                download
              >
                <i className="fas fa-download"></i> Exporter CSV
              </a>
            </>
          )}
          {activeTab === 'historique' && (
            <a 
              href={`${API_BASE}/reporting/export?type=historique`} 
              className="btn btn-secondary"
              download
            >
              <i className="fas fa-download"></i> Exporter Historique
            </a>
          )}
          {activeTab === 'reporting' && (
            <a 
              href={`${API_BASE}/reporting/export?type=stats`} 
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
        {error && (
          activeTab === 'demandes'
            ? <div className="loading">Attente avant actualisation...</div>
            : <div className="error">Erreur: {error}</div>
        )}
        
        {/* Onglet Demandes */}
        {activeTab === 'demandes' && !loading && !error && (
          <div className="demandes-container">
            <h2>Demandes de location ({demandes.length})</h2>

            {/* Formulaire d'ajout de demande */}
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setLoading(true);
                setError(null);
                try {
                  const response = await fetch(url('/demandes'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newDemande)
                  });
                  if (!response.ok) {
                    const res = await response.json();
                    throw new Error(res.error || 'Erreur lors de l\'ajout');
                  }
                  setNewDemande({
                    nom: '', prenom: '', telephone: '', ville: '', date_debut: '', date_fin: '', type_vehicule: '', pays: '', email: '', nb_personnes: '', infos_libres: ''
                  });
                  fetchDemandes();
                  alert('Demande ajoutée avec succès!');
                } catch (err) {
                  setError(err.message);
                } finally {
                  setLoading(false);
                }
              }}
              style={{ marginBottom: '2rem', background: '#f8f9ff', padding: '1rem', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}
            >
              <h3>Ajouter une demande</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                <input required type="text" placeholder="Nom" value={newDemande.nom} onChange={e => setNewDemande({ ...newDemande, nom: e.target.value })} />
                <input required type="text" placeholder="Prénom" value={newDemande.prenom} onChange={e => setNewDemande({ ...newDemande, prenom: e.target.value })} />
                <input type="email" placeholder="Email" value={newDemande.email} onChange={e => setNewDemande({ ...newDemande, email: e.target.value })} />
                <input type="text" placeholder="Téléphone" value={newDemande.telephone} onChange={e => setNewDemande({ ...newDemande, telephone: e.target.value })} />
                <input type="text" placeholder="Ville" value={newDemande.ville} onChange={e => setNewDemande({ ...newDemande, ville: e.target.value })} />
                <input type="text" placeholder="Pays" value={newDemande.pays} onChange={e => setNewDemande({ ...newDemande, pays: e.target.value })} />
                <input type="date" placeholder="Date début" value={newDemande.date_debut} onChange={e => setNewDemande({ ...newDemande, date_debut: e.target.value })} />
                <input type="date" placeholder="Date fin" value={newDemande.date_fin} onChange={e => setNewDemande({ ...newDemande, date_fin: e.target.value })} />
                <input type="date" placeholder="Date voyage" value={newDemande.date_voyage || ''} onChange={e => setNewDemande({ ...newDemande, date_voyage: e.target.value })} />
                <input type="text" placeholder="Type de véhicule" value={newDemande.type_vehicule} onChange={e => setNewDemande({ ...newDemande, type_vehicule: e.target.value })} />
                <input type="number" min="1" placeholder="Nb personnes" value={newDemande.nb_personnes} onChange={e => setNewDemande({ ...newDemande, nb_personnes: e.target.value })} />
                <input type="text" placeholder="Infos libres" value={newDemande.infos_libres} onChange={e => setNewDemande({ ...newDemande, infos_libres: e.target.value })} />
              </div>
              <button type="submit" className="btn btn-primary" style={{ marginTop: '1rem' }}>Ajouter</button>
            </form>

            {demandes.length === 0 ? (
              <div className="empty-state">
                <p>Aucune demande trouvée.</p>
                <p>Cliquez sur "Récupérer les emails" pour analyser les nouveaux emails.</p>
              </div>
            ) : (
              <div className="demandes-table" style={{ overflowX: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th>N° Id</th>
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
                      <th>Nbr de personnes</th>
                      <th>Sous-traitants</th>
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
                          <td>{demande.nb_personnes || '-'}</td>
                          <td>{demande.nb_sous_traitants || 0}</td>
                          <td>
                            <div className="action-buttons">
                              {demande.statut === 'en_attente' && (
                                <button 
                                  onClick={() => openEmailPreview(demande.id)}
                                  className="btn btn-success btn-small"
                                  title="Prévisualiser et envoyer"
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
                              {/* Add a button to show the email body in a popup */}
                              <button 
                                onClick={() => {
                                  console.log('Corps du mail:', demande.corps_mail); // Log the email body
                                  setPopupContent(demande.corps_mail)
                                }} 
                                className="btn btn-info btn-small" 
                                title="Voir le corps du mail"
                              >
                                <i className="fas fa-eye"></i>
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

              {/* Section des statistiques sous forme de bulles */}
              <div className="stats-bubbles">
                <div className="bubble">
                  <span className="bubble-number">{sousTraitantsFiltres.length}</span>
                  <span className="bubble-label">Affichés</span>
                </div>
                <div className="bubble">
                  <span className="bubble-number">{sousTraitants.length}</span>
                  <span className="bubble-label">Total</span>
                </div>
                <div className="bubble">
                  <span className="bubble-number">{Object.keys(statsVilles).length}</span>
                  <span className="bubble-label">Villes</span>
                </div>
                <div className="bubble">
                  <span className="bubble-number">{Object.keys(statsPays).length}</span>
                  <span className="bubble-label">Pays</span>
                </div>
              </div>
            </div>
        )}

        {/* Popup pour afficher le corps du mail */}
        {popupContent && (
          <div className="popup-overlay" onClick={() => setPopupContent(null)}>
            <div className="popup-content" onClick={(e) => e.stopPropagation()}>
              <button className="close-popup" onClick={() => setPopupContent(null)}>&times;</button>
              <h3>Corps du mail</h3>
              <p>{popupContent}</p>
            </div>
          </div>
        )}

        {/* Modal de prévisualisation d'email */}
        {previewOpen && (
          <div className="popup-overlay" onClick={() => setPreviewOpen(false)}>
            <div className="popup-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px', width: '95%' }}>
              <button className="close-popup" onClick={() => setPreviewOpen(false)}>&times;</button>
              <h3>Prévisualiser l'email aux sous-traitants</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label>Sujet</label>
                  <input
                    type="text"
                    value={previewData.subject}
                    onChange={(e) => setPreviewData({ ...previewData, subject: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <label>Destinataires (BCC)</label>
                  <input
                    type="text"
                    value={(previewData.recipients || []).join(', ')}
                    onChange={(e) => setPreviewData({ ...previewData, recipients: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                    placeholder="email1@example.com, email2@example.com"
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <label>Corps du message</label>
                  <textarea
                    value={previewData.body}
                    onChange={(e) => setPreviewData({ ...previewData, body: e.target.value })}
                    rows={14}
                    style={{ width: '100%' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                  <button className="btn btn-outline" onClick={() => setPreviewOpen(false)}>Annuler</button>
                  <button className="btn btn-primary" onClick={sendEmailWithEdits} disabled={sendingPreview}>
                    {sendingPreview ? 'Envoi...' : 'Envoyer et valider'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Add a button to toggle the credentials form */}
        <button
          onClick={() => setShowCredentialsForm(!showCredentialsForm)}
          style={{ margin: '20px', padding: '10px', backgroundColor: '#28a745', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
        >
          {showCredentialsForm ? 'Masquer le formulaire' : 'Afficher le formulaire'}
        </button>

        {/* Formulaire pour saisir l'email et le mot de passe API */}
        {showCredentialsForm && (
          <div className="credentials-form" style={{ maxWidth: '400px', margin: '20px auto', padding: '20px', border: '1px solid #ccc', borderRadius: '8px', boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)' }}>
            <h3 style={{ textAlign: 'center', marginBottom: '20px' }}>Connectez-vous à votre compte</h3>
            <div style={{ marginBottom: '15px' }}>
              <label htmlFor="email" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Email</label>
              <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #ccc', borderRadius: '4px', padding: '5px' }}>
                <i className="fas fa-envelope" style={{ marginRight: '10px', color: '#888' }}></i>
                <input
                  id="email"
                  type="email"
                  placeholder="Entrez votre email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ flex: '1', border: 'none', outline: 'none' }}
                />
              </div>
            </div>
            <div style={{ marginBottom: '20px' }}>
              <label htmlFor="apiPassword" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Mot de passe API</label>
              <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #ccc', borderRadius: '4px', padding: '5px' }}>
                <i className="fas fa-key" style={{ marginRight: '10px', color: '#888' }}></i>
                <input
                  id="apiPassword"
                  type="password"
                  placeholder="Entrez votre mot de passe API"
                  value={apiPassword}
                  onChange={(e) => setApiPassword(e.target.value)}
                  style={{ flex: '1', border: 'none', outline: 'none' }}
                />
              </div>
            </div>
            <div style={{ marginBottom: '15px' }}>
              <label htmlFor="openaiKey" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Clé OpenAI (optionnel)</label>
              <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #ccc', borderRadius: '4px', padding: '5px' }}>
                <i className="fas fa-robot" style={{ marginRight: '10px', color: '#888' }}></i>
                <input
                  id="openaiKey"
                  type="password"
                  placeholder="OPENAI_API_KEY"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  style={{ flex: '1', border: 'none', outline: 'none' }}
                />
              </div>
            </div>
            <div style={{ marginBottom: '20px' }}>
              <label htmlFor="openaiModel" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Modèle OpenAI</label>
              <select id="openaiModel" value={openaiModel} onChange={(e)=> setOpenaiModel(e.target.value)} className="form-select" style={{ width: '100%' }}>
                <option value="gpt-4o-mini">gpt-4o-mini (défaut)</option>
                <option value="gpt-4o">gpt-4o</option>
                <option value="o4-mini">o4-mini</option>
              </select>
            </div>
            <button
              onClick={saveCredentials}
              style={{ width: '100%', padding: '10px', backgroundColor: '#007BFF', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              Enregistrer les identifiants
            </button>
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