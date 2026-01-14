import React from 'react';
import ChatBox from '../ui_components/ChatBox.jsx';

//specs are individual for each workspace
export default class Workspace extends React.Component {
  constructor(props) {
    super(props);

    // Cache workspace id (renamed from sessionContext)
    this.workspaceId = null;

    this.getSpecInfo = this.getSpecInfo.bind(this);
    this.createWorkspace = this.createWorkspace.bind(this);
    this.createWorkspace();
  }

  /*
  async componentDidMount() {
    // Create workspace in backend when the Workspace mounts
    await this.createWorkspace();
  }
    */

  render() {
    return <ChatBox workspaceId={this.workspaceId} />;
  }

  // Create workspace in the backend and cache the returned id as workspaceId
  // Equivalent to:
  // curl -X POST "http://localhost:3000/api/workspaces" \
  //   -H "Content-Type: application/json" \
  //   -H "Authorization: Bearer $TOKEN" \
  //   -d '{"name": "My Ruby Mod"}'
  async createWorkspace() {
    try {
      const token = this.props.token; // Expect auth token via props (if needed)

      const response = await fetch('http://localhost:3000/api/workspaces', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          name: 'My Ruby Mod',
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create workspace: ${response.status}`);
      }

      const data = await response.json();
      // Save returned workspace id (acts as sessionContext)
      // Adjust property name (`id`, `workspace_id`, etc.) to match backend response
      this.workspaceId = data.id || data.workspace_id;
    } catch (error) {
      console.error('Error creating workspace:', error);
      this.workspaceId = null;
    }
  }

  // Get spec info from the backend for this workspace
  async getSpecInfo() {
    try {
      const workspaceId = this.workspaceId;
      if (!workspaceId) {
        throw new Error('workspaceId is not set');
      }

      const endpoint = `http://localhost:3000/api/workspaces/${workspaceId}/spec`;

      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch spec info: ${response.status}`);
      }

      const specInfo = await response.json();
      return specInfo;
    } catch (error) {
      console.error('Error fetching spec info:', error);
      throw error;
    }
  }

  async displaySpecStructure() {
      
  }
}