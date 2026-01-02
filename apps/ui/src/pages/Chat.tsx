/** Chat page component. */

/// <reference types="vite/client" />

declare global {
  interface Window {
    ENV?: Record<string, string>;
  }
}

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
  type SSEParameterRequest,
  type ToolCall,
  approveToolCall,
  provideParameters,
  setApiUrl,
  startChatSSE,
  stopRun,
  uploadFile,
} from '@agentic/ui-lib';
import './Chat.css';

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [attachedFiles, setAttachedFiles] = useState<FileUpload[]>([]);
  const [allFiles, setAllFiles] = useState<FileUpload[]>([]); // All uploaded files for message display
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [pendingToolCall, setPendingToolCall] = useState<{ runId: string; toolCall: ToolCall; partitionKey?: string } | null>(null);
  const [pendingParameterRequest, setPendingParameterRequest] = useState<SSEParameterRequest | null>(null);
  const [toasts, setToasts] = useState<Array<{ id: string; message: string; type: 'success' | 'error' | 'info' }>>([]);
  const [conversationId, setConversationId] = useState<string | null>(() => {
    // Initialize from sessionStorage on mount
    return sessionStorage.getItem('conversationId');
  });
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentContentRef = useRef<string>('');
  const toastIdCounterRef = useRef<number>(0);

  const addToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = `${Date.now()}-${++toastIdCounterRef.current}`;
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

      // Add user message to UI
      // Filter out null/undefined fileIds
      const validFileIds = files.map((f) => f.fileId).filter((id) => id != null && id !== '');
      const userMessage: ChatMessage = {
        role: 'user',
        content: message,
        fileIds: validFileIds.length > 0 ? validFileIds : undefined,
        id: Date.now().toString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      
      // Add files to allFiles for message display
      // Files already have dataUrl from attachedFiles, so preserve them
      // This ensures files remain visible below messages after sending
      setAllFiles((prev) => {
        // Merge new files with existing, avoiding duplicates
        const existingFileIds = new Set(prev.map((f) => f.fileId));
        const newFiles = files.filter((f) => !existingFileIds.has(f.fileId));
        // Files from attachedFiles already include dataUrl, so add them as-is
        return [...prev, ...newFiles];
      });
      // Keep attached files in composer after sending

      // Start streaming
      setIsStreaming(true);
      currentContentRef.current = '';

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      let runId: string | null = null;

      try {
        console.log('Sending message with conversationId:', conversationId);
        await startChatSSE({
          threadId: conversationId || undefined,
          messages: [userMessage], // Only send the new user message
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
              // Update conversationId if provided in response
              if (event.data.conversationId && event.data.conversationId !== conversationId) {
                console.log('Updating conversationId from message_done:', event.data.conversationId, 'previous:', conversationId);
                setConversationId(event.data.conversationId);
                sessionStorage.setItem('conversationId', event.data.conversationId);
              }
            } else if (event.type === 'parameter_request') {
              runId = event.data.runId;
              setCurrentRunId(runId);
              setPendingParameterRequest(event.data);
              // Clear any pending tool call - we need parameters first
              setPendingToolCall(null);
              // Show parameter form inline - don't show approval modal yet
            } else if (event.type === 'tool_call_requested') {
              runId = event.data.runId;
              setCurrentRunId(runId);
              // Clear parameter request if it exists (parameters have been provided)
              if (pendingParameterRequest && pendingParameterRequest.toolCallId === event.data.toolCall.id) {
                setPendingParameterRequest(null);
              }
              // Show approval modal
              setPendingToolCall({
                runId: event.data.runId,
                toolCall: event.data.toolCall,
                partitionKey: event.data.partitionKey,
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
              // Update conversationId if provided in response
              if (event.data.conversationId && event.data.conversationId !== conversationId) {
                console.log('Updating conversationId from done event:', event.data.conversationId, 'previous:', conversationId);
                setConversationId(event.data.conversationId);
                sessionStorage.setItem('conversationId', event.data.conversationId);
              } else if (!event.data.conversationId) {
                console.warn('Done event missing conversationId, current:', conversationId);
              }
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
    [conversationId, isStreaming, addToast],
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
        // Create data URL for images to display immediately
        let dataUrl: string | undefined;
        if (file.type.startsWith('image/')) {
          dataUrl = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result as string);
            reader.onerror = reject;
            reader.readAsDataURL(file);
          });
        }

        const uploaded = await uploadFile(file);
        // Add data URL to uploaded file for display in composer
        const fileWithPreview = { ...uploaded, dataUrl };
        setAttachedFiles((prev) => [...prev, fileWithPreview]);
        
        // Don't create preview messages - images should only show in composer before sending
        // Files will be added to allFiles when message is sent
        
        addToast(`File ${file.name} uploaded`, 'success');
      } catch (error) {
        addToast(`Failed to upload file: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      }
    },
    [addToast],
  );

  const handleRemoveFile = useCallback((fileId: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.fileId !== fileId));
    // Check if file is in any sent message before removing from allFiles
    setMessages((prev) => {
      const hasFileInSentMessage = prev.some((m) => 
        !m.id?.startsWith('preview-') && m.fileIds?.includes(fileId)
      );
      if (!hasFileInSentMessage) {
        // File not in any sent message, safe to remove from allFiles
        setAllFiles((current) => current.filter((f) => f.fileId !== fileId));
      }
      return prev;
    });
  }, []);

  const handleToolApprove = useCallback(async () => {
    if (!pendingToolCall) {
      return;
    }

    try {
      await approveToolCall(pendingToolCall.runId, pendingToolCall.toolCall.id, true, pendingToolCall.partitionKey);
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
      await approveToolCall(pendingToolCall.runId, pendingToolCall.toolCall.id, false, pendingToolCall.partitionKey);
      setPendingToolCall(null);
      setPendingParameterRequest(null);
      addToast('Tool call rejected', 'info');
      setIsStreaming(false);
      setCurrentRunId(null);
    } catch (error) {
      addToast(`Failed to reject tool: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    }
  }, [pendingToolCall, addToast]);

  const handleParametersSubmit = useCallback(
    async (parameters: Record<string, unknown>) => {
      if (!pendingParameterRequest) {
        return;
      }

      try {
        await provideParameters(
          pendingParameterRequest.runId,
          pendingParameterRequest.toolCallId,
          parameters,
        );
        addToast('Parameters submitted', 'success');
        // Keep pendingParameterRequest until tool_call_requested event clears it
        // The backend will emit tool_call_requested event after parameters are provided
      } catch (error) {
        addToast(
          `Failed to submit parameters: ${error instanceof Error ? error.message : 'Unknown error'}`,
          'error',
        );
      }
    },
    [pendingParameterRequest, addToast],
  );

  const handleParametersCancel = useCallback(() => {
    setPendingParameterRequest(null);
    setIsStreaming(false);
    setCurrentRunId(null);
  }, []);

  // Load API URL from localStorage or env
  useEffect(() => {
    const savedApiUrl = localStorage.getItem('apiUrl');
    if (savedApiUrl) {
      setApiUrl(savedApiUrl);
    } else {
      // Check window.ENV first (runtime config from env-config.js), then fall back to build-time env
      const envApiUrl = window.ENV?.VITE_API_URL || import.meta.env.VITE_API_URL;
      if (envApiUrl) {
        setApiUrl(envApiUrl);
      }
    }
  }, []);

  return (
    <div className="chat-page">
      <ChatShell title="Chat">
        <MessageList
          messages={messages}
          files={allFiles}
          pendingParameterRequest={pendingParameterRequest}
          onParametersSubmit={handleParametersSubmit}
          onParametersCancel={handleParametersCancel}
        />
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

