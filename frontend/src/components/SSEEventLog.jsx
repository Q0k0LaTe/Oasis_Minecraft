/**
 * SSEEventLog - Display SSE events in a timeline format
 * 
 * Shows real-time events from the backend with inline actions for approval workflow.
 */

import React from 'react';

export default function SSEEventLog({ 
  events, 
  artifacts, 
  onDownload,
  onApprove,
  onReject,
  runStatus 
}) {
  if ((!events || events.length === 0) && (!artifacts || artifacts.length === 0)) {
    return (
      <div className="sse-event-log empty">
        <div className="empty-state">
          <p>No events yet</p>
          <p className="hint">Events will appear here when processing starts</p>
        </div>
      </div>
    );
  }

  return (
    <div className="sse-event-log">
      {/* Inline Approval Actions - shown when awaiting_approval */}
      {runStatus === 'awaiting_approval' && onApprove && onReject && (
        <div className="inline-approval-actions">
          <div className="approval-prompt">
            <span className="approval-icon">⏳</span>
            <span>AI is waiting for your approval to continue</span>
          </div>
          <div className="approval-buttons">
            <button className="btn btn-sm btn-success" onClick={() => onApprove()}>
              ✓ Approve
            </button>
            <button className="btn btn-sm btn-danger" onClick={() => onReject()}>
              ✗ Reject
            </button>
          </div>
        </div>
      )}

      {/* Events Timeline */}
      <div className="event-timeline">
        {events.map((event) => (
          <EventItem key={event.id} event={event} />
        ))}
      </div>

      {/* Artifacts Section */}
      {artifacts && artifacts.length > 0 && (
        <div className="artifacts-section">
          <h4>Build Artifacts</h4>
          <div className="artifacts-list">
            {artifacts.map((artifact, index) => (
              <div key={artifact.id || index} className="artifact-item">
                <span className="artifact-icon">📦</span>
                <span className="artifact-name">{artifact.file_name}</span>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={() => onDownload(artifact)}
                >
                  Download
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * EventItem - Single event display
 */
function EventItem({ event }) {
  const { type, payload, level, timestamp } = event;

  const getEventIcon = () => {
    switch (type) {
      case 'run.status':
        return payload?.status === 'succeeded' ? '✅' : 
               payload?.status === 'failed' ? '❌' : '🔄';
      case 'run.progress':
        return '📊';
      case 'log.append':
        return level === 'error' ? '❌' : 
               level === 'warning' ? '⚠️' : '📝';
      case 'spec.preview':
        return '👁️';
      case 'spec.saved':
        return '💾';
      case 'run.awaiting_approval':
        return '⏳';
      case 'run.awaiting_input':
        return '❓';
      case 'artifact.created':
        return '📦';
      case 'error':
        return '❌';
      default:
        return '📌';
    }
  };

  const getEventTitle = () => {
    switch (type) {
      case 'run.status':
        return `Status: ${payload?.status || 'unknown'}`;
      case 'run.progress':
        return `Progress: ${payload?.progress || 0}%`;
      case 'log.append':
        return payload?.message || 'Log message';
      case 'spec.preview':
        return `Delta preview (${payload?.delta_index + 1}/${payload?.total_deltas})`;
      case 'spec.saved':
        return `Spec saved (v${payload?.spec_version})`;
      case 'run.awaiting_approval':
        return `Awaiting approval (${payload?.deltas_count} changes)`;
      case 'run.awaiting_input':
        return 'AI needs clarification';
      case 'artifact.created':
        return `Artifact: ${payload?.file_name}`;
      case 'error':
        return `Error: ${payload?.message}`;
      default:
        return type;
    }
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    const date = new Date(ts);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getLevelClass = () => {
    if (level === 'error' || type === 'error') return 'error';
    if (level === 'warning' || type === 'run.awaiting_approval' || type === 'run.awaiting_input') return 'warning';
    if (level === 'success' || type === 'spec.saved' || type === 'artifact.created') return 'success';
    if (type === 'run.status' && payload?.status === 'succeeded') return 'success';
    if (type === 'run.status' && payload?.status === 'failed') return 'error';
    return 'info';
  };

  return (
    <div className={`event-item ${getLevelClass()}`}>
      <div className="event-icon">{getEventIcon()}</div>
      <div className="event-content">
        <div className="event-title">{getEventTitle()}</div>
        {type === 'spec.preview' && payload?.delta && (
          <div className="event-detail">
            <code>{JSON.stringify(payload.delta, null, 2)}</code>
          </div>
        )}
        {type === 'log.append' && payload?.phase && (
          <div className="event-phase">Phase: {payload.phase}</div>
        )}
      </div>
      <div className="event-time">{formatTime(timestamp)}</div>
    </div>
  );
}

