import Home from "./pages/Home";
import Login from "./pages/Login";
import Workspace from "./pages/Workspace";
import React from 'react';

// Manage auth state so user logs in once, then goes to workspace
class App extends React.Component {
  constructor(props) {
    super(props);

    let savedToken = null;
    try {
      savedToken = window.localStorage.getItem('authToken');
    } catch {
      savedToken = null;
    }

    this.state = {
      authToken: savedToken,
      username: null,
    };

    this.handleLoginSuccess = this.handleLoginSuccess.bind(this);
  }

  handleLoginSuccess({ token, username }) {
    this.setState({
      authToken: token,
      username,
    });
  }

  render() {
    const { authToken } = this.state;

    return (
      <div className="app">
        {authToken ? (
          // Pass auth token down so Workspace can create workspace and call APIs
          <Workspace token={authToken} />
        ) : (
          <Login onLoginSuccess={this.handleLoginSuccess} />
        )}
      </div>
    );
  }
}

export default App;