/** Message list component. */

import React, { useEffect, useRef } from 'react';
import type { ChatMessage, FileUpload } from '../types/chat.types';
import { MessageBubble } from './MessageBubble';
import './MessageList.css';

export interface MessageListProps {
  messages: ChatMessage[];
  files?: FileUpload[];
}

export const MessageList: React.FC<MessageListProps> = ({ messages, files = [] }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.length === 0 ? (
        <div className="message-list-empty">No messages yet. Start a conversation!</div>
      ) : (
        messages.map((message, index) => (
          <MessageBubble key={message.id || index} message={message} files={files} />
        ))
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

