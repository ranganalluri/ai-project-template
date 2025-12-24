/** Chat page component. */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ChatShell,
  Composer,
  MessageList,
  ToolApprovalModal,
  ToastContainer,
  type ChatMessage,
  type FileUpload,
  type SSEEvent,
  type ToolCall,
  approveToolCall,
  setApiUrl,
  startChatSSE,
  stopRun,
  uploadFile,
} from '@agentic/ui-lib';
import './Chat.css';

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [attachedFiles, setAttachedFiles] = useState<FileUpload[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [pendingToolCall, setPendingToolCall] = useState<{ runId: string; toolCall: ToolCall } | null>(null);
  const [toasts, setToasts] = useState<Array<{ id: string; message: string; type: 'success' | 'error' | 'info' }>>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentContentRef = useRef<string>('');

  const addToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const handleSend = useCallback(
    async (message: string, files: FileUpload[]) => {
      if (isStreaming) {
        return;
      }

      // Add user message
      const userMessage: ChatMessage = {
        role: 'user',
        content: message,
        fileIds: files.map((f) => f.fileId),
        id: Date.now().toString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Start streaming
      setIsStreaming(true);
      currentContentRef.current = '';

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      let runId: string | null = null;

      try {
        await startChatSSE({
          messages: [...messages, userMessage],
          files,
          onEvent: (event: SSEEvent) => {
            if (event.type === 'message_delta') {
              currentContentRef.current += event.data.deltaText;
              // Update the last assistant message or create new one
              setMessages((prev) => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant') {
                  lastMessage.content = currentContentRef.current;
                  return newMessages;
                } else {
                  return [
                    ...newMessages,
                    {
                      role: 'assistant',
                      content: currentContentRef.current,
                      id: event.data.runId,
                    },
                  ];
                }
              });
            } else if (event.type === 'message_done') {
              currentContentRef.current = event.data.message.content;
              setMessages((prev) => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant') {
                  lastMessage.content = event.data.message.content;
                  lastMessage.id = event.data.runId;
                  return newMessages;
                } else {
                  return [...newMessages, { ...event.data.message, id: event.data.runId }];
                }
              });
            } else if (event.type === 'tool_call_requested') {
              runId = event.data.runId;
              setCurrentRunId(runId);
              setPendingToolCall({
                runId: event.data.runId,
                toolCall: event.data.toolCall,
              });
              // Pause streaming UI - modal will handle approval
            } else if (event.type === 'tool_call_result') {
              // Tool was executed, continue streaming
              addToast(`Tool ${event.data.toolCallId} executed successfully`, 'success');
            } else if (event.type === 'error') {
              addToast(event.data.message, 'error');
              setIsStreaming(false);
              setCurrentRunId(null);
            } else if (event.type === 'done') {
              setIsStreaming(false);
              setCurrentRunId(null);
              currentContentRef.current = '';
            }
          },
          onError: (error) => {
            addToast(`Error: ${error.message}`, 'error');
            setIsStreaming(false);
            setCurrentRunId(null);
          },
          signal: abortController.signal,
        });
      } catch (error) {
        addToast(`Failed to start chat: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
        setIsStreaming(false);
        setCurrentRunId(null);
      }
    },
    [messages, isStreaming, addToast],
  );

  const handleStop = useCallback(async () => {
    if (currentRunId) {
      try {
        await stopRun(currentRunId);
        abortControllerRef.current?.abort();
        setIsStreaming(false);
        setCurrentRunId(null);
        addToast('Chat stopped', 'info');
      } catch (error) {
        addToast(`Failed to stop: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      }
    }
  }, [currentRunId, addToast]);

  const handleFileSelect = useCallback(
    async (file: File) => {
      try {
        const uploaded = await uploadFile(file);
        setAttachedFiles((prev) => [...prev, uploaded]);
        addToast(`File ${file.name} uploaded`, 'success');
      } catch (error) {
        addToast(`Failed to upload file: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      }
    },
    [addToast],
  );

  const handleRemoveFile = useCallback((fileId: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.fileId !== fileId));
  }, []);

  const handleToolApprove = useCallback(async () => {
    if (!pendingToolCall) {
      return;
    }

    try {
      await approveToolCall(pendingToolCall.runId, pendingToolCall.toolCall.id, true);
      setPendingToolCall(null);
      addToast('Tool call approved', 'success');
      // Streaming will continue automatically
    } catch (error) {
      addToast(`Failed to approve tool: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    }
  }, [pendingToolCall, addToast]);

  const handleToolReject = useCallback(async () => {
    if (!pendingToolCall) {
      return;
    }

    try {
      await approveToolCall(pendingToolCall.runId, pendingToolCall.toolCall.id, false);
      setPendingToolCall(null);
      addToast('Tool call rejected', 'info');
      setIsStreaming(false);
      setCurrentRunId(null);
    } catch (error) {
      addToast(`Failed to reject tool: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    }
  }, [pendingToolCall, addToast]);

  // Load API URL from localStorage or env
  useEffect(() => {
    const savedApiUrl = localStorage.getItem('apiUrl');
    if (savedApiUrl) {
      setApiUrl(savedApiUrl);
    } else {
      const envApiUrl = import.meta.env.VITE_API_URL;
      if (envApiUrl) {
        setApiUrl(envApiUrl);
      }
    }
  }, []);

  return (
    <div className="chat-page">
      <ChatShell title="Chat">
        <MessageList messages={messages} files={attachedFiles} />
        <Composer
          onSend={handleSend}
          onStop={handleStop}
          isStreaming={isStreaming}
          attachedFiles={attachedFiles}
          onRemoveFile={handleRemoveFile}
          onFileSelect={handleFileSelect}
        />
      </ChatShell>
      {pendingToolCall && (
        <ToolApprovalModal
          toolCall={pendingToolCall.toolCall}
          runId={pendingToolCall.runId}
          onApprove={handleToolApprove}
          onReject={handleToolReject}
        />
      )}
      <ToastContainer
        toasts={toasts.map((t) => ({ ...t, duration: 3000 }))}
        onRemove={removeToast}
      />
    </div>
  );
};

