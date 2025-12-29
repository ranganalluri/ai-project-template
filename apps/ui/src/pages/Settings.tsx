/** Settings page component. */

import React, { useEffect, useState } from 'react';
import { checkHealth, getApiUrl, setApiUrl } from '@agentic/ui-lib';
import './Settings.css';

export const Settings: React.FC = () => {
  const [apiUrl, setApiUrlState] = useState<string>('');
  const [healthStatus, setHealthStatus] = useState<'checking' | 'ok' | 'error' | null>(null);
  const [healthMessage, setHealthMessage] = useState<string>('');
  const [foundryConfigured, setFoundryConfigured] = useState<boolean>(false);

  useEffect(() => {
    // Load saved API URL
    const savedApiUrl = localStorage.getItem('apiUrl') || getApiUrl();
    setApiUrlState(savedApiUrl);
  }, []);

  const handleSave = () => {
    localStorage.setItem('apiUrl', apiUrl);
    setApiUrl(apiUrl);
    setHealthStatus(null);
    setHealthMessage('');
  };

  const handleTest = async () => {
    setHealthStatus('checking');
    setHealthMessage('Checking connection...');

    try {
      // Temporarily set API URL for test
      const originalUrl = getApiUrl();
      setApiUrl(apiUrl);

      const result = await checkHealth();
      setHealthStatus('ok');
      setFoundryConfigured(result.foundryConfigured);
      setHealthMessage(
        `Backend is healthy. Status: ${result.status}. Foundry: ${result.foundryConfigured ? 'Configured' : 'Not configured'}`,
      );

      // Restore original URL
      setApiUrl(originalUrl);
    } catch (error) {
      setHealthStatus('error');
      setHealthMessage(`Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-container">
        <h1>Settings</h1>

        <div className="settings-section">
          <h2>Backend Configuration</h2>
          <div className="settings-field">
            <label htmlFor="api-url">API URL</label>
            <input
              id="api-url"
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrlState(e.target.value)}
              placeholder="http://localhost:8000"
            />
            <div className="settings-field-actions">
              <button type="button" onClick={handleSave} className="settings-button settings-button-primary">
                Save
              </button>
              <button type="button" onClick={handleTest} className="settings-button settings-button-secondary">
                Test Connection
              </button>
            </div>
          </div>

          {healthStatus && (
            <div className={`settings-status settings-status-${healthStatus}`}>
              {healthStatus === 'checking' && '⏳ '}
              {healthStatus === 'ok' && '✅ '}
              {healthStatus === 'error' && '❌ '}
              {healthMessage}
            </div>
          )}
        </div>

        <div className="settings-section">
          <h2>Azure AI Foundry</h2>
          <div className="settings-info">
            <p>
              Foundry connection is configured on the backend via environment variables:
            </p>
            <ul>
              <li>
                <code>FOUNDRY_PROJECT_CONNECTION_STRING</code> - Your Foundry project connection string
              </li>
              <li>
                <code>FOUNDRY_DEPLOYMENT_NAME</code> - Deployment name (default: gpt-4)
              </li>
            </ul>
            <p>
              <strong>Status:</strong>{' '}
              {foundryConfigured ? (
                <span className="settings-status-ok">✅ Configured</span>
              ) : (
                <span className="settings-status-error">
                  ❌ Not configured (click "Test Connection" to check)
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="settings-section">
          <h2>Environment Variables</h2>
          <div className="settings-info">
            <p>Backend requires the following environment variables:</p>
            <ul>
              <li>
                <code>FOUNDRY_PROJECT_CONNECTION_STRING</code> - Azure AI Foundry project connection string
              </li>
              <li>
                <code>FOUNDRY_DEPLOYMENT_NAME</code> - Model deployment name (optional, default: gpt-4)
              </li>
            </ul>
            <p>
              For local development, set these in your <code>.env</code> file or environment.
            </p>
            <p>
              For Azure Container Apps, configure these as environment variables in your container app settings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

