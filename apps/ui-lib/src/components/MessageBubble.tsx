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

  return (
    <div className={`message-bubble message-bubble-${message.role}`}>
      <div className="message-bubble-header">
        <span className="message-bubble-role">
          {isUser ? 'You' : isAssistant ? 'Assistant' : isTool ? 'Tool' : 'System'}
        </span>
      </div>
      {messageFiles.length > 0 && (
        <div className="message-bubble-files">
          {messageFiles.map((file) => (
            <div key={file.fileId} className="message-bubble-file-chip">
              📎 {file.filename}
            </div>
          ))}
        </div>
      )}
      <div className="message-bubble-content">{message.content}</div>
    </div>
  );
};

