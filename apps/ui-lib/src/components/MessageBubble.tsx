/** Message bubble component. */

import React from 'react';
import type { ChatMessage, FileUpload } from '../types/chat.types';
import './MessageBubble.css';

export interface MessageBubbleProps {
  message: ChatMessage;
  files?: FileUpload[];
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, files = [] }) => {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isTool = message.role === 'tool';

  const messageFiles = message.fileIds
    ? files.filter((f) => message.fileIds?.includes(f.fileId))
    : [];

  const getAvatarText = () => {
    if (isUser) return 'U';
    if (isAssistant) return 'AI';
    if (isTool) return 'T';
    return 'S';
  };

  return (
    <div className={`message-bubble message-bubble-${message.role}`}>
      {!isUser && <div className="message-bubble-avatar">{getAvatarText()}</div>}
      <div className="message-bubble-content-wrapper">
        <div className="message-bubble-header">
          <span className="message-bubble-role">
            {isUser ? 'You' : isAssistant ? 'Assistant' : isTool ? 'Tool' : 'System'}
          </span>
        </div>
        <div className="message-bubble-content">{message.content}</div>
        {messageFiles.length > 0 && (
          <div className="message-bubble-files">
            {messageFiles.map((file, index) => (
              <div key={file.fileId || `file-${index}`} className="message-bubble-file-chip" title={file.fileName}>
                📎 {file.fileName || 'Unknown file'}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

