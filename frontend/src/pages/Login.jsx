import React, { useState } from 'react';
import '../assets/css/style.css';
import { API_BASE_URL } from '../config.js';

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!username || !password) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error(`Login failed: ${response.status}`);
      }

      const data = await response.json();
      const token = data.token;

      if (!token) {
        throw new Error('No token returned from backend.');
      }

      // Optionally cache token locally
      try {
        window.localStorage.setItem('authToken', token);
      } catch {
        // ignore storage errors
      }

      if (onLoginSuccess) {
        onLoginSuccess({ token, username });
      }
    } catch (err) {
      console.error('Error during login:', err);
      setError(err.message || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <h1 className="login-headline">Welcome to Mod Generator</h1>

      <form className="login-form" onSubmit={handleSubmit}>
        <label className="login-label">
          <span>Username</span>
          <input
            className="login-input"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </label>

        <label className="login-label">
          <span>Password</span>
          <input
            className="login-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>

        {error && <div className="login-error">{error}</div>}

        <button
          className="login-button login-submit"
          type="submit"
          disabled={loading}
        >
          {loading ? 'Logging in…' : 'Log In'}
        </button>
      </form>
    </div>
  );
}