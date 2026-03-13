import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCandidates } from '../api/candidates';
import './HomePage.css';

export default function HomePage() {
  const navigate = useNavigate();
  const [candidateCount, setCandidateCount] = useState<number | null>(null);
  const [loadingCandidates, setLoadingCandidates] = useState(true);
  const [hoveredCard, setHoveredCard] = useState<number | null>(null);

  useEffect(() => {
    const checkCandidates = async () => {
      try {
        const response = await getCandidates({ page: 1, page_size: 1 });
        setCandidateCount(response.total);
      } catch {
        setCandidateCount(0);
      } finally {
        setLoadingCandidates(false);
      }
    };
    checkCandidates();
  }, []);

  const hasCandidates = candidateCount !== null && candidateCount > 0;

  return (
    <div className="home-page">
      {/* ——— 3D Hero Animation ——— */}
      <section className="hero-section">
        <div className="hero-bg-grid" />
        <div className="hero-glow hero-glow-1" />
        <div className="hero-glow hero-glow-2" />
        <div className="hero-glow hero-glow-3" />

        <div className="hero-content">
          <div className="hero-text">
            <div className="hero-badge">
              <span className="hero-badge-dot" />
              Powered by Eurisko
            </div>
            <h1 className="hero-title">
              <span className="hero-title-line">Intelligent</span>
              <span className="hero-title-line hero-title-gradient">HR Analytics</span>
              <span className="hero-title-line">Platform</span>
            </h1>
            <p className="hero-subtitle">
              Upload, explore, and query your candidate data with AI-powered natural language search.
            </p>
          </div>

          <div className="hero-3d-container">
            <div className="scene-3d">
              {/* Orbiting rings */}
              <div className="orbit orbit-1">
                <div className="orbit-dot" />
              </div>
              <div className="orbit orbit-2">
                <div className="orbit-dot" />
              </div>
              <div className="orbit orbit-3">
                <div className="orbit-dot" />
              </div>

              {/* Central 3D cube — Eurisko icon on each face */}
              <div className="cube-wrapper">
                <div className="cube">
                  <div className="cube-face cube-front">
                    <img src="/eurisko-icon.webp" alt="Eurisko" className="cube-logo-img" />
                  </div>
                  <div className="cube-face cube-back">
                    <img src="/eurisko-icon.webp" alt="Eurisko" className="cube-logo-img" />
                  </div>
                  <div className="cube-face cube-right">
                    <img src="/eurisko-icon.webp" alt="Eurisko" className="cube-logo-img" />
                  </div>
                  <div className="cube-face cube-left">
                    <img src="/eurisko-icon.webp" alt="Eurisko" className="cube-logo-img" />
                  </div>
                  <div className="cube-face cube-top">
                    <img src="/eurisko-icon.webp" alt="Eurisko" className="cube-logo-img" />
                  </div>
                  <div className="cube-face cube-bottom">
                    <img src="/eurisko-icon.webp" alt="Eurisko" className="cube-logo-img" />
                  </div>
                </div>
              </div>

              {/* Floating particles */}
              <div className="particle particle-1" />
              <div className="particle particle-2" />
              <div className="particle particle-3" />
              <div className="particle particle-4" />
              <div className="particle particle-5" />
              <div className="particle particle-6" />
            </div>
          </div>
        </div>
      </section>

      {/* ——— Option Cards ——— */}
      <section className="options-section">
        <div className="options-header">
          <h2 className="options-title">Get Started</h2>
          <p className="options-subtitle">Choose where you'd like to begin</p>
        </div>

        <div className="options-grid">
          {/* Card 1 — Upload */}
          <div
            className={`option-card option-card-upload ${hoveredCard === 1 ? 'hovered' : ''}`}
            onMouseEnter={() => setHoveredCard(1)}
            onMouseLeave={() => setHoveredCard(null)}
            onClick={() => navigate('/upload')}
          >
            <div className="card-glow card-glow-purple" />
            <div className="card-icon-wrapper">
              <div className="card-icon card-icon-upload">
                <svg viewBox="0 0 48 48" fill="none">
                  <path d="M14 32V28H34V32H14Z" fill="currentColor" opacity="0.3" />
                  <path d="M24 8L32 18H26V26H22V18H16L24 8Z" fill="currentColor" />
                  <path d="M10 36H38V40H10V36Z" fill="currentColor" opacity="0.2" />
                </svg>
              </div>
              <div className="card-icon-ring" />
            </div>
            <div className="card-content">
              <h3 className="card-title">Upload Data</h3>
              <p className="card-description">
                Import your Excel spreadsheets to populate the candidate database with structured data.
              </p>
            </div>
            <div className="card-action">
              <span className="card-action-text">Upload XLSX</span>
              <svg className="card-arrow" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="card-number">01</div>
          </div>

          {/* Card 2 — Candidates */}
          <div
            className={`option-card option-card-candidates ${hoveredCard === 2 ? 'hovered' : ''} ${!hasCandidates && !loadingCandidates ? 'card-disabled' : ''}`}
            onMouseEnter={() => setHoveredCard(2)}
            onMouseLeave={() => setHoveredCard(null)}
            onClick={() => hasCandidates ? navigate('/candidates') : undefined}
          >
            <div className="card-glow card-glow-violet" />
            <div className="card-icon-wrapper">
              <div className="card-icon card-icon-candidates">
                <svg viewBox="0 0 48 48" fill="none">
                  <circle cx="18" cy="16" r="6" fill="currentColor" opacity="0.7" />
                  <circle cx="34" cy="16" r="4" fill="currentColor" opacity="0.4" />
                  <path d="M6 38C6 31.373 11.373 26 18 26C24.627 26 30 31.373 30 38H6Z" fill="currentColor" opacity="0.5" />
                  <path d="M28 38C28 33.029 31.029 30 34 28C38.971 30 42 33.029 42 38H28Z" fill="currentColor" opacity="0.3" />
                </svg>
              </div>
              <div className="card-icon-ring" />
            </div>
            <div className="card-content">
              <h3 className="card-title">
                Explore Candidates
                {!loadingCandidates && (
                  <span className={`status-badge ${hasCandidates ? 'status-live' : 'status-empty'}`}>
                    {hasCandidates ? (
                      <>
                        <span className="status-dot status-dot-live" />
                        {candidateCount} available
                      </>
                    ) : (
                      <>
                        <span className="status-dot status-dot-empty" />
                        Empty
                      </>
                    )}
                  </span>
                )}
                {loadingCandidates && (
                  <span className="status-badge status-loading">
                    <span className="status-dot status-dot-loading" />
                    Checking...
                  </span>
                )}
              </h3>
              <p className="card-description">
                {hasCandidates
                  ? `Browse, filter, and sort through ${candidateCount} candidate${candidateCount !== 1 ? 's' : ''} in the database.`
                  : loadingCandidates
                  ? 'Checking database for candidate records...'
                  : 'No candidates in the database yet. Upload an Excel file first to get started.'}
              </p>
            </div>
            <div className="card-actions-group">
              {hasCandidates ? (
                <div className="card-action">
                  <span className="card-action-text">View Candidates</span>
                  <svg className="card-arrow" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </div>
              ) : !loadingCandidates ? (
                <div className="card-action-disabled">
                  <svg className="card-lock" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                  </svg>
                  <span>No data available</span>
                </div>
              ) : null}
              {(!hasCandidates && !loadingCandidates) && (
                <button
                  className="card-secondary-action"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate('/upload');
                  }}
                >
                  <svg viewBox="0 0 20 20" fill="currentColor" className="card-secondary-icon">
                    <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                  Upload Data First
                </button>
              )}
            </div>
            <div className="card-number">02</div>

            {/* Tooltip for disabled state */}
            {!hasCandidates && !loadingCandidates && (
              <div className="card-tooltip">
                No candidates found in the database. Please upload an Excel file to import candidate data.
              </div>
            )}
          </div>

          {/* Card 3 — AI Chat */}
          <div
            className={`option-card option-card-chat ${hoveredCard === 3 ? 'hovered' : ''}`}
            onMouseEnter={() => setHoveredCard(3)}
            onMouseLeave={() => setHoveredCard(null)}
            onClick={() => navigate('/chat')}
          >
            <div className="card-glow card-glow-indigo" />
            <div className="card-icon-wrapper">
              <div className="card-icon card-icon-chat card-icon-robot">
                <img src="/chatbot-avatar.webp" alt="AI Assistant" className="card-robot-img" />
              </div>
              <div className="card-icon-ring" />
            </div>
            <div className="card-content">
              <h3 className="card-title">
                AI Assistant
                <span className="ai-badge">AI</span>
              </h3>
              <p className="card-description">
                Ask questions in natural language to find, filter, and analyze candidates instantly.
              </p>
            </div>
            <div className="card-action">
              <span className="card-action-text">Start Chatting</span>
              <svg className="card-arrow" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="card-number">03</div>
          </div>
        </div>
      </section>
    </div>
  );
}