/** Schema panel to display extracted schema JSON */

import React, { useEffect, useState } from 'react';
import './SchemaPanel.css';

export interface SchemaPanelProps {
  schemaBlobUrl?: string | null;
  selectedFieldPath?: string | null;
  className?: string;
}

export const SchemaPanel: React.FC<SchemaPanelProps> = ({
  schemaBlobUrl,
  selectedFieldPath,
  className = '',
}) => {
  const [schema, setSchema] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!schemaBlobUrl) {
      setSchema(null);
      return;
    }

    setLoading(true);
    setError(null);

    fetch(schemaBlobUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to fetch schema: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        setSchema(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load schema');
        setLoading(false);
      });
  }, [schemaBlobUrl]);

  if (!schemaBlobUrl) {
    return (
      <div className={`schema-panel ${className}`}>
        <div className="schema-panel-header">
          <h3 className="schema-panel-title">Extracted Schema</h3>
        </div>
        <div className="schema-panel-content">
          <p className="schema-panel-empty">No schema available</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={`schema-panel ${className}`}>
        <div className="schema-panel-header">
          <h3 className="schema-panel-title">Extracted Schema</h3>
        </div>
        <div className="schema-panel-content">
          <p className="schema-panel-loading">Loading schema...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`schema-panel ${className}`}>
        <div className="schema-panel-header">
          <h3 className="schema-panel-title">Extracted Schema</h3>
        </div>
        <div className="schema-panel-content">
          <p className="schema-panel-error">{error}</p>
        </div>
      </div>
    );
  }

  // Helper function to get value by field path
  const getValueByPath = (obj: any, path: string): any => {
    const parts = path.split('.');
    let current = obj;
    for (const part of parts) {
      if (current && typeof current === 'object' && part in current) {
        current = current[part];
      } else {
        return undefined;
      }
    }
    return current;
  };

  const selectedValue = selectedFieldPath ? getValueByPath(schema, selectedFieldPath) : undefined;

  return (
    <div className={`schema-panel ${className}`}>
      <div className="schema-panel-header">
        <h3 className="schema-panel-title">Extracted Schema</h3>
      </div>
      <div className="schema-panel-content">
        {selectedFieldPath && selectedValue !== undefined && (
          <div className="schema-panel-selected">
            <div className="schema-panel-selected-header">
              <span className="schema-panel-selected-label">Selected Field:</span>
              <span className="schema-panel-selected-path">{selectedFieldPath}</span>
            </div>
            <div className="schema-panel-selected-value">
              <pre>{JSON.stringify(selectedValue, null, 2)}</pre>
            </div>
          </div>
        )}
        <div className="schema-panel-json">
          <pre>{JSON.stringify(schema, null, 2)}</pre>
        </div>
      </div>
    </div>
  );
};



