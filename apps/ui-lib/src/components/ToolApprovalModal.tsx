/** Tool approval modal component. */

import React from 'react';
import type { ToolCall } from '../types/chat.types';
import './ToolApprovalModal.css';

export interface ToolApprovalModalProps {
  toolCall: ToolCall;
  runId: string;
  onApprove: () => void;
  onReject: () => void;
}

export const ToolApprovalModal: React.FC<ToolApprovalModalProps> = ({
  toolCall,
  runId,
  onApprove,
  onReject,
}) => {
  let argumentsObj: unknown;
  try {
    argumentsObj = JSON.parse(toolCall.argumentsJson);
  } catch {
    argumentsObj = toolCall.argumentsJson;
  }

  return (
    <div className="tool-approval-modal-overlay">
      <div className="tool-approval-modal">
        <h2 className="tool-approval-modal-title">Tool Call Approval Required</h2>
        <div className="tool-approval-modal-content">
          <p>
            The assistant wants to call the tool <strong>{toolCall.name}</strong>.
          </p>
          <div className="tool-approval-modal-details">
            <div className="tool-approval-modal-detail">
              <strong>Tool:</strong> {toolCall.name}
            </div>
            <div className="tool-approval-modal-detail">
              <strong>Arguments:</strong>
              <pre className="tool-approval-modal-arguments">
                {JSON.stringify(argumentsObj, null, 2)}
              </pre>
            </div>
            <div className="tool-approval-modal-detail">
              <strong>Run ID:</strong> {runId}
            </div>
          </div>
          <div className="tool-approval-modal-actions">
            <button
              type="button"
              className="tool-approval-modal-button tool-approval-modal-button-approve"
              onClick={onApprove}
            >
              Approve
            </button>
            <button
              type="button"
              className="tool-approval-modal-button tool-approval-modal-button-reject"
              onClick={onReject}
            >
              Reject
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

