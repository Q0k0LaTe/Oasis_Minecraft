/**
 * ConversationPanel - Right column with chat, SSE events, and message input
 */

import React, { useState, useRef, useEffect } from 'react';
import MessageList from './MessageList.jsx';
import MessageInput from './MessageInput.jsx';
import SSEEventLog from './SSEEventLog.jsx';

export default function ConversationPanel({
  conversations,
  activeConversationId,
  onSelectConversation,
  messages,
  events,
  sseStatus,
  runStatus,
  progress,
  artifacts,
  onSendMessage,
  onReconnect,
  onDownload,
  onApprove,
  onReject,
  isSending,
}) {
  const [activeTab, setActiveTab] = useState('conversation');
  const messageListRef = useRef(null);
  const eventLogRef = useRef(null);

  // Auto-scroll messages when new ones arrive
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  // Auto-scroll events when new ones arrive
  useEffect(() => {
    if (eventLogRef.current) {
      eventLogRef.current.scrollTop = eventLogRef.current.scrollHeight;
    }
  }, [events]);

  // Auto-switch to events tab when SSE is active
  useEffect(() => {
    if (sseStatus === 'connected' || sseStatus === 'connecting') {
      setActiveTab('events');
    }
  }, [sseStatus]);

  return (
    <div className="conversation-panel">
      {/* Tabs */}
      <div className="panel-tabs">
        <button
          className={`tab ${activeTab === 'conversation' ? 'active' : ''}`}
          onClick={() => setActiveTab('conversation')}
        >
          Main Conversation
          {messages.length > 0 && (
            <span className="tab-badge">{messages.length}</span>
          )}
        </button>
        <button
          className={`tab ${activeTab === 'events' ? 'active' : ''}`}
          onClick={() => setActiveTab('events')}
        >
          Events
          {events.length > 0 && (
            <span className="tab-badge">{events.length}</span>
          )}
        </button>
      </div>

      {/* Status Bar */}
      {(runStatus || sseStatus !== 'idle') && (
        <div className="status-bar">
          <div className="status-info">
            <span className={`status-dot status-${sseStatus}`}></span>
            <span className="status-text">
              {runStatus === 'running' && 'Processing...'}
              {runStatus === 'awaiting_approval' && 'Awaiting approval'}
              {runStatus === 'awaiting_input' && 'Waiting for input'}
              {runStatus === 'succeeded' && 'Completed'}
              {runStatus === 'failed' && 'Failed'}
              {runStatus === 'queued' && 'Queued'}
              {!runStatus && sseStatus === 'connecting' && 'Connecting...'}
              {!runStatus && sseStatus === 'disconnected' && 'Disconnected'}
            </span>
          </div>
          {progress > 0 && progress < 100 && (
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
          {sseStatus === 'disconnected' && (
            <button className="btn btn-sm btn-ghost" onClick={onReconnect}>
              Reconnect
            </button>
          )}
        </div>
      )}

      {/* Content Area */}
      <div className="panel-content">
        {activeTab === 'conversation' ? (
          <div className="message-container" ref={messageListRef}>
            <MessageList messages={messages} />
          </div>
        ) : (
          <div className="event-container" ref={eventLogRef}>
            <SSEEventLog 
              events={events} 
              artifacts={artifacts}
              onDownload={onDownload}
              onApprove={onApprove}
              onReject={onReject}
              runStatus={runStatus}
            />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="panel-input">
        <MessageInput
          onSend={onSendMessage}
          disabled={isSending || runStatus === 'running'}
          placeholder={
            runStatus === 'running' 
              ? 'Processing...' 
              : 'Describe what you want to create...'
          }
        />
      </div>
    </div>
  );
}

