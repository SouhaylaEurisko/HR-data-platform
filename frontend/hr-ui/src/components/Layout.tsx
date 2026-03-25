import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import UserMenu from './UserMenu';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const canAddUser = user?.role === 'hr_manager';
  const isHome = location.pathname === '/';
  const isChat = location.pathname === '/chat';
  const isAuthPage = location.pathname.startsWith('/auth/');

  // Don't show layout on auth pages
  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <div className="layout">
      <nav className="navbar">
        <div className="nav-container">
          <Link to="/" className="nav-brand">
            <img
              src="/eurisko-logo.webp"
              alt="Eurisko"
              className="eurisko-logo-img"
            />
            <div className="nav-brand-divider" />
            <span className="nav-brand-product">HR Platform</span>
          </Link>

          <div className="nav-actions">
            {/* Home button — visible on all sub-pages */}
            {!isHome && (
              <button
                onClick={() => navigate('/')}
                className="nav-home-btn"
                aria-label="Go to Home"
              >
                <svg viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
                </svg>
              </button>
            )}

            {isAuthenticated && canAddUser && isHome && (
              <button
                type="button"
                className="nav-add-user-btn"
                onClick={() => navigate('/auth/signup')}
              >
                Add user
              </button>
            )}

            {/* User menu for authenticated users */}
            {isAuthenticated && <UserMenu />}
            
            {/* Login button for unauthenticated users */}
            {!isAuthenticated && (
              <button
                onClick={() => navigate('/auth/login')}
                className="nav-login-btn"
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      </nav>

      <main className="main-content">{children}</main>

      {/* Floating chat bubble — visible on all pages except Chat & Home */}
      {!isChat && !isHome && isAuthenticated && (
        <button
          className="floating-chat-btn"
          onClick={() => navigate('/chat')}
          aria-label="Open AI Chat"
        >
          <img
            src="/chatbot-avatar.webp"
            alt="AI Chat"
            className="floating-chat-img"
          />
          <span className="floating-chat-pulse" />
          <span className="floating-chat-tooltip">AI Assistant</span>
        </button>
      )}

      <footer className="footer">
        <div className="footer-container">
          <div className="footer-brand">
            <img
              src="/eurisko-logo.webp"
              alt="Eurisko"
              className="footer-logo-img"
            />
          </div>
          <div className="footer-links">
            <a href="https://eurisko.net" target="_blank" rel="noopener noreferrer">
              eurisko.net
            </a>
            <span className="footer-separator">·</span>
            <span className="footer-copyright">© {new Date().getFullYear()} Eurisko™ — All rights reserved.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}