/**
 * Centralized API client with authentication and error handling
 */

import { API_BASE_URL } from '../config.js';

// Get token from localStorage
export function getToken() {
  try {
    return localStorage.getItem('sessionToken');
  } catch {
    return null;
  }
}

// Set token in localStorage
export function setToken(token) {
  try {
    if (token) {
      localStorage.setItem('sessionToken', token);
    } else {
      localStorage.removeItem('sessionToken');
    }
  } catch {
    // Ignore storage errors
  }
}

// Clear token from localStorage
export function clearToken() {
  try {
    localStorage.removeItem('sessionToken');
  } catch {
    // Ignore storage errors
  }
}

/**
 * Base fetch wrapper with authentication and error handling
 * @param {string} endpoint - API endpoint (without base URL)
 * @param {object} options - Fetch options
 * @returns {Promise<any>} - Response data
 */
export async function apiClient(endpoint, options = {}) {
  const token = getToken();
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  // Add auth header if token exists
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const config = {
    ...options,
    headers,
    credentials: 'include', // Also support cookie-based auth
  };
  
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, config);
    
    // Handle 401 - redirect to login
    if (response.status === 401) {
      clearToken();
      // Dispatch custom event for auth failure
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      throw new ApiError('Unauthorized - please login again', 401);
    }
    
    // Handle 204 No Content
    if (response.status === 204) {
      return null;
    }
    
    // Parse response
    const data = await response.json().catch(() => null);
    
    // Handle error responses
    if (!response.ok) {
      const message = data?.detail || data?.message || `Request failed with status ${response.status}`;
      throw new ApiError(message, response.status, data);
    }
    
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network or other errors
    throw new ApiError(error.message || 'Network error', 0);
  }
}

/**
 * Custom API Error class
 */
export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// Convenience methods
export const api = {
  get: (endpoint, options = {}) => 
    apiClient(endpoint, { ...options, method: 'GET' }),
  
  post: (endpoint, body, options = {}) => 
    apiClient(endpoint, { 
      ...options, 
      method: 'POST', 
      body: JSON.stringify(body) 
    }),
  
  put: (endpoint, body, options = {}) => 
    apiClient(endpoint, { 
      ...options, 
      method: 'PUT', 
      body: JSON.stringify(body) 
    }),
  
  patch: (endpoint, body, options = {}) => 
    apiClient(endpoint, { 
      ...options, 
      method: 'PATCH', 
      body: JSON.stringify(body) 
    }),
  
  delete: (endpoint, options = {}) => 
    apiClient(endpoint, { ...options, method: 'DELETE' }),
};

export default api;

