import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getErrorMessage } from '../utils/errorHandler';
import './AuthPage.css';

export default function SignupPage() {
  const { createUserAsAdmin } = useAuth();
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'hr_manager' | 'hr_viewer'>('hr_viewer');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setIsSubmitting(true);
    try {
      const created = await createUserAsAdmin(email, password, firstName.trim(), lastName.trim(), role);
      setSuccessMessage(
        `User ${created.email} was created. Share the email and temporary password so they can sign in.`
      );
      setEmail('');
      setFirstName('');
      setLastName('');
      setPassword('');
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-page auth-page--in-layout">
      <main className="auth-main">
        <div className="auth-card auth-card-centered">
          <div className="auth-card-header">
            <h3 className="auth-card-title">Add user</h3>
            <p className="auth-card-subtitle">
              Create an account for a colleague in your organization. They will use these credentials to sign in.
            </p>
          </div>

          {successMessage && (
            <div className="auth-error" style={{ background: 'rgba(34, 197, 94, 0.12)', borderColor: 'rgba(34, 197, 94, 0.4)', color: '#166534' }}>
              {successMessage}
            </div>
          )}
          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="auth-form-row auth-form-row-split">
              <div className="auth-form-col">
                <label htmlFor="firstName" className="auth-label">
                  First name
                </label>
                <input
                  id="firstName"
                  type="text"
                  className="auth-input"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="John"
                  required
                  autoComplete="given-name"
                  maxLength={100}
                />
              </div>
              <div className="auth-form-col">
                <label htmlFor="lastName" className="auth-label">
                  Last name
                </label>
                <input
                  id="lastName"
                  type="text"
                  className="auth-input"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Doe"
                  required
                  autoComplete="family-name"
                  maxLength={100}
                />
              </div>
            </div>

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
              <label htmlFor="role" className="auth-label">
                Role
              </label>
              <select
                id="role"
                className="auth-input"
                value={role}
                onChange={(e) => setRole(e.target.value as 'hr_manager' | 'hr_viewer')}
              >
                <option value="hr_viewer">HR viewer (read-focused)</option>
                <option value="hr_manager">HR manager</option>
              </select>
            </div>

            <div className="auth-form-row">
              <label htmlFor="password" className="auth-label">
                Temporary password
              </label>
              <div className="auth-password-wrapper">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="auth-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <svg className="auth-password-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
                      <path fillRule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z" clipRule="evenodd" />
                      <path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z" />
                    </svg>
                  ) : (
                    <svg className="auth-password-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                      <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <button type="submit" className="auth-button" disabled={isSubmitting}>
              {isSubmitting ? 'Creating user...' : 'Create user'}
            </button>
          </form>

        </div>
      </main>
    </div>
  );
}

