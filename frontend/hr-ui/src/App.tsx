import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import UploadPage from './pages/UploadPage';
import CandidatesPage from './pages/CandidatesPage';
import CandidateDetailPage from './pages/CandidateDetailPage';
import ChatPage from './pages/ChatPage';
import './App.css';

export default function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          {/* Public auth routes - no layout */}
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="/auth/signup" element={<SignupPage />} />
          
          {/* Protected routes with layout */}
          <Route
            path="/"
            element={
              <Layout>
                <ProtectedRoute>
                  <HomePage />
                </ProtectedRoute>
              </Layout>
            }
          />
          <Route
            path="/upload"
            element={
              <Layout>
                <ProtectedRoute>
                  <UploadPage />
                </ProtectedRoute>
              </Layout>
            }
          />
          <Route
            path="/candidates"
            element={
              <Layout>
                <ProtectedRoute>
                  <CandidatesPage />
                </ProtectedRoute>
              </Layout>
            }
          />
          <Route
            path="/candidates/:id"
            element={
              <Layout>
                <ProtectedRoute>
                  <CandidateDetailPage />
                </ProtectedRoute>
              </Layout>
            }
          />
          <Route
            path="/chat"
            element={
              <Layout>
                <ProtectedRoute>
                  <ChatPage />
                </ProtectedRoute>
              </Layout>
            }
          />
          
          {/* Redirect unknown routes to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}