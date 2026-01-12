import Home from "./pages/Home";
import Login from "./pages/Login";

//add a few states here since typically you wouldn't want the user the relogin each time and go straight into workflow
class App extends React.Component {
  render() {
    return (
      <div className="app">
        <Title />
        <MessageList />
        <SendMessageForm />
     </div>
    )
  }
}

export default App;