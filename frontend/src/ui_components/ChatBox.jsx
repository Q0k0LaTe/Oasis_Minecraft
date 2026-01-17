import React from 'react';
import '../assets/css/style.css';
import { API_BASE_URL } from '../config.js';

const DATA = [{
    senderId: "system",
    text: "randomStuff"
}];

class ChatBox extends React.Component {
  
  constructor() {
    super()
    this.state = {
       messages: DATA,
       isLoading: false, // Track if a request is in progress
       conversationId: null // Store the conversation ID
    }
    this.userSendMessage = this.userSendMessage.bind(this);
    this.getConversation = this.getConversation.bind(this);
    this.createConversation = this.createConversation.bind(this);
    //this.getAIResponse = this.getAIResponse.bind(this);
  }

  async componentDidMount() {
    // Create conversation when ChatBox mounts
    await this.createConversation();
  }
  
  render() {
    return (
      <div className="chatbox">
        <Title />
        <MessageList messages={this.state.messages} />
        <SendMessageForm 
          sendMessage={this.userSendMessage} 
          disabled={this.state.isLoading}
        />
     </div>
    )
  }

  userSendMessage(text) {
    // Prevent sending if already loading
    if (this.state.isLoading) {
      return;
    }

    //just add the data chain for now
    DATA.push({
      senderId: "User",
      text: text
    });
    this.setState({
       messages: DATA
    });

    // Use the stored conversationId instead of workspaceId
    if (this.state.conversationId) {
      this.getConversation(this.state.conversationId);
    } else {
      console.error('Conversation ID not available');
    }
  };

  // Create a conversation for this workspace
  async createConversation() {
    try {
      const workspaceId = this.props.workspaceId;
      if (!workspaceId) {
        throw new Error('workspaceId is required to create conversation');
      }

      const endpoint = `${API_BASE_URL}/workspaces/${workspaceId}/conversations`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to create conversation: ${response.status}`);
      }

      const data = await response.json();
      // Save returned conversation id
      const conversationId = data.id || data.conversation_id;
      this.setState({ conversationId });
      
      return conversationId;
    } catch (error) {
      console.error('Error creating conversation:', error);
      this.setState({ conversationId: null });
      throw error;
    }
  }

  //add accept or refuse changes later
  //ai automatically generates/updates spec, idk if it returns anything actually, but it does what it does
  // post message to call backend to get conversation: returns array of messages and its size
  async getConversation(conversationId) {
    // Set loading state to prevent sending another message
    this.setState({ isLoading: true });

    try {
      if (!conversationId) {
        throw new Error('conversationId is required to fetch conversation');
      }

      const endpoint = `${API_BASE_URL}/conversations/${conversationId}`;

      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch conversation: ${response.status}`);
      }

      // Expect backend to return an array of messages
      const messages = await response.json();
      const size = Array.isArray(messages) ? messages.length : 0;

      // Request completed successfully - re-enable sending
      this.setState({ isLoading: false });
      return { messages, size };
    } catch (error) {
      console.error('Error fetching AI conversation:', error);
      // Request failed - re-enable sending
      this.setState({ isLoading: false });
      throw error;
    }
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
        {this.props.messages.map(message => {
          return (
           <li key={message.id}>
             <div className="message-sender">
               {message.senderId}
             </div>
             <div
               className={
                 "message-bubble" +
                 (message.senderId === "User" ? " user" : "") +
                 (message.senderId === "system" ? " system" : "")
               }
             >
               {message.text}
             </div>
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
          type="text"
          disabled={this.props.disabled}
        />
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
    // Prevent submission if disabled
    if (this.props.disabled) {
      return;
    }
    this.props.sendMessage(this.state.message);
    this.setState({
      message: ''
    })
  }
}

function Title() {

}