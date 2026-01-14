import React from 'react';
import '../assets/css/style.css';

const DATA = [{
    senderId: "system",
    text: "randomStuff"
}];

class ChatBox extends React.Component {
  
  constructor() {
    super()
    this.state = {
       messages: DATA
    }
    this.userSendMessage = this.userSendMessage.bind(this);
    this.postConversation = this.postConversation.bind(this);
    //this.getAIResponse = this.getAIResponse.bind(this);
    this.workspaceId = this.props.workspaceId;
  }
  
  render() {
    return (
      <div className="chatbox">
        <Title />
        <MessageList messages={this.state.messages} />
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

    this.postConversation(this.workspaceId);
  };

  //add accept or refuse changes later
  //ai automatically generates/updates spec, idk if it returns anything actually, but it does what it does
  // post message to call backend to get conversation: returns array of messages and its size
  async postConversation(conversationId) {
    try {
      if (!conversationId) {
        throw new Error('conversationId is required to fetch conversation');
      }

      const endpoint = `http://localhost:3000/api/conversations/${conversationId}/messages`;

      const response = await fetch(endpoint, {
        method: 'POST',
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

      return { messages, size };
    } catch (error) {
      console.error('Error fetching AI conversation:', error);
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