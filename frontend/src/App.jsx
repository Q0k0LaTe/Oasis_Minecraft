import Home from "./pages/Home";
import Login from "./pages/Login";
import Workspace from "./pages/Workspace";
import React from 'react';

//add a few states here since typically you wouldn't want the user the relogin each time and go straight into workflow
class App extends React.Component {
  render() {
    return (
      //implement workspace constructor
      <div className="app">
        <Workspace />
     </div>
    )
  }
}

export default App;