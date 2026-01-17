/**
 * Authentication API endpoints
 * Following frontend-api-guide.md strictly
 */

import api, { setToken, clearToken } from './client.js';

/**
 * Send verification code to email
 * POST /api/auth/send-verification-code
 */
export async function sendVerificationCode(email) {
  return api.post('/auth/send-verification-code', { email });
}

/**
 * Register a new user
 * POST /api/auth/register
 */
export async function register({ username, email, password, verification_code }) {
  return api.post('/auth/register', {
    username,
    email,
    password,
    verification_code,
  });
}

/**
 * Login with email and password
 * POST /api/auth/login
 */
export async function login({ email, password }) {
  const data = await api.post('/auth/login', { email, password });
  
  // Store the session token
  if (data?.session?.token) {
    setToken(data.session.token);
  }
  
  return data;
}

/**
 * Google OAuth login
 * POST /api/auth/google-login
 */
export async function googleLogin(idToken) {
  const data = await api.post('/auth/google-login', { id_token: idToken });
  
  // Store the session token if login is complete
  if (data?.session?.token) {
    setToken(data.session.token);
  }
  
  return data;
}

/**
 * Set username for Google OAuth users
 * POST /api/auth/set-username
 */
export async function setUsername({ id_token, username }) {
  const data = await api.post('/auth/set-username', { id_token, username });
  
  // Store the session token
  if (data?.session?.token) {
    setToken(data.session.token);
  }
  
  return data;
}

/**
 * Logout current session
 * POST /api/auth/logout
 */
export async function logout() {
  try {
    await api.post('/auth/logout', {});
  } finally {
    clearToken();
  }
}

/**
 * Get Google client ID for OAuth
 * GET /api/auth/google-client-id
 */
export async function getGoogleClientId() {
  return api.get('/auth/google-client-id');
}

export default {
  sendVerificationCode,
  register,
  login,
  googleLogin,
  setUsername,
  logout,
  getGoogleClientId,
};

