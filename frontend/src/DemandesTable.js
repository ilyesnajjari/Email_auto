import React, { useState, useEffect } from 'react';
import './DemandesTable.css';

const DemandesTable = () => {
  const [demandes, setDemandes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState({ ville: '', date: '' });
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState({ subject: '', body: '', recipients: [], ville: '', lang: '' });
  const [sending, setSending] = useState(false);

  // URL de l'API backend, configurable via Vite env
  const API_URL = (import.meta.env.VITE_API_BASE || '').replace(/\/+$/, '');

  // Charger les demandes au montage du composant
  useEffect(() => {
    fetchDemandes();
  }, []);

  const fetchDemandes = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/demandes`);
      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
      }
      const data = await response.json();
      setDemandes(data);
      setError(null);
    } catch (err) {
      setError(`Erreur lors du chargement: ${err.message}`);
      console.error('Erreur:', err);
    } finally {
      setLoading(false);
    }
  };

  const openPreview = async (id) => {
    try {
      const resp = await fetch(`${API_URL}/demandes/${id}/email/preview`);
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || `Erreur HTTP: ${resp.status}`);
      setPreviewData({
        subject: data.subject || 'Nouvelle demande de location',
        body: data.body || '',
        recipients: data.recipients || [],
        ville: data.ville || '',
        lang: data.lang || 'fr',
        id
      });
      setPreviewOpen(true);
    } catch (err) {
      alert(`Erreur lors de la prévisualisation: ${err.message}`);
    }
  };

  const sendWithEdits = async () => {
    if (!previewData?.id) return;
    if (!previewData.body.trim() || !previewData.recipients?.length) {
      alert('Corps du mail et destinataires requis');
      return;
    }
    try {
      setSending(true);
      const resp = await fetch(`${API_URL}/demandes/${previewData.id}/email/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: previewData.subject,
          body: previewData.body,
          recipients: previewData.recipients,
        })
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || `Erreur HTTP: ${resp.status}`);
      setPreviewOpen(false);
      fetchDemandes();
      alert('Email envoyé et demande validée');
    } catch (err) {
      alert(`Erreur lors de l\'envoi: ${err.message}`);
    } finally {
      setSending(false);
    }
  };

  const fetchEmails = async () => {
    try {
      const response = await fetch(`${API_URL}/fetch_emails`, {
        method: 'POST'
      });
      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
      }
      // Recharger les demandes après récupération des emails
      fetchDemandes();
      alert('Emails récupérés et analysés avec succès !');
    } catch (err) {
      alert(`Erreur lors de la récupération des emails: ${err.message}`);
    }
  };

  const exportCSV = () => {
    window.open(`${API_URL}/demandes/export`, '_blank');
  };

  const applyFilter = async () => {
    try {
      const params = new URLSearchParams();
      if (filter.ville) params.append('ville', filter.ville);
      if (filter.date) params.append('date', filter.date);
      
      const response = await fetch(`${API_URL}/demandes/filter?${params}`);
      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
      }
      const data = await response.json();
      setDemandes(data);
    } catch (err) {
      setError(`Erreur lors du filtrage: ${err.message}`);
    }
  };

  const clearFilter = () => {
    setFilter({ ville: '', date: '' });
    fetchDemandes();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'validee': return '#28a745';
      case 'en_attente': return '#ffc107';
      case 'refusee': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('fr-FR');
    } catch {
      return dateString;
    }
  };

  if (loading) return <div className="loading">Chargement des demandes...</div>;
  if (error) return <div className="error">Erreur: {error}</div>;

  return (
    <div className="demandes-container">
      <div className="actions-bar">
        <button onClick={fetchEmails} className="btn btn-primary">
          📧 Récupérer les emails
        </button>
        <button onClick={exportCSV} className="btn btn-secondary">
          📊 Exporter CSV
        </button>
        <button onClick={fetchDemandes} className="btn btn-refresh">
          🔄 Actualiser
        </button>
      </div>

      <div className="filters">
        <h3>Filtres</h3>
        <div className="filter-group">
          <input
            type="text"
            placeholder="Filtrer par ville..."
            value={filter.ville}
            onChange={(e) => setFilter({...filter, ville: e.target.value})}
          />
          <input
            type="date"
            value={filter.date}
            onChange={(e) => setFilter({...filter, date: e.target.value})}
          />
          <button onClick={applyFilter} className="btn btn-filter">
            Filtrer
          </button>
          <button onClick={clearFilter} className="btn btn-clear">
            Effacer
          </button>
        </div>
      </div>

      <div className="table-container">
        <h2>Demandes de location ({demandes.length})</h2>
        {demandes.length === 0 ? (
          <div className="no-data">Aucune demande trouvée.</div>
        ) : (
          <table className="demandes-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nom</th>
                <th>Prénom</th>
                <th>Téléphone</th>
                <th>Ville</th>
                <th>Date début</th>
                <th>Date fin</th>
                <th>Véhicule</th>
                <th>Statut</th>
                <th>Sous-traitant</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {demandes.map((demande) => (
                <tr key={demande.id}>
                  <td>{demande.id}</td>
                  <td>{demande.nom || 'N/A'}</td>
                  <td>{demande.prenom || 'N/A'}</td>
                  <td>{demande.telephone || 'N/A'}</td>
                  <td>{demande.ville || 'N/A'}</td>
                  <td>{formatDate(demande.date_debut)}</td>
                  <td>{formatDate(demande.date_fin)}</td>
                  <td>{demande.type_vehicule || 'N/A'}</td>
                  <td>
                    <span 
                      className="status-badge"
                      style={{ backgroundColor: getStatusColor(demande.statut) }}
                    >
                      {demande.statut || 'en_attente'}
                    </span>
                  </td>
                  <td>{demande.sous_traitant || 'N/A'}</td>
                  <td>
                    {demande.statut !== 'validee' && (
                      <button
                        onClick={() => openPreview(demande.id)}
                        className="btn btn-validate"
                      >
                        ✅ Valider
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default DemandesTable;

// Simple modal styles can be in CSS; add inline modal here for brevity
export const EmailPreviewModal = ({ open, data, onClose, onChange, onSend, sending }) => {
  if (!open) return null;
  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h3>Prévisualiser l'email aux partenaires</h3>
        <div>
          <label>Sujet</label>
          <input
            value={data.subject}
            onChange={e => onChange({ ...data, subject: e.target.value })}
          />
        </div>
        <div>
          <label>Destinataires</label>
          <textarea
            value={(data.recipients || []).join(', ')}
            onChange={e => onChange({ ...data, recipients: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
          />
        </div>
        <div>
          <label>Corps du mail</label>
          <textarea
            rows={12}
            value={data.body}
            onChange={e => onChange({ ...data, body: e.target.value })}
          />
        </div>
        <div className="modal-actions">
          <button onClick={onClose} className="btn">Annuler</button>
          <button onClick={onSend} className="btn btn-primary" disabled={sending}>{sending ? 'Envoi…' : 'Envoyer'}</button>
        </div>
      </div>
    </div>
  );
};