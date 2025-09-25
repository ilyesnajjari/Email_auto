import React from "react";
import DemandesTable from "./DemandesTable";
import "./App.css";

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>🚗 Dashboard Demandes de Location</h1>
        <p>Système de gestion automatisé des demandes de location de véhicules</p>
      </header>
      <main className="app-main">
        <DemandesTable />
      </main>
      <footer className="app-footer">
        <p>&copy; 2025 Système de Gestion de Location - Automatisation des emails</p>
      </footer>
    </div>
  );
}

export default App;
