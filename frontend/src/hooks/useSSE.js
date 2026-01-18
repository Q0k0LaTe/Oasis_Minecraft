/**
 * useSSE - Custom hook for SSE event subscription
 * Uses fetch + ReadableStream because EventSource doesn't support Authorization headers
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { subscribeToSSE } from '../api/runs.js';

/**
 * SSE Event types
 */
export const SSE_EVENT_TYPES = {
  STATUS: 'run.status',
  PROGRESS: 'run.progress',
  LOG: 'log.append',
  SPEC_PREVIEW: 'spec.preview',
  SPEC_SAVED: 'spec.saved',
  AWAITING_APPROVAL: 'run.awaiting_approval',
  AWAITING_INPUT: 'run.awaiting_input',
  ARTIFACT: 'artifact.created',
  TEXTURE_SELECTION_REQUIRED: 'texture.selection_required',
  TEXTURE_SELECTED: 'texture.selected',
};

/**
 * useSSE hook
 *
 * @param {string|null} runId - Run ID to subscribe to (null to disable)
 * @param {object} options - Configuration options
 * @param {function} [options.onSpecSaved] - Callback when spec is saved
 * @param {function} [options.onArtifact] - Callback when artifact is created
 * @param {function} [options.onTextureSelectionRequired] - Callback when texture selection is needed
 * @param {boolean} [options.autoReconnect=true] - Whether to auto-reconnect on disconnect
 * @returns {object} - SSE state and controls
 */
export function useSSE(runId, options = {}) {
  const { onSpecSaved, onArtifact, onTextureSelectionRequired, autoReconnect = true } = options;

  // State
  const [status, setStatus] = useState('idle'); // idle, connecting, connected, disconnected, error
  const [runStatus, setRunStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [events, setEvents] = useState([]);
  const [pendingDeltas, setPendingDeltas] = useState([]);
  const [clarifyingQuestions, setClarifyingQuestions] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [pendingTextures, setPendingTextures] = useState({});
  const [error, setError] = useState(null);

  // Refs
  const cleanupRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptRef = useRef(0);

  // Add event to the log
  const addEvent = useCallback((type, payload, level = 'info') => {
    const event = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      payload,
      level,
      timestamp: new Date().toISOString(),
    };
    setEvents(prev => [...prev, event]);
    return event;
  }, []);

  // Clear events
  const clearEvents = useCallback(() => {
    setEvents([]);
    setPendingDeltas([]);
    setClarifyingQuestions([]);
    setArtifacts([]);
    setPendingTextures({});
    setProgress(0);
    setRunStatus(null);
  }, []);

  // Disconnect from SSE
  const disconnect = useCallback(() => {
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setStatus('disconnected');
  }, []);

  // Connect to SSE
  const connect = useCallback(() => {
    if (!runId) return;

    // Clean up existing connection
    disconnect();

    setStatus('connecting');
    setError(null);

    const cleanup = subscribeToSSE(runId, {
      onStatus: (payload) => {
        setRunStatus(payload.status);
        addEvent(SSE_EVENT_TYPES.STATUS, payload);
        
        // Reset reconnect counter on successful status
        reconnectAttemptRef.current = 0;
        
        // If run completed or failed, disconnect
        if (['succeeded', 'failed', 'canceled', 'rejected'].includes(payload.status)) {
          setStatus('disconnected');
        }
      },

      onProgress: (payload) => {
        setProgress(payload.progress || 0);
        addEvent(SSE_EVENT_TYPES.PROGRESS, payload);
      },

      onLog: (payload) => {
        addEvent(SSE_EVENT_TYPES.LOG, payload, payload.level || 'info');
      },

      onSpecPreview: (payload) => {
        addEvent(SSE_EVENT_TYPES.SPEC_PREVIEW, payload);
      },

      onSpecSaved: (payload) => {
        addEvent(SSE_EVENT_TYPES.SPEC_SAVED, payload);
        onSpecSaved?.(payload);
      },

      onAwaitingApproval: (payload) => {
        setRunStatus('awaiting_approval');
        setPendingDeltas(payload.pending_deltas || []);
        addEvent(SSE_EVENT_TYPES.AWAITING_APPROVAL, payload, 'warning');
      },

      onAwaitingInput: (payload) => {
        setRunStatus('awaiting_input');
        setClarifyingQuestions(payload.clarifying_questions || []);
        addEvent(SSE_EVENT_TYPES.AWAITING_INPUT, payload, 'warning');
      },

      onArtifact: (payload) => {
        setArtifacts(prev => [...prev, payload]);
        addEvent(SSE_EVENT_TYPES.ARTIFACT, payload, 'success');
        onArtifact?.(payload);
      },

      onTextureSelectionRequired: (payload) => {
        setRunStatus('awaiting_texture_selection');
        setPendingTextures(payload.pending_textures || {});
        addEvent(SSE_EVENT_TYPES.TEXTURE_SELECTION_REQUIRED, payload, 'warning');
        onTextureSelectionRequired?.(payload);
      },

      onTextureSelected: (payload) => {
        // Update pending textures by removing the selected one
        setPendingTextures(prev => {
          const updated = { ...prev };
          delete updated[payload.entity_id];
          return updated;
        });
        addEvent(SSE_EVENT_TYPES.TEXTURE_SELECTED, payload, 'success');
      },

      onError: (err) => {
        // Don't show error for normal network close or abort
        const errorMessage = err.message || 'Unknown error';
        const isNormalClose = errorMessage.includes('network') || 
                              errorMessage.includes('aborted') ||
                              errorMessage.includes('abort');
        
        if (!isNormalClose) {
          setError(errorMessage);
          setStatus('error');
          addEvent('error', { message: errorMessage }, 'error');

          // Auto-reconnect logic
          if (autoReconnect && reconnectAttemptRef.current < 3) {
            reconnectAttemptRef.current++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttemptRef.current), 10000);
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, delay);
          }
        } else {
          // Treat as normal close
          setStatus('disconnected');
        }
      },

      onClose: () => {
        setStatus('disconnected');
      },
    });

    cleanupRef.current = cleanup;
    setStatus('connected');
  }, [runId, addEvent, disconnect, autoReconnect, onSpecSaved, onArtifact]);

  // Auto-connect when runId changes
  useEffect(() => {
    if (runId) {
      clearEvents();
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [runId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Manual reconnect function
  const reconnect = useCallback(() => {
    reconnectAttemptRef.current = 0;
    connect();
  }, [connect]);

  return {
    // Connection state
    status,
    isConnected: status === 'connected',
    error,

    // Run state
    runStatus,
    progress,

    // Events
    events,
    clearEvents,

    // Approval state
    pendingDeltas,
    clarifyingQuestions,

    // Texture selection state
    pendingTextures,

    // Artifacts
    artifacts,

    // Controls
    connect,
    disconnect,
    reconnect,
  };
}

export default useSSE;

