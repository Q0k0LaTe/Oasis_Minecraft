/**
 * App - Main application component with routing
 */

import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext.jsx';

// Pages
import AuthPage from './pages/AuthPage.jsx';
import WorkspaceListPage from './pages/WorkspaceListPage.jsx';
import WorkspaceIDEPage from './pages/WorkspaceIDEPage.jsx';

/**
 * ProtectedRoute - Redirects to login if not authenticated
 */
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login, saving the attempted location
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
  }

/**
 * PublicRoute - Redirects to workspaces if already authenticated
 */
function PublicRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/workspaces" replace />;
  }

  return children;
}

/**
 * AppRoutes - Route definitions
 */
function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <AuthPage />
          </PublicRoute>
        }
      />

      {/* Protected routes */}
      <Route
        path="/workspaces"
        element={
          <ProtectedRoute>
            <WorkspaceListPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/workspace/:workspaceId"
        element={
          <ProtectedRoute>
            <WorkspaceIDEPage />
          </ProtectedRoute>
        }
      />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/workspaces" replace />} />
      
      {/* 404 - redirect to home */}
      <Route path="*" element={<Navigate to="/workspaces" replace />} />
    </Routes>
  );
}

/**
 * App - Root component
 */
export default function App() {
  return (
    <AuthProvider>
      <div className="app">
        <AppRoutes />
      </div>
    </AuthProvider>
  );
}
