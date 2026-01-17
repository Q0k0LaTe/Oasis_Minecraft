/**
 * AuthPage - Login and Registration page
 * Combined login/register with tabs
 */

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

export default function AuthPage() {
  const [activeTab, setActiveTab] = useState('login');
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/workspaces';

  return (
    <div className="auth-page">
      <div className="auth-container">
        <h1 className="auth-title">Oasis Minecraft</h1>
        <p className="auth-subtitle">AI-Powered Mod Generator</p>

        <div className="auth-tabs">
          <button
            className={`auth-tab ${activeTab === 'login' ? 'active' : ''}`}
            onClick={() => setActiveTab('login')}
          >
            Login
          </button>
          <button
            className={`auth-tab ${activeTab === 'register' ? 'active' : ''}`}
            onClick={() => setActiveTab('register')}
          >
            Register
          </button>
        </div>

        <div className="auth-form-container">
          {activeTab === 'login' ? (
            <LoginForm onSuccess={() => navigate(from, { replace: true })} />
          ) : (
            <RegisterForm onSuccess={() => setActiveTab('login')} />
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Login Form Component
 */
function LoginForm({ onSuccess }) {
  const { login, isLoading, error, setError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');
    setError(null);

    if (!email || !password) {
      setLocalError('Please enter both email and password.');
      return;
    }

    const result = await login({ email, password });
    if (result.success) {
      onSuccess?.();
    } else {
      setLocalError(result.error || 'Login failed');
    }
  };

  const displayError = localError || error;

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="login-email">Email</label>
        <input
          id="login-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          autoComplete="email"
          disabled={isLoading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          autoComplete="current-password"
          disabled={isLoading}
        />
      </div>

      {displayError && <div className="form-error">{displayError}</div>}

      <button
        type="submit"
        className="btn btn-primary btn-block"
        disabled={isLoading}
      >
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
}

/**
 * Register Form Component
 */
function RegisterForm({ onSuccess }) {
  const { register, sendVerificationCode, isLoading, error, setError } = useAuth();
  const [step, setStep] = useState(1); // 1: email, 2: code + details
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [localError, setLocalError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [codeSending, setCodeSending] = useState(false);

  // Step 1: Send verification code
  const handleSendCode = async (e) => {
    e.preventDefault();
    setLocalError('');
    setError(null);
    setSuccessMessage('');

    if (!email) {
      setLocalError('Please enter your email.');
      return;
    }

    setCodeSending(true);
    const result = await sendVerificationCode(email);
    setCodeSending(false);

    if (result.success) {
      setSuccessMessage('Verification code sent! Check your email.');
      setStep(2);
    } else {
      setLocalError(result.error || 'Failed to send verification code');
    }
  };

  // Step 2: Complete registration
  const handleRegister = async (e) => {
    e.preventDefault();
    setLocalError('');
    setError(null);

    if (!username || !password || !verificationCode) {
      setLocalError('Please fill in all fields.');
      return;
    }

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      setLocalError('Password must be at least 6 characters.');
      return;
    }

    const result = await register({
      username,
      email,
      password,
      verification_code: verificationCode,
    });

    if (result.success) {
      setSuccessMessage('Registration successful! Please login.');
      setTimeout(() => onSuccess?.(), 1500);
    } else {
      setLocalError(result.error || 'Registration failed');
    }
  };

  const displayError = localError || error;

  return (
    <form className="auth-form" onSubmit={step === 1 ? handleSendCode : handleRegister}>
      {step === 1 ? (
        <>
          <div className="form-group">
            <label htmlFor="register-email">Email</label>
            <input
              id="register-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              disabled={codeSending}
            />
          </div>

          {displayError && <div className="form-error">{displayError}</div>}
          {successMessage && <div className="form-success">{successMessage}</div>}

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={codeSending}
          >
            {codeSending ? 'Sending...' : 'Send Verification Code'}
          </button>
        </>
      ) : (
        <>
          <div className="form-info">
            Verification code sent to <strong>{email}</strong>
            <button
              type="button"
              className="btn-link"
              onClick={() => setStep(1)}
            >
              Change email
            </button>
          </div>

          <div className="form-group">
            <label htmlFor="register-code">Verification Code</label>
            <input
              id="register-code"
              type="text"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value)}
              placeholder="123456"
              autoComplete="one-time-code"
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="register-username">Username</label>
            <input
              id="register-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="cooluser123"
              autoComplete="username"
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="register-password">Password</label>
            <input
              id="register-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="new-password"
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="register-confirm">Confirm Password</label>
            <input
              id="register-confirm"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="new-password"
              disabled={isLoading}
            />
          </div>

          {displayError && <div className="form-error">{displayError}</div>}
          {successMessage && <div className="form-success">{successMessage}</div>}

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={isLoading}
          >
            {isLoading ? 'Creating account...' : 'Create Account'}
          </button>
        </>
      )}
    </form>
  );
}

