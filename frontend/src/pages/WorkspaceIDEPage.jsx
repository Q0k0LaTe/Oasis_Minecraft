/**
 * WorkspaceIDEPage - Main workspace editor with three-column layout
 * Left: Object List | Center: Properties Panel | Right: Conversation + SSE Log
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useWorkspace } from '../hooks/useWorkspace.js';
import { useSSE } from '../hooks/useSSE.js';
import * as conversationsApi from '../api/conversations.js';
import * as runsApi from '../api/runs.js';

import ObjectList from '../components/ObjectList.jsx';
import PropertiesPanel from '../components/PropertiesPanel.jsx';
import ConversationPanel from '../components/ConversationPanel.jsx';
import SpecEditor from '../components/SpecEditor.jsx';
import ApprovalDialog from '../components/ApprovalDialog.jsx';
import TextureSelectionDialog from '../components/TextureSelectionDialog.jsx';

export default function WorkspaceIDEPage() {
  const { workspaceId } = useParams();
  const navigate = useNavigate();
  const { logout } = useAuth();

  // Workspace state
  const {
    workspace,
    spec,
    specVersion,
    conversations,
    isLoading: workspaceLoading,
    error: workspaceError,
    loadWorkspace,
    loadSpec,
    loadConversations,
    createConversation,
    updateSpec,
    refresh,
  } = useWorkspace(workspaceId);

  // Local state
  const [selectedObject, setSelectedObject] = useState(null);
  const [selectedObjectType, setSelectedObjectType] = useState(null);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentRunId, setCurrentRunId] = useState(null);
  const [showSpecEditor, setShowSpecEditor] = useState(false);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [showTextureSelectionDialog, setShowTextureSelectionDialog] = useState(false);
  const [buildArtifacts, setBuildArtifacts] = useState([]);
  const [isSending, setIsSending] = useState(false);

  // SSE subscription
  const {
    status: sseStatus,
    runStatus,
    progress,
    events,
    pendingDeltas,
    pendingTextures,
    artifacts,
    clearEvents,
    reconnect,
  } = useSSE(currentRunId, {
    onSpecSaved: () => {
      // Refresh spec when saved
      loadSpec();
    },
    onArtifact: (artifact) => {
      setBuildArtifacts(prev => [...prev, artifact]);
    },
    onTextureSelectionRequired: () => {
      // Show texture selection dialog
      setShowTextureSelectionDialog(true);
    },
  });

  // Show approval dialog when awaiting approval (even with 0 deltas)
  useEffect(() => {
    if (runStatus === 'awaiting_approval') {
      setShowApprovalDialog(true);
    }
  }, [runStatus]);

  // Show texture selection dialog when awaiting texture selection
  useEffect(() => {
    if (runStatus === 'awaiting_texture_selection') {
      setShowTextureSelectionDialog(true);
    }
    // Hide texture selection dialog when status changes away from awaiting_texture_selection
    if (runStatus !== 'awaiting_texture_selection' && showTextureSelectionDialog) {
      // Check if there are still pending textures
      if (Object.keys(pendingTextures).length === 0) {
        setShowTextureSelectionDialog(false);
      }
    }
  }, [runStatus, pendingTextures, showTextureSelectionDialog]);

  // Initial data load
  useEffect(() => {
    const initializeWorkspace = async () => {
      await loadWorkspace();
      await loadSpec();
      const convs = await loadConversations();
      
      // If no conversations exist, create the main one
      if (convs && convs.length === 0) {
        const newConv = await createConversation('Main Conversation');
        if (newConv) {
          setActiveConversationId(newConv.id);
        }
      } else if (convs && convs.length > 0) {
        setActiveConversationId(convs[0].id);
      }
    };

    if (workspaceId) {
      initializeWorkspace();
    }
  }, [workspaceId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load messages when conversation changes
  useEffect(() => {
    const loadMessages = async () => {
      if (!activeConversationId) return;
      try {
        const data = await conversationsApi.getMessages(activeConversationId);
        setMessages(data.messages || []);
      } catch (err) {
        console.error('Error loading messages:', err);
      }
    };
    loadMessages();
  }, [activeConversationId]);

  // Handle sending a message
  const handleSendMessage = useCallback(async (content, triggerRun = true) => {
    if (!activeConversationId || !content.trim()) return;

    setIsSending(true);
    try {
      const result = await conversationsApi.sendMessage(activeConversationId, {
        content: content.trim(),
        trigger_run: triggerRun,
        run_type: 'generate',
      });

      // Add user message to list
      if (result.message) {
        setMessages(prev => [...prev, result.message]);
      }

      // Start SSE subscription for the new run
      if (result.run_id) {
        setCurrentRunId(result.run_id);
        clearEvents();
      }
    } catch (err) {
      console.error('Error sending message:', err);
    } finally {
      setIsSending(false);
    }
  }, [activeConversationId, clearEvents]);

  // Handle object selection
  const handleSelectObject = useCallback((object, type) => {
    setSelectedObject(object);
    setSelectedObjectType(type);
  }, []);

  // Handle build trigger
  const handleBuild = useCallback(async () => {
    if (!workspaceId) return;

    try {
      setBuildArtifacts([]);
      const result = await runsApi.triggerBuild(workspaceId);
      if (result.id) {
        setCurrentRunId(result.id);
        clearEvents();
      }
    } catch (err) {
      console.error('Error triggering build:', err);
    }
  }, [workspaceId, clearEvents]);

  // Handle export (download spec as JSON)
  const handleExport = useCallback(() => {
    if (!spec) return;

    const dataStr = JSON.stringify(spec, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${spec.mod_id || 'mod'}_spec.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [spec]);

  // Handle spec save from editor
  const handleSpecSave = useCallback(async (newSpec) => {
    const result = await updateSpec(newSpec, 'Manual edit from spec editor');
    if (result.success) {
      setShowSpecEditor(false);
    }
    return result;
  }, [updateSpec]);

  // Handle object deletion from ObjectList
  const handleDeleteObject = useCallback(async (obj, type, index) => {
    const name = obj.item_name || obj.block_name || obj.tool_name || 'this object';
    if (!window.confirm(`Delete "${name}"?`)) return;

    // Map type to spec array name
    const pathMap = { block: 'blocks', item: 'items', structure: 'tools' };
    const arrayName = pathMap[type];

    if (!spec || !arrayName) return;

    // Create a copy of the spec with the item removed
    const newSpec = { ...spec };
    const currentArray = newSpec[arrayName] || [];
    newSpec[arrayName] = currentArray.filter((_, i) => i !== index);

    // Use updateSpec to save the modified spec
    const result = await updateSpec(newSpec, `Deleted ${name}`);

    // Clear selection if deleted item was selected
    if (result.success && selectedObject) {
      const selectedId = selectedObject.item_id || selectedObject.block_id || selectedObject.tool_id;
      const deletedId = obj.item_id || obj.block_id || obj.tool_id;
      if (selectedId === deletedId) {
        setSelectedObject(null);
        setSelectedObjectType(null);
      }
    }
  }, [spec, updateSpec, selectedObject]);

  // Handle approval
  const handleApprove = useCallback(async (modifiedDeltas = null) => {
    if (!currentRunId) return;

    try {
      await runsApi.approveRun(currentRunId, modifiedDeltas);
      setShowApprovalDialog(false);
      // Spec will be refreshed via SSE onSpecSaved callback
    } catch (err) {
      console.error('Error approving:', err);
    }
  }, [currentRunId]);

  // Handle rejection
  const handleReject = useCallback(async (reason = null) => {
    if (!currentRunId) return;

    try {
      await runsApi.rejectRun(currentRunId, reason);
      setShowApprovalDialog(false);
    } catch (err) {
      console.error('Error rejecting:', err);
    }
  }, [currentRunId]);

  // Handle texture selection
  const handleTextureSelect = useCallback(async (entityId, variantIndex) => {
    if (!currentRunId) return;

    try {
      const result = await runsApi.selectTexture(currentRunId, entityId, variantIndex);
      // If all textures selected, the dialog will be hidden via the useEffect
      return result;
    } catch (err) {
      console.error('Error selecting texture:', err);
      throw err;
    }
  }, [currentRunId]);

  // Handle artifact download
  const handleDownload = useCallback(async (artifact) => {
    if (!currentRunId) return;

    try {
      const blob = await runsApi.downloadArtifact(currentRunId, artifact.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = artifact.file_name || 'download.jar';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading artifact:', err);
    }
  }, [currentRunId]);

  if (workspaceLoading && !workspace) {
    return (
      <div className="workspace-ide loading">
        <div className="spinner"></div>
        <p>Loading workspace...</p>
      </div>
    );
  }

  if (workspaceError) {
    return (
      <div className="workspace-ide error">
        <p>Error loading workspace: {workspaceError}</p>
        <button className="btn btn-primary" onClick={() => navigate('/workspaces')}>
          Back to Workspaces
        </button>
      </div>
    );
  }

  return (
    <div className="workspace-ide">
      {/* Header */}
      <header className="ide-header">
        <div className="header-left">
          <button className="btn btn-ghost" onClick={() => navigate('/workspaces')}>
            ← Back
          </button>
          <h1 className="workspace-name">{workspace?.name || 'Workspace'}</h1>
          <span className="spec-version">v{specVersion}</span>
        </div>
        <div className="header-right">
          <button className="btn btn-ghost" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      {/* Main Content - Three Column Layout */}
      <main className="ide-main">
        {/* Left Column - Object List */}
        <aside className="ide-column ide-left">
          <ObjectList
            spec={spec}
            selectedObject={selectedObject}
            onSelectObject={handleSelectObject}
            onDeleteObject={handleDeleteObject}
            onExport={handleExport}
            onBuild={handleBuild}
            isBuildRunning={runStatus === 'running' && currentRunId}
          />
        </aside>

        {/* Center Column - Properties Panel */}
        <section className="ide-column ide-center">
          <PropertiesPanel
            object={selectedObject}
            objectType={selectedObjectType}
            onAdjust={() => setShowSpecEditor(true)}
          />
        </section>

        {/* Right Column - Conversation + Events */}
        <aside className="ide-column ide-right">
          <ConversationPanel
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelectConversation={setActiveConversationId}
            messages={messages}
            events={events}
            sseStatus={sseStatus}
            runStatus={runStatus}
            progress={progress}
            artifacts={[...artifacts, ...buildArtifacts]}
            onSendMessage={handleSendMessage}
            onReconnect={reconnect}
            onDownload={handleDownload}
            onApprove={handleApprove}
            onReject={handleReject}
            isSending={isSending}
          />
        </aside>
      </main>

      {/* Modals */}
      {showSpecEditor && (
        <SpecEditor
          spec={spec}
          onSave={handleSpecSave}
          onClose={() => setShowSpecEditor(false)}
        />
      )}

      {showApprovalDialog && (
        <ApprovalDialog
          deltas={pendingDeltas}
          onApprove={handleApprove}
          onReject={handleReject}
          onClose={() => setShowApprovalDialog(false)}
        />
      )}

      {showTextureSelectionDialog && Object.keys(pendingTextures).length > 0 && (
        <TextureSelectionDialog
          pendingTextures={pendingTextures}
          onSelectTexture={handleTextureSelect}
          onClose={() => setShowTextureSelectionDialog(false)}
        />
      )}
    </div>
  );
}

