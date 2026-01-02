/** Chat composer component. */

import React, { useState } from 'react';
import type { FileUpload } from '../types/chat.types';
import { FileUploadButton } from './FileUploadButton';
import './Composer.css';

export interface ComposerProps {
  onSend: (message: string, files: FileUpload[]) => void;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  attachedFiles?: FileUpload[];
  onRemoveFile?: (fileId: string) => void;
  onFileSelect?: (file: File) => void;
}

export const Composer: React.FC<ComposerProps> = ({
  onSend,
  onStop,
  isStreaming = false,
  disabled = false,
  attachedFiles = [],
  onRemoveFile,
  onFileSelect,
}) => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if ((message.trim() || attachedFiles.length > 0) && !disabled) {
      onSend(message.trim(), attachedFiles);
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (file: File) => {
    if (onFileSelect) {
      onFileSelect(file);
    }
  };

  return (
    <div className="composer">
      {attachedFiles.length > 0 && (
        <div className="composer-files">
          {attachedFiles.map((file, index) => {
            const isImage = file.contentType.startsWith('image/');
            return (
              <div key={file.fileId || `file-${index}`} className="composer-file-chip">
                {isImage && file.dataUrl ? (
                  <img src={file.dataUrl} alt={file.fileName} className="composer-file-thumbnail" />
                ) : (
                  <span className="composer-file-icon">📎</span>
                )}
                <span className="composer-file-name">{file.fileName}</span>
                {onRemoveFile && (
                  <button
                    type="button"
                    className="composer-file-remove"
                    onClick={() => onRemoveFile(file.fileId)}
                    aria-label="Remove file"
                  >
                    ×
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
      <div className="composer-input-container">
        <FileUploadButton onFileSelect={handleFileSelect} disabled={disabled || isStreaming} />
        <textarea
          className="composer-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
          disabled={disabled || isStreaming}
          rows={1}
        />
        {isStreaming && onStop ? (
          <button
            type="button"
            className="composer-button composer-button-stop"
            onClick={onStop}
            disabled={disabled}
          >
            Stop
          </button>
        ) : (
          <button
            type="button"
            className="composer-button composer-button-send"
            onClick={handleSend}
            disabled={disabled || isStreaming || (!message.trim() && attachedFiles.length === 0)}
          >
            Send
          </button>
        )}
      </div>
    </div>
  );
};

