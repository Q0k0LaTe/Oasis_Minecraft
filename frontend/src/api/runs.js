/**
 * Run, Artifact, and SSE API endpoints
 * Following frontend-api-guide.md strictly
 */

import api, { getToken } from './client.js';
import { API_BASE_URL } from '../config.js';

/**
 * Get a run by ID
 * GET /api/runs/{run_id}
 */
export async function getRun(runId) {
  return api.get(`/runs/${runId}`);
}

/**
 * Cancel a run
 * POST /api/runs/{run_id}/cancel
 */
export async function cancelRun(runId) {
  return api.post(`/runs/${runId}/cancel`, {});
}

/**
 * Approve pending deltas for a run
 * POST /api/runs/{run_id}/approve
 */
export async function approveRun(runId, modifiedDeltas = null) {
  return api.post(`/runs/${runId}/approve`, {
    modified_deltas: modifiedDeltas,
  });
}

/**
 * Reject pending deltas for a run
 * POST /api/runs/{run_id}/reject
 */
export async function rejectRun(runId, reason = null) {
  return api.post(`/runs/${runId}/reject`, { reason });
}

/**
 * Select a texture variant for an entity during build
 * POST /api/runs/{run_id}/select-texture
 */
export async function selectTexture(runId, entityId, selectedVariantIndex) {
  return api.post(`/runs/${runId}/select-texture`, {
    entity_id: entityId,
    selected_variant_index: selectedVariantIndex,
  });
}

/**
 * Get historical events for a run (non-SSE)
 * GET /api/runs/{run_id}/events/history
 */
export async function getRunEventsHistory(runId) {
  return api.get(`/runs/${runId}/events/history`);
}

/**
 * List all runs for a workspace
 * GET /api/runs/workspace/{workspace_id}
 */
export async function listRuns(workspaceId) {
  return api.get(`/runs/workspace/${workspaceId}`);
}

/**
 * Trigger a build for a workspace
 * POST /api/runs/workspace/{workspace_id}/build
 */
export async function triggerBuild(workspaceId) {
  return api.post(`/runs/workspace/${workspaceId}/build`, {});
}

// ========== Artifact Endpoints ==========

/**
 * List all artifacts for a run
 * GET /api/runs/{run_id}/artifacts
 */
export async function listArtifacts(runId) {
  return api.get(`/runs/${runId}/artifacts`);
}

/**
 * Get artifact info
 * GET /api/runs/{run_id}/artifacts/{artifact_id}
 */
export async function getArtifact(runId, artifactId) {
  return api.get(`/runs/${runId}/artifacts/${artifactId}`);
}

/**
 * Get download URL for an artifact
 * Returns the full URL for downloading
 */
export function getDownloadUrl(runId, artifactId) {
  const token = getToken();
  // Include token as query param for download (since it's a direct link)
  return `${API_BASE_URL}/runs/${runId}/artifacts/${artifactId}/download${token ? `?token=${token}` : ''}`;
}

/**
 * Download artifact directly
 * GET /api/runs/{run_id}/artifacts/{artifact_id}/download
 */
export async function downloadArtifact(runId, artifactId) {
  const token = getToken();
  const url = `${API_BASE_URL}/runs/${runId}/artifacts/${artifactId}/download`;
  
  const response = await fetch(url, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    credentials: 'include',
  });
  
  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }
  
  return response.blob();
}

// ========== SSE Subscription ==========

/**
 * Subscribe to SSE events for a run
 * Uses fetch + ReadableStream because EventSource doesn't support Authorization headers
 * 
 * @param {string} runId - Run ID to subscribe to
 * @param {object} handlers - Event handlers
 * @param {function} [handlers.onStatus] - Called on run.status events
 * @param {function} [handlers.onProgress] - Called on run.progress events
 * @param {function} [handlers.onLog] - Called on log.append events
 * @param {function} [handlers.onSpecPreview] - Called on spec.preview events
 * @param {function} [handlers.onSpecSaved] - Called on spec.saved events
 * @param {function} [handlers.onAwaitingApproval] - Called on run.awaiting_approval events
 * @param {function} [handlers.onAwaitingInput] - Called on run.awaiting_input events
 * @param {function} [handlers.onArtifact] - Called on artifact.created events
 * @param {function} [handlers.onError] - Called on errors
 * @param {function} [handlers.onClose] - Called when connection closes
 * @returns {function} - Cleanup function to abort the subscription
 */
export function subscribeToSSE(runId, handlers = {}) {
  const token = getToken();
  const url = `${API_BASE_URL}/runs/${runId}/events`;
  const abortController = new AbortController();
  let isAborted = false;
  
  // Start the subscription
  (async () => {
    try {
      const response = await fetch(url, {
        headers: {
          'Accept': 'text/event-stream',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        credentials: 'include',
        signal: abortController.signal,
      });
      
      if (!response.ok) {
        throw new Error(`SSE connection failed: ${response.status}`);
      }
      
      // Check if we have a readable stream
      if (!response.body) {
        // Fallback: try to read as text (non-streaming response)
        const text = await response.text();
        if (text) {
          processSSEText(text, handlers);
        }
        handlers.onClose?.();
        return;
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            // Process any remaining buffer content
            if (buffer.trim()) {
              processSSEText(buffer, handlers);
            }
            handlers.onClose?.();
            break;
          }
          
          buffer += decoder.decode(value, { stream: true });
          
          // Process complete events (separated by double newline)
          const events = buffer.split('\n\n');
          buffer = events.pop() || ''; // Keep incomplete event in buffer
          
          for (const eventStr of events) {
            if (!eventStr.trim()) continue;
            
            const parsed = parseSSEEvent(eventStr);
            if (parsed) {
              dispatchSSEEvent(parsed, handlers);
            }
          }
        }
      } catch (readError) {
        // Reader error - might be normal close or actual error
        if (!isAborted && readError.name !== 'AbortError') {
          // Process any remaining buffer
          if (buffer.trim()) {
            processSSEText(buffer, handlers);
          }
          // Only report as error if it's not a normal stream end
          if (readError.message && !readError.message.includes('network')) {
            console.warn('SSE read error:', readError);
          }
        }
        handlers.onClose?.();
      }
    } catch (error) {
      if (error.name !== 'AbortError' && !isAborted) {
        handlers.onError?.(error);
      }
    }
  })();
  
  // Return cleanup function
  return () => {
    isAborted = true;
    abortController.abort();
  };
}

/**
 * Process SSE text that may contain multiple events
 */
function processSSEText(text, handlers) {
  const events = text.split('\n\n');
  for (const eventStr of events) {
    if (!eventStr.trim()) continue;
    const parsed = parseSSEEvent(eventStr);
    if (parsed) {
      dispatchSSEEvent(parsed, handlers);
    }
  }
}

/**
 * Parse a single SSE event string
 */
function parseSSEEvent(eventStr) {
  const lines = eventStr.split('\n');
  let eventType = null;
  let data = null;
  
  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      const dataStr = line.slice(5).trim();
      try {
        data = JSON.parse(dataStr);
      } catch {
        data = dataStr;
      }
    }
  }
  
  if (eventType && data) {
    return { eventType, data };
  }
  return null;
}

/**
 * Dispatch parsed SSE event to appropriate handler
 */
function dispatchSSEEvent({ eventType, data }, handlers) {
  const payload = data.payload || data;
  
  switch (eventType) {
    case 'run.status':
      handlers.onStatus?.(payload);
      break;
    case 'run.progress':
      handlers.onProgress?.(payload);
      break;
    case 'log.append':
      handlers.onLog?.(payload);
      break;
    case 'spec.preview':
      handlers.onSpecPreview?.(payload);
      break;
    case 'spec.saved':
      handlers.onSpecSaved?.(payload);
      break;
    case 'run.awaiting_approval':
      handlers.onAwaitingApproval?.(payload);
      break;
    case 'run.awaiting_input':
      handlers.onAwaitingInput?.(payload);
      break;
    case 'artifact.created':
      handlers.onArtifact?.(normalizeArtifactPayload(payload));
      break;
    case 'texture.selection_required':
      handlers.onTextureSelectionRequired?.(payload);
      break;
    case 'texture.selected':
      handlers.onTextureSelected?.(payload);
      break;
    default:
      // Unknown event type - could log for debugging
      console.log('Unknown SSE event:', eventType, payload);
  }
}

function normalizeArtifactPayload(payload) {
  if (!payload || typeof payload !== 'object') return payload;
  if (payload.id) return payload;
  if (payload.artifact_id) {
    return { ...payload, id: payload.artifact_id };
  }
  return payload;
}

export default {
  getRun,
  cancelRun,
  approveRun,
  rejectRun,
  selectTexture,
  getRunEventsHistory,
  listRuns,
  triggerBuild,
  listArtifacts,
  getArtifact,
  getDownloadUrl,
  downloadArtifact,
  subscribeToSSE,
};

