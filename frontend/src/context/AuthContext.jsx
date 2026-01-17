/**
 * AuthContext - Global authentication state management
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getToken, setToken, clearToken } from '../api/client.js';
import * as authApi from '../api/auth.js';

// Create the context
const AuthContext = createContext(null);

/**
 * AuthProvider component - wraps the app to provide auth state
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [sessionToken, setSessionToken] = useState(() => getToken());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check if user is authenticated
  const isAuthenticated = !!sessionToken;

  // Initialize auth state from localStorage
  useEffect(() => {
    const token = getToken();
    if (token) {
      setSessionToken(token);
      // We could verify the token here, but for now just trust it
      // The API will return 401 if it's invalid
    }
    setIsLoading(false);
  }, []);

  // Listen for unauthorized events (401 responses)
  useEffect(() => {
    const handleUnauthorized = () => {
      setSessionToken(null);
      setUser(null);
      clearToken();
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  // Login function
  const login = useCallback(async ({ email, password }) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await authApi.login({ email, password });
      
      if (data.success && data.session?.token) {
        setSessionToken(data.session.token);
        setToken(data.session.token);
        setUser(data.user);
        return { success: true, user: data.user };
      } else {
        throw new Error(data.message || 'Login failed');
      }
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Register function
  const register = useCallback(async ({ username, email, password, verification_code }) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await authApi.register({ username, email, password, verification_code });
      
      if (data.success) {
        // Registration successful - user needs to login
        return { success: true, user: data.user };
      } else {
        throw new Error(data.message || 'Registration failed');
      }
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Send verification code
  const sendVerificationCode = useCallback(async (email) => {
    setError(null);
    try {
      const data = await authApi.sendVerificationCode(email);
      return { success: true, message: data.message };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  }, []);

  // Logout function
  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } catch (err) {
      // Ignore logout errors - clear local state anyway
      console.error('Logout error:', err);
    } finally {
      setSessionToken(null);
      setUser(null);
      clearToken();
      setIsLoading(false);
    }
  }, []);

  // Context value
  const value = {
    user,
    sessionToken,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    sendVerificationCode,
    logout,
    setError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * useAuth hook - access auth context
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;

