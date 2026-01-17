/**
 * Conversation and Message API endpoints
 * Following frontend-api-guide.md strictly
 */

import api from './client.js';

/**
 * Create a new conversation in a workspace
 * POST /api/workspaces/{workspace_id}/conversations
 */
export async function createConversation(workspaceId, title = 'Main Conversation') {
  return api.post(`/workspaces/${workspaceId}/conversations`, { title });
}

/**
 * List all conversations in a workspace
 * GET /api/workspaces/{workspace_id}/conversations
 */
export async function listConversations(workspaceId) {
  return api.get(`/workspaces/${workspaceId}/conversations`);
}

/**
 * Get a single conversation by ID
 * GET /api/conversations/{conversation_id}
 */
export async function getConversation(conversationId) {
  return api.get(`/conversations/${conversationId}`);
}

/**
 * Update conversation (title, etc.)
 * PATCH /api/conversations/{conversation_id}
 */
export async function updateConversation(conversationId, updates) {
  return api.patch(`/conversations/${conversationId}`, updates);
}

/**
 * Delete a conversation
 * DELETE /api/conversations/{conversation_id}
 */
export async function deleteConversation(conversationId) {
  return api.delete(`/conversations/${conversationId}`);
}

// ========== Message Endpoints ==========

/**
 * Get all messages in a conversation
 * GET /api/conversations/{conversation_id}/messages
 */
export async function getMessages(conversationId) {
  return api.get(`/conversations/${conversationId}/messages`);
}

/**
 * Send a message to a conversation
 * POST /api/conversations/{conversation_id}/messages
 * 
 * @param {string} conversationId 
 * @param {object} params
 * @param {string} params.content - Message content
 * @param {boolean} [params.trigger_run=false] - Whether to trigger an AI run
 * @param {string} [params.run_type='generate'] - Type of run: 'generate' or 'build'
 */
export async function sendMessage(conversationId, { content, trigger_run = false, run_type = 'generate' }) {
  return api.post(`/conversations/${conversationId}/messages`, {
    content,
    trigger_run,
    run_type,
  });
}

/**
 * Get a single message by ID
 * GET /api/messages/{message_id}
 */
export async function getMessage(messageId) {
  return api.get(`/messages/${messageId}`);
}

export default {
  createConversation,
  listConversations,
  getConversation,
  updateConversation,
  deleteConversation,
  getMessages,
  sendMessage,
  getMessage,
};

