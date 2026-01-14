import '../assets/css/style.css';

export default function Login() {
  return (
    <div className="login-container">
      <h1 className="login-headline">Welcome to Mod Generator</h1>
      <div className="login-buttons">
        <button className="login-button">Log in By Google</button>
        <button className="login-button">Log in By Email</button>
      </div>
    </div>
  );
}