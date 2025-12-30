/** Message list component. */

import React, { useEffect, useRef } from 'react';
<<<<<<< HEAD
import type { ChatMessage, FileUpload, SSEParameterRequest } from '../types/chat.types';
import { MessageBubble } from './MessageBubble';
import { ParameterInputForm } from './ParameterInputForm';
=======
import type { ChatMessage, FileUpload } from '../types/chat.types';
import { MessageBubble } from './MessageBubble';
>>>>>>> origin/main
import './MessageList.css';

export interface MessageListProps {
  messages: ChatMessage[];
  files?: FileUpload[];
<<<<<<< HEAD
  pendingParameterRequest?: SSEParameterRequest | null;
  onParametersSubmit?: (parameters: Record<string, unknown>) => void;
  onParametersCancel?: () => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  files = [],
  pendingParameterRequest,
  onParametersSubmit,
  onParametersCancel,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when messages change or parameter request appears
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pendingParameterRequest]);

  return (
    <div className="message-list">
      {messages.length === 0 && !pendingParameterRequest ? (
        <div className="message-list-empty">No messages yet. Start a conversation!</div>
      ) : (
        <>
          {messages.map((message, index) => (
            <MessageBubble key={message.id || index} message={message} files={files} />
          ))}
          {pendingParameterRequest && (
            <div className="message-list-parameter-form">
              <ParameterInputForm
                toolName={pendingParameterRequest.toolName}
                parameters={pendingParameterRequest.missingParameters}
                onSubmit={onParametersSubmit || (() => {})}
                onCancel={onParametersCancel}
              />
            </div>
          )}
        </>
=======
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
>>>>>>> origin/main
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

