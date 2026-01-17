/**
 * Workspace and Spec API endpoints
 * Following frontend-api-guide.md strictly
 */

import api from './client.js';

/**
 * Create a new workspace
 * POST /api/workspaces
 */
export async function createWorkspace({ name, description, spec }) {
  return api.post('/workspaces', { name, description, spec });
}

/**
 * List all workspaces for current user
 * GET /api/workspaces
 */
export async function listWorkspaces() {
  return api.get('/workspaces');
}

/**
 * Get a single workspace by ID
 * GET /api/workspaces/{workspace_id}
 */
export async function getWorkspace(workspaceId) {
  return api.get(`/workspaces/${workspaceId}`);
}

/**
 * Update workspace (name, description, etc.)
 * PATCH /api/workspaces/{workspace_id}
 */
export async function updateWorkspace(workspaceId, updates) {
  return api.patch(`/workspaces/${workspaceId}`, updates);
}

/**
 * Delete a workspace
 * DELETE /api/workspaces/{workspace_id}
 */
export async function deleteWorkspace(workspaceId) {
  return api.delete(`/workspaces/${workspaceId}`);
}

// ========== Spec Endpoints ==========

/**
 * Get current spec for a workspace
 * GET /api/workspaces/{workspace_id}/spec
 */
export async function getSpec(workspaceId) {
  return api.get(`/workspaces/${workspaceId}/spec`);
}

/**
 * Replace entire spec (full update)
 * PUT /api/workspaces/{workspace_id}/spec
 */
export async function updateSpec(workspaceId, spec, changeNotes = null) {
  return api.put(`/workspaces/${workspaceId}/spec`, {
    spec,
    change_notes: changeNotes,
  });
}

/**
 * Partial update spec with operations
 * PATCH /api/workspaces/{workspace_id}/spec
 */
export async function patchSpec(workspaceId, operations, changeNotes = null) {
  return api.patch(`/workspaces/${workspaceId}/spec`, {
    operations,
    change_notes: changeNotes,
  });
}

/**
 * Get spec version history
 * GET /api/workspaces/{workspace_id}/spec/history
 */
export async function getSpecHistory(workspaceId) {
  return api.get(`/workspaces/${workspaceId}/spec/history`);
}

/**
 * Rollback spec to a previous version
 * POST /api/workspaces/{workspace_id}/spec/rollback/{version}
 */
export async function rollbackSpec(workspaceId, version) {
  return api.post(`/workspaces/${workspaceId}/spec/rollback/${version}`, {});
}

export default {
  createWorkspace,
  listWorkspaces,
  getWorkspace,
  updateWorkspace,
  deleteWorkspace,
  getSpec,
  updateSpec,
  patchSpec,
  getSpecHistory,
  rollbackSpec,
};

