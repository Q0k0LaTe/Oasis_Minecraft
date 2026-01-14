import React from 'react';
import '../assets/css/style.css';

//write this first

//lets say senderId is our context Id (aka a specific mod session), and maybe add a developer data so we know who to attribute the mods to, since mods display the creator (unless that is curseforge/modrinth data)
//this should be more like a data chain
const DATA = [{
    senderId: "system",
    text: "randomStuff"
}];

class ChatBox extends React.Component {
  
  constructor() {
    super()
    this.state = {
       messages: DATA,
       sessionContext: "",
       currentSpecs: null
    }
    this.userSendMessage = this.userSendMessage.bind(this);
    this.getAIResponse = this.getAIResponse.bind(this);
    this.initializeSession = this.initializeSession.bind(this);
    this.loadSpecFile = this.loadSpecFile.bind(this);
    this.acceptDelta = this.acceptDelta.bind(this);
    this.rejectDelta = this.rejectDelta.bind(this);
  }

  componentDidMount() {
    // Initialize session when component mounts
    // You can call initializeSession with a session name when needed
  }
  
  render() {
    return (
      <div className="chatbox">
        <Title />
        <MessageList 
          messages={this.state.messages} 
          onAcceptDelta={this.acceptDelta}
          onRejectDelta={this.rejectDelta}
        />
        <SendMessageForm sendMessage = {this.userSendMessage} />
     </div>
    )
  }

  userSendMessage(text) {
    //just add the data chain for now
    DATA.push({
      senderId: "User",
      text: text
    });
    this.setState({
       messages: DATA
    });

    this.getAIResponse(text);
  };

  // Initialize a new session and create/load spec file
  async initializeSession(sessionName) {
    if (!sessionName || sessionName.trim() === "") {
      console.error("Session name cannot be empty");
      return;
    }

    this.setState({ sessionContext: sessionName });

    try {
      // Try to load existing spec file, or create new one if it doesn't exist
      const response = await fetch(`http://localhost:3000/api/specs/${sessionName}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const specs = await response.json();
        this.setState({ currentSpecs: specs });
        DATA.push({
          senderId: "system",
          text: `Loaded existing session: ${sessionName}`
        });
      } else if (response.status === 404) {
        // Create new spec file
        const newSpecs = {};
        const createResponse = await fetch(`http://localhost:3000/api/specs/${sessionName}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(newSpecs)
        });

        if (createResponse.ok) {
          this.setState({ currentSpecs: newSpecs });
          DATA.push({
            senderId: "system",
            text: `Created new session: ${sessionName}`
          });
        } else {
          throw new Error(`Failed to create spec file: ${createResponse.status}`);
        }
      } else {
        throw new Error(`Failed to load spec file: ${response.status}`);
      }

      this.setState({ messages: DATA });
    } catch (error) {
      console.error('Error initializing session:', error);
      DATA.push({
        senderId: "system",
        text: `Error initializing session: ${error.message}`
      });
      this.setState({ messages: DATA });
    }
  }

  // Load current spec file from backend
  async loadSpecFile() {
    if (!this.state.sessionContext) {
      return null;
    }

    try {
      const response = await fetch(`http://localhost:3000/api/specs/${this.state.sessionContext}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const specs = await response.json();
        this.setState({ currentSpecs: specs });
        return specs;
      } else {
        console.warn(`Spec file not found for session: ${this.state.sessionContext}`);
        return null;
      }
    } catch (error) {
      console.error('Error loading spec file:', error);
      return null;
    }
  }
  
  //lock sending messages before response is back
  async getAIResponse(userMessage) {
    //automatically happens after user sends message、スベックを生成してから生成したことの案内メッセージを返す
    try {
      // Load current spec file before sending request
      let currentSpecs = this.state.currentSpecs;
      if (!currentSpecs && this.state.sessionContext) {
        currentSpecs = await this.loadSpecFile();
      }

      const response = await fetch('http://localhost:3000/api/v2/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          sessionContext: this.state.sessionContext,
          currentSpecs: currentSpecs || {}
        })
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data = await response.json();
      
      // The API responds with a spec file, description, and specsDelta
      const { specFile, description, specsDelta } = data;
      
      // Generate unique message ID for tracking
      const messageId = Date.now().toString();
      
      // Add the Agent response to messages with description and pending delta
      DATA.push({
        id: messageId,
        senderId: "Agent",
        text: description || "Spec file generated successfully.",
        specFile: specFile,
        specsDelta: specsDelta,
        pendingDelta: true // Flag to show accept/reject buttons
      });
      
      // Refresh chatbox state to display the new message
      this.setState({
        messages: DATA
      });
    } catch (error) {
      console.error('Error calling AI API:', error);
      
      // Add error message to chat
      DATA.push({
        senderId: "system",
        text: `Error: ${error.message}. Please try again.`
      });
      
      this.setState({
        messages: DATA
      });
    }
    
    //undo if refused
  }

  // Accept the specsDelta and apply it to the current spec file
  async acceptDelta(messageId) {
    const message = DATA.find(msg => msg.id === messageId);
    if (!message || !message.specsDelta) {
      console.error("No delta found for message:", messageId);
      return;
    }

    try {
      // Apply delta to current specs
      const updatedSpecs = this.applyDelta(this.state.currentSpecs || {}, message.specsDelta);
      
      // Save updated specs to backend
      const response = await fetch(`http://localhost:3000/api/specs/${this.state.sessionContext}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedSpecs)
      });

      if (!response.ok) {
        throw new Error(`Failed to save spec file: ${response.status}`);
      }

      // Update state and mark message as accepted
      message.pendingDelta = false;
      message.accepted = true;
      this.setState({
        currentSpecs: updatedSpecs,
        messages: DATA
      });

      DATA.push({
        senderId: "system",
        text: "Changes accepted and applied to spec file."
      });
      this.setState({ messages: DATA });
    } catch (error) {
      console.error('Error accepting delta:', error);
      DATA.push({
        senderId: "system",
        text: `Error applying changes: ${error.message}`
      });
      this.setState({ messages: DATA });
    }
  }

  // Reject the specsDelta
  rejectDelta(messageId) {
    const message = DATA.find(msg => msg.id === messageId);
    if (!message) {
      console.error("Message not found:", messageId);
      return;
    }

    // Mark message as rejected
    message.pendingDelta = false;
    message.rejected = true;
    this.setState({ messages: DATA });

    DATA.push({
      senderId: "system",
      text: "Changes rejected."
    });
    this.setState({ messages: DATA });
  }

  // Helper method to apply delta to specs (deep merge)
  applyDelta(currentSpecs, delta) {
    const result = JSON.parse(JSON.stringify(currentSpecs)); // Deep clone
    
    // Apply delta changes (assuming delta is an object with changes)
    // This is a simple deep merge - adjust based on your delta format
    if (delta && typeof delta === 'object') {
      Object.keys(delta).forEach(key => {
        if (delta[key] === null) {
          // Delete key if delta value is null
          delete result[key];
        } else if (typeof delta[key] === 'object' && !Array.isArray(delta[key])) {
          // Recursively merge nested objects
          result[key] = this.applyDelta(result[key] || {}, delta[key]);
        } else {
          // Set new value
          result[key] = delta[key];
        }
      });
    }
    
    return result;
  }

  undo() {

  }

  redo() {

  }
}

export default ChatBox;

class MessageList extends React.Component {
  render() {
    return (
      <ul className="message-list">                 
        {this.props.messages.map((message, index) => {
          return (
           <li key={message.id || index}>
             <div>
               {message.senderId}
             </div>
             <div>
               {message.text}
             </div>
             {message.pendingDelta && (
               <div className="delta-actions">
                 <button 
                  onClick={() => this.props.onAcceptDelta(message.id)}
                  className="accept-button"
                >
                  Accept Changes
                </button>
                <button 
                  onClick={() => this.props.onRejectDelta(message.id)}
                  className="reject-button"
                >
                  Reject Changes
                </button>
               </div>
             )}
             {message.accepted && (
               <div className="delta-status accepted">✓ Changes accepted</div>
             )}
             {message.rejected && (
               <div className="delta-status rejected">✗ Changes rejected</div>
             )}
           </li>
         )
       })}
     </ul>
    )
  }
}

class SendMessageForm extends React.Component {
  constructor() {
    super()
    this.state = {
      message: ''
    }
    this.handleChange = this.handleChange.bind(this)
    this.handleSubmit = this.handleSubmit.bind(this)
  }
  
  render() {
    return (
      <form
        onSubmit={this.handleSubmit}
        className="send-message-form">
        <input
          onChange={this.handleChange}
          value={this.state.message}
          placeholder="Enter your prompt, press ENTER to send, Ctrl+ENTER for new line:"
          type="text" />
      </form>
    )
  }

  handleChange(e) {
    this.setState({ 
      message: e.target.value
    })
  }

  handleSubmit(e) {
    e.preventDefault();
    this.props.sendMessage(this.state.message);
    this.setState({
      message: ''
    })
  }
}

function Title() {

}