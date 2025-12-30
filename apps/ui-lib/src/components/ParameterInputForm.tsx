/** Parameter input form component for collecting missing tool parameters. */

import React, { useState } from 'react';
import './ParameterInputForm.css';

export interface ParameterInfo {
  name: string;
  type: string;
  description: string;
  llmExplanation?: string;
}

export interface ParameterInputFormProps {
  toolName: string;
  parameters: ParameterInfo[];
  onSubmit: (parameters: Record<string, unknown>) => void;
  onCancel?: () => void;
}

export const ParameterInputForm: React.FC<ParameterInputFormProps> = ({
  toolName,
  parameters,
  onSubmit,
  onCancel,
}) => {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (paramName: string, value: string) => {
    setFormData((prev) => ({ ...prev, [paramName]: value }));
    // Clear error when user starts typing
    if (errors[paramName]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[paramName];
        return newErrors;
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    for (const param of parameters) {
      const value = formData[param.name]?.trim();
      if (!value) {
        newErrors[param.name] = 'This parameter is required';
        continue;
      }

      // Type validation
      if (param.type === 'number' || param.type === 'integer') {
        const numValue = Number(value);
        if (isNaN(numValue)) {
          newErrors[param.name] = `Must be a valid ${param.type}`;
        }
      } else if (param.type === 'boolean') {
        if (value !== 'true' && value !== 'false') {
          newErrors[param.name] = 'Must be true or false';
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) {
      return;
    }

    // Convert form data to proper types
    const typedData: Record<string, unknown> = {};
    for (const param of parameters) {
      const value = formData[param.name]?.trim();
      if (param.type === 'number' || param.type === 'integer') {
        typedData[param.name] = Number(value);
      } else if (param.type === 'boolean') {
        typedData[param.name] = value === 'true';
      } else {
        typedData[param.name] = value;
      }
    }

    onSubmit(typedData);
  };

  const renderInput = (param: ParameterInfo) => {
    const value = formData[param.name] || '';
    const error = errors[param.name];

    if (param.type === 'boolean') {
      return (
        <select
          className={`parameter-input-form-field ${error ? 'parameter-input-form-field-error' : ''}`}
          value={value}
          onChange={(e) => handleChange(param.name, e.target.value)}
        >
          <option value="">Select...</option>
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
      );
    }

    if (param.type === 'number' || param.type === 'integer') {
      return (
        <input
          type="number"
          className={`parameter-input-form-field ${error ? 'parameter-input-form-field-error' : ''}`}
          value={value}
          onChange={(e) => handleChange(param.name, e.target.value)}
          placeholder={`Enter ${param.type}...`}
        />
      );
    }

    // Default to text input
    return (
      <input
        type="text"
        className={`parameter-input-form-field ${error ? 'parameter-input-form-field-error' : ''}`}
        value={value}
        onChange={(e) => handleChange(param.name, e.target.value)}
        placeholder={`Enter ${param.name}...`}
      />
    );
  };

  return (
    <div className="parameter-input-form">
      <div className="parameter-input-form-header">
        <h3 className="parameter-input-form-title">Missing Parameters for {toolName}</h3>
        <p className="parameter-input-form-subtitle">Please provide the following required parameters:</p>
      </div>

      <form onSubmit={handleSubmit} className="parameter-input-form-form">
        {parameters.map((param) => (
          <div key={param.name} className="parameter-input-form-group">
            <label className="parameter-input-form-label">
              {param.name}
              <span className="parameter-input-form-type">({param.type})</span>
              <span className="parameter-input-form-required">*</span>
            </label>

            {param.llmExplanation && (
              <div className="parameter-input-form-explanation">
                <div className="parameter-input-form-explanation-icon">💡</div>
                <div className="parameter-input-form-explanation-text">{param.llmExplanation}</div>
              </div>
            )}

            {param.description && !param.llmExplanation && (
              <div className="parameter-input-form-description">{param.description}</div>
            )}

            {renderInput(param)}

            {errors[param.name] && (
              <div className="parameter-input-form-error">{errors[param.name]}</div>
            )}
          </div>
        ))}

        <div className="parameter-input-form-actions">
          {onCancel && (
            <button type="button" className="parameter-input-form-button-cancel" onClick={onCancel}>
              Cancel
            </button>
          )}
          <button type="submit" className="parameter-input-form-button-submit">
            Submit Parameters
          </button>
        </div>
      </form>
    </div>
  );
};

