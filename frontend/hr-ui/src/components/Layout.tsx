import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="layout">
      <nav className="navbar">
        <div className="nav-container">
          <h1 className="nav-title">HR Data Platform</h1>
          <ul className="nav-links">
            <li>
              <Link
                to="/upload"
                className={isActive('/upload') ? 'active' : ''}
              >
                Upload
              </Link>
            </li>
            <li>
              <Link
                to="/candidates"
                className={isActive('/candidates') ? 'active' : ''}
              >
                Candidates
              </Link>
            </li>
            <li>
              <Link
                to="/chat"
                className={isActive('/chat') ? 'active' : ''}
              >
                Chat
              </Link>
            </li>
          </ul>
        </div>
      </nav>
      <main className="main-content">{children}</main>
    </div>
  );
}
