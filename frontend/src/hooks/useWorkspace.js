/**
 * useWorkspace - Custom hook for workspace and spec state management
 */

import { useState, useCallback } from 'react';
import * as workspacesApi from '../api/workspaces.js';
import * as conversationsApi from '../api/conversations.js';

/**
 * useWorkspace hook
 * 
 * @param {string|null} workspaceId - Workspace ID to load
 * @returns {object} - Workspace state and actions
 */
export function useWorkspace(workspaceId) {
  const [workspace, setWorkspace] = useState(null);
  const [spec, setSpec] = useState(null);
  const [specVersion, setSpecVersion] = useState(0);
  const [conversations, setConversations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load workspace data
  const loadWorkspace = useCallback(async () => {
    if (!workspaceId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await workspacesApi.getWorkspace(workspaceId);
      setWorkspace(data);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  // Load spec data
  const loadSpec = useCallback(async () => {
    if (!workspaceId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await workspacesApi.getSpec(workspaceId);
      setSpec(data.spec);
      setSpecVersion(data.version || 0);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  // Update spec (full replacement)
  const updateSpec = useCallback(async (newSpec, changeNotes = null) => {
    if (!workspaceId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await workspacesApi.updateSpec(workspaceId, newSpec, changeNotes);
      setSpec(data.spec);
      setSpecVersion(data.version || 0);
      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  // Patch spec (partial update)
  const patchSpec = useCallback(async (operations, changeNotes = null) => {
    if (!workspaceId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await workspacesApi.patchSpec(workspaceId, operations, changeNotes);
      setSpec(data.spec);
      setSpecVersion(data.version || 0);
      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  // Load conversations
  const loadConversations = useCallback(async () => {
    if (!workspaceId) return;
    
    try {
      const data = await conversationsApi.listConversations(workspaceId);
      setConversations(data.conversations || []);
      return data.conversations || [];
    } catch (err) {
      console.error('Error loading conversations:', err);
      return [];
    }
  }, [workspaceId]);

  // Create conversation
  const createConversation = useCallback(async (title = 'Main Conversation') => {
    if (!workspaceId) return;
    
    try {
      const data = await conversationsApi.createConversation(workspaceId, title);
      setConversations(prev => [...prev, data]);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }, [workspaceId]);

  // Refresh all data
  const refresh = useCallback(async () => {
    await Promise.all([
      loadWorkspace(),
      loadSpec(),
      loadConversations(),
    ]);
  }, [loadWorkspace, loadSpec, loadConversations]);

  // Get objects from spec grouped by type
  const getObjects = useCallback(() => {
    if (!spec) return { blocks: [], items: [], structures: [] };
    
    return {
      blocks: spec.blocks || [],
      items: spec.items || [],
      structures: spec.tools || spec.structures || [],
    };
  }, [spec]);

  return {
    // State
    workspace,
    spec,
    specVersion,
    conversations,
    isLoading,
    error,

    // Actions
    loadWorkspace,
    loadSpec,
    updateSpec,
    patchSpec,
    loadConversations,
    createConversation,
    refresh,

    // Helpers
    getObjects,
    setError,
  };
}

export default useWorkspace;

