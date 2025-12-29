/** Chat shell layout component. */

import React from 'react';
import './ChatShell.css';

export interface ChatShellProps {
  children: React.ReactNode;
  title?: string;
}

export const ChatShell: React.FC<ChatShellProps> = ({ children, title = 'Chat' }) => {
  return (
    <div className="chat-shell">
      {title && <div className="chat-shell-header">{title}</div>}
      <div className="chat-shell-content">{children}</div>
    </div>
  );
};

