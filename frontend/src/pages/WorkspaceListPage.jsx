/**
 * WorkspaceListPage - List and create workspaces
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import * as workspacesApi from '../api/workspaces.js';

export default function WorkspaceListPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [workspaces, setWorkspaces] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Load workspaces
  const loadWorkspaces = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await workspacesApi.listWorkspaces();
      setWorkspaces(data.workspaces || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

  // Handle workspace creation
  const handleCreate = async (workspaceData) => {
    try {
      const newWorkspace = await workspacesApi.createWorkspace(workspaceData);
      setWorkspaces(prev => [newWorkspace, ...prev]);
      setShowCreateModal(false);
      // Navigate to the new workspace
      navigate(`/workspace/${newWorkspace.id}`);
    } catch (err) {
      throw err; // Let the modal handle the error
    }
  };

  // Handle workspace deletion
  const handleDelete = async (workspaceId) => {
    if (!confirm('Are you sure you want to delete this workspace?')) return;
    
    try {
      await workspacesApi.deleteWorkspace(workspaceId);
      setWorkspaces(prev => prev.filter(w => w.id !== workspaceId));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="workspace-list-page">
      <header className="page-header">
        <div className="header-left">
          <h1>My Workspaces</h1>
        </div>
        <div className="header-right">
          {user && <span className="user-info">Hi, {user.username}</span>}
          <button className="btn btn-ghost" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      <main className="page-content">
        <div className="workspace-actions">
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateModal(true)}
          >
            + New Workspace
          </button>
        </div>

        {error && (
          <div className="alert alert-error">
            {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {isLoading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading workspaces...</p>
          </div>
        ) : workspaces.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📦</div>
            <h2>No workspaces yet</h2>
            <p>Create your first workspace to start building Minecraft mods!</p>
            <button
              className="btn btn-primary"
              onClick={() => setShowCreateModal(true)}
            >
              Create Workspace
            </button>
          </div>
        ) : (
          <div className="workspace-grid">
            {workspaces.map(workspace => (
              <WorkspaceCard
                key={workspace.id}
                workspace={workspace}
                onClick={() => navigate(`/workspace/${workspace.id}`)}
                onDelete={() => handleDelete(workspace.id)}
              />
            ))}
          </div>
        )}
      </main>

      {showCreateModal && (
        <CreateWorkspaceModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  );
}

/**
 * Workspace Card Component
 */
function WorkspaceCard({ workspace, onClick, onDelete }) {
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="workspace-card" onClick={onClick}>
      <div className="card-header">
        <h3 className="card-title">{workspace.name}</h3>
        <button
          className="btn btn-icon btn-ghost"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          title="Delete workspace"
        >
          🗑️
        </button>
      </div>
      
      {workspace.description && (
        <p className="card-description">{workspace.description}</p>
      )}
      
      <div className="card-meta">
        <span className="meta-item">
          v{workspace.spec_version || 1}
        </span>
        <span className="meta-item">
          {formatDate(workspace.last_modified_at || workspace.updated_at)}
        </span>
      </div>
      
      {workspace.spec && (
        <div className="card-stats">
          <span>{workspace.spec.items?.length || 0} items</span>
          <span>{workspace.spec.blocks?.length || 0} blocks</span>
          <span>{workspace.spec.tools?.length || 0} tools</span>
        </div>
      )}
    </div>
  );
}

/**
 * Create Workspace Modal
 */
function CreateWorkspaceModal({ onClose, onCreate }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Please enter a workspace name.');
      return;
    }

    setIsLoading(true);
    try {
      await onCreate({
        name: name.trim(),
        description: description.trim() || null,
        spec: {
          mod_name: name.trim(),
          mod_id: name.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, ''),
          version: '1.0.0',
          mc_version: '1.20.1',
          items: [],
          blocks: [],
          tools: [],
        },
      });
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create New Workspace</h2>
          <button className="btn btn-icon btn-ghost" onClick={onClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label htmlFor="workspace-name">Workspace Name</label>
              <input
                id="workspace-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Awesome Mod"
                autoFocus
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="workspace-description">Description (optional)</label>
              <textarea
                id="workspace-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="A mod that adds amazing items and blocks..."
                rows={3}
                disabled={isLoading}
              />
            </div>

            {error && <div className="form-error">{error}</div>}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading}
            >
              {isLoading ? 'Creating...' : 'Create Workspace'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

