import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getErrorMessage } from '../utils/errorHandler';
import './AuthPage.css';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      // Always redirect to home page after login
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <header className="auth-header">
        <div className="auth-header-inner">
          <img
            src="/eurisko-logo.webp"
            alt="Eurisko"
            className="auth-header-logo"
          />
          <span className="auth-header-title">HR Analytics Platform</span>
        </div>
      </header>

      <main className="auth-main">
        <div className="auth-card auth-card-centered">
          <div className="auth-card-header">
            <h3 className="auth-card-title">Sign In</h3>
            <p className="auth-card-subtitle">
              Use your email and password to access your candidate data.
            </p>
          </div>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="auth-form-row">
              <label htmlFor="email" className="auth-label">
                Email
              </label>
              <input
                id="email"
                type="email"
                className="auth-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="auth-form-row">
              <label htmlFor="password" className="auth-label">
                Password
              </label>
              <input
                id="password"
                type="password"
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>

            <button type="submit" className="auth-button" disabled={isSubmitting}>
              {isSubmitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="auth-meta">
            Don&apos;t have an account?{' '}
            <Link to="/auth/signup">Create an account</Link>
          </div>
        </div>
      </main>
    </div>
  );
}