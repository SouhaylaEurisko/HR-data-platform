import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '3rem',
          textAlign: 'center',
          backgroundColor: '#0A0E1A',
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: "'Inter', system-ui, sans-serif",
        }}>
          <div style={{
            backgroundColor: '#181F35',
            border: '1px solid #1E293B',
            borderRadius: '0.75rem',
            padding: '2.5rem',
            maxWidth: '500px',
            width: '100%',
            boxShadow: '0 8px 28px rgba(0, 0, 0, 0.6)',
          }}>
            <div style={{
              width: '48px',
              height: '48px',
              margin: '0 auto 1.5rem',
              borderRadius: '50%',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.5rem',
            }}>
              ⚠️
            </div>
            <h1 style={{
              color: '#F1F5F9',
              fontSize: '1.5rem',
              marginBottom: '0.75rem',
              fontWeight: 600,
            }}>
              Something went wrong
            </h1>
            <p style={{
              color: '#EF4444',
              marginBottom: '1.5rem',
              fontSize: '0.9rem',
              lineHeight: 1.5,
            }}>
              {this.state.error?.message}
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '0.75rem 2rem',
                background: 'linear-gradient(135deg, #A855F7 0%, #7C3AED 50%, #6366F1 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '0.9rem',
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}
            >
              Reload Page
            </button>
            <div style={{ marginTop: '2rem' }}>
              <img
                src="/eurisko-logo.webp"
                alt="Eurisko"
                style={{ height: '18px', opacity: 0.5 }}
              />
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
