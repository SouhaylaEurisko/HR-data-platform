import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import ChangePasswordPage from './pages/ChangePasswordPage';
import HrManagerRoute from './components/HrManagerRoute';
import HrWriteRoute from './components/HrWriteRoute';
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
          <Route
            path="/auth/signup"
            element={
              <ProtectedRoute>
                <HrManagerRoute>
                  <SignupPage />
                </HrManagerRoute>
              </ProtectedRoute>
            }
          />
          
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
                  <HrWriteRoute>
                    <UploadPage />
                  </HrWriteRoute>
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
          <Route
            path="/settings/change-password"
            element={
              <Layout>
                <ProtectedRoute>
                  <ChangePasswordPage />
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