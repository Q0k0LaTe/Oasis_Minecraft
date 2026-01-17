/**
 * API module exports
 */

export * from './client.js';
export * as auth from './auth.js';
export * as workspaces from './workspaces.js';
export * as conversations from './conversations.js';
export * as runs from './runs.js';

// Default export with all APIs
import authApi from './auth.js';
import workspacesApi from './workspaces.js';
import conversationsApi from './conversations.js';
import runsApi from './runs.js';

export default {
  auth: authApi,
  workspaces: workspacesApi,
  conversations: conversationsApi,
  runs: runsApi,
};

