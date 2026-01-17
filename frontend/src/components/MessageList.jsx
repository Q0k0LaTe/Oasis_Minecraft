/**
 * MessageList - Display chat messages
 */

import React from 'react';

export default function MessageList({ messages }) {
  if (!messages || messages.length === 0) {
    return (
      <div className="message-list empty">
        <div className="empty-state">
          <p>No messages yet</p>
          <p className="hint">Start by describing what you want to create!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <MessageBubble key={message.id || index} message={message} />
      ))}
    </div>
  );
}

/**
 * MessageBubble - Single message display
 */
function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isSystem = message.role === 'system';

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={`message ${isUser ? 'user' : ''} ${isAssistant ? 'assistant' : ''} ${isSystem ? 'system' : ''}`}>
      <div className="message-header">
        <span className="message-role">
          {isUser ? 'You' : isAssistant ? 'AI Assistant' : 'System'}
        </span>
        <span className="message-time">{formatTime(message.created_at)}</span>
      </div>
      <div className="message-content">
        {message.content_type === 'json' ? (
          <pre className="message-json">
            {typeof message.content === 'string' 
              ? message.content 
              : JSON.stringify(message.content, null, 2)}
          </pre>
        ) : (
          <p>{message.content}</p>
        )}
      </div>
    </div>
  );
}

