/** Fields list panel to display extracted fields from Document Intelligence */

import React from 'react';
import type { FieldEvidence } from '../utils/pdfCoordinates';
import './FieldsListPanel.css';

export interface FieldsListPanelProps {
  fields: FieldEvidence[];
  selectedField?: FieldEvidence | null;
  onFieldSelect?: (field: FieldEvidence) => void;
  className?: string;
}

export const FieldsListPanel: React.FC<FieldsListPanelProps> = ({
  fields,
  selectedField,
  onFieldSelect,
  className = '',
}) => {
  // Dummy fields for testing if no fields provided
  const dummyFields: FieldEvidence[] = [
    {
      fieldPath: 'invoice.invoiceNumber',
      value: 'INV-2024-001',
      confidence: 0.95,
      evidence: [
        {
          page: 1,
          polygon: [{ x: 100, y: 200 }, { x: 300, y: 200 }, { x: 300, y: 250 }, { x: 100, y: 250 }],
          sourceText: 'INV-2024-001',
          confidence: 0.95,
        },
      ],
    },
    {
      fieldPath: 'invoice.date',
      value: '2024-01-15',
      confidence: 0.88,
      evidence: [
        {
          page: 1,
          polygon: [{ x: 400, y: 200 }, { x: 550, y: 200 }, { x: 550, y: 250 }, { x: 400, y: 250 }],
          sourceText: '2024-01-15',
          confidence: 0.88,
        },
      ],
    },
    {
      fieldPath: 'invoice.totalAmount',
      value: '$1,234.56',
      confidence: 0.92,
      evidence: [
        {
          page: 1,
          polygon: [{ x: 450, y: 600 }, { x: 600, y: 600 }, { x: 600, y: 650 }, { x: 450, y: 650 }],
          sourceText: '$1,234.56',
          confidence: 0.92,
        },
      ],
    },
    {
      fieldPath: 'invoice.vendor.name',
      value: 'Acme Corporation',
      confidence: 0.85,
      evidence: [
        {
          page: 1,
          polygon: [{ x: 100, y: 100 }, { x: 350, y: 100 }, { x: 350, y: 150 }, { x: 100, y: 150 }],
          sourceText: 'Acme Corporation',
          confidence: 0.85,
        },
      ],
    },
    {
      fieldPath: 'invoice.items[0].description',
      value: 'Product A',
      confidence: 0.90,
      evidence: [
        {
          page: 1,
          polygon: [{ x: 100, y: 350 }, { x: 300, y: 350 }, { x: 300, y: 400 }, { x: 100, y: 400 }],
          sourceText: 'Product A',
          confidence: 0.90,
        },
      ],
    },
  ];

  const displayFields = fields.length > 0 ? fields : dummyFields;

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return 'fields-list-confidence-high';
    if (confidence >= 0.5) return 'fields-list-confidence-medium';
    return 'fields-list-confidence-low';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence > 0.8) return 'High';
    if (confidence >= 0.5) return 'Medium';
    return 'Low';
  };

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  return (
    <div className={`fields-list-panel ${className}`}>
      <div className="fields-list-header">
        <h3 className="fields-list-title">Extracted Fields</h3>
        <span className="fields-list-count">{displayFields.length} fields</span>
      </div>
      <div className="fields-list-content">
        {displayFields.length === 0 ? (
          <div className="fields-list-empty">No fields extracted</div>
        ) : (
          <div className="fields-list-items">
            {displayFields.map((field, index) => {
              const isSelected = selectedField?.fieldPath === field.fieldPath;
              return (
                <div
                  key={index}
                  className={`fields-list-item ${isSelected ? 'fields-list-item-selected' : ''}`}
                  onClick={() => onFieldSelect?.(field)}
                >
                  <div className="fields-list-item-header">
                    <div className="fields-list-item-path">{field.fieldPath}</div>
                    <div className={`fields-list-item-confidence ${getConfidenceColor(field.confidence)}`}>
                      {getConfidenceLabel(field.confidence)}
                    </div>
                  </div>
                  <div className="fields-list-item-value">{formatValue(field.value)}</div>
                  {field.evidence && field.evidence.length > 0 && (
                    <div className="fields-list-item-evidence">
                      {field.evidence.length} evidence{field.evidence.length > 1 ? 's' : ''} found
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};


