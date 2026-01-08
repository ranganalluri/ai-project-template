import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { Home } from '@/pages/Home';
import { Agents } from '@/pages/Agents';
import { Chat } from '@/pages/Chat';
import { ContentProcessing } from '@/pages/ContentProcessing';
import { Settings } from '@/pages/Settings';
import '@/styles/index.css';
import '@agentic/ui-lib/style.css';
// Setup PDF.js worker before any PDF operations
import '@/utils/pdfWorkerSetup';

const App: React.FC = () => {
  return (
    <Router>
      <div className="flex flex-col h-screen">
        <Header />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/home" element={<Home />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/content-processing" element={<ContentProcessing />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
};

export default App;
