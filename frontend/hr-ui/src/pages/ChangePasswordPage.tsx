import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { changePassword } from '../api/auth';
import { getErrorMessage } from '../utils/errorHandler';
import './AuthPage.css';

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }
    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters.');
      return;
    }
    setIsSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      setSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="change-password-page" style={{ maxWidth: 520, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Change password</h1>
      <p style={{ color: 'var(--text-muted, #64748b)', marginBottom: '1.5rem' }}>
        Enter your current password, then choose a new one.
      </p>

      {success && (
        <div className="auth-error" style={{ background: 'rgba(34, 197, 94, 0.12)', borderColor: 'rgba(34, 197, 94, 0.4)', color: '#166534' }}>
          Password updated successfully.
        </div>
      )}
      {error && <div className="auth-error">{error}</div>}

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="auth-form-row">
          <label htmlFor="current" className="auth-label">
            Current password
          </label>
          <input
            id="current"
            type="password"
            className="auth-input"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        <div className="auth-form-row">
          <label htmlFor="newpass" className="auth-label">
            New password
          </label>
          <input
            id="newpass"
            type="password"
            className="auth-input"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={6}
            autoComplete="new-password"
          />
        </div>
        <div className="auth-form-row">
          <label htmlFor="confirm" className="auth-label">
            Confirm new password
          </label>
          <input
            id="confirm"
            type="password"
            className="auth-input"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={6}
            autoComplete="new-password"
          />
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button type="submit" className="auth-button" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Update password'}
          </button>
          <button
            type="button"
            className="auth-button"
            style={{ background: 'transparent', border: '1px solid var(--border, #e2e8f0)', color: 'inherit' }}
            onClick={() => navigate('/')}
          >
            Back to home
          </button>
        </div>
      </form>
    </div>
  );
}
