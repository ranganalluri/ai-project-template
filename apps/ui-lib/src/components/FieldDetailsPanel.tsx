/** Field details panel to display selected field information */

import React from 'react';
import { FieldEvidence } from '../utils/pdfCoordinates';
import './FieldDetailsPanel.css';

export interface FieldDetailsPanelProps {
  field: FieldEvidence | null;
  onClose?: () => void;
  className?: string;
}

export const FieldDetailsPanel: React.FC<FieldDetailsPanelProps> = ({
  field,
  onClose,
  className = '',
}) => {
  if (!field) {
    return null;
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return 'text-green-600';
    if (confidence >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence > 0.8) return 'High';
    if (confidence >= 0.5) return 'Medium';
    return 'Low';
  };

  return (
    <div className={`field-details-panel ${className}`}>
      <div className="field-details-header">
        <h3 className="field-details-title">Field Details</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="field-details-close"
            aria-label="Close field details"
          >
            ×
          </button>
        )}
      </div>

      <div className="field-details-content">
        <div className="field-details-section">
          <label className="field-details-label">Field Path</label>
          <p className="field-details-value">{field.fieldPath}</p>
        </div>

        <div className="field-details-section">
          <label className="field-details-label">Value</label>
          <p className="field-details-value">
            {typeof field.value === 'object' ? JSON.stringify(field.value, null, 2) : String(field.value)}
          </p>
        </div>

        <div className="field-details-section">
          <label className="field-details-label">Confidence</label>
          <p className={`field-details-value ${getConfidenceColor(field.confidence)}`}>
            {getConfidenceLabel(field.confidence)} ({(field.confidence * 100).toFixed(1)}%)
          </p>
        </div>

        {field.evidence && field.evidence.length > 0 && (
          <div className="field-details-section">
            <label className="field-details-label">Evidence</label>
            <div className="field-details-evidence">
              {field.evidence.map((ev, index) => (
                <div key={index} className="field-details-evidence-item">
                  <div className="field-details-evidence-header">
                    <span>Page {ev.page}</span>
                    <span className={getConfidenceColor(ev.confidence)}>
                      {(ev.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  {ev.sourceText && (
                    <p className="field-details-evidence-text">{ev.sourceText}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};



