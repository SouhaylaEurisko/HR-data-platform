import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function UserMenu() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  if (!isAuthenticated || !user) {
    return null;
  }

  const initials = user.full_name
    ? user.full_name
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((n) => n[0]?.toUpperCase())
        .join('')
    : user.email[0]?.toUpperCase();

  const handleAction = () => {
    logout();
    navigate('/auth/login', { replace: true });
  };

  return (
    <div className="user-menu">
      <button
        type="button"
        className="user-menu-btn"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="true"
        aria-expanded={open}
      >
        <div className="user-avatar-circle">
          <span>{initials}</span>
        </div>
      </button>
      {open && (
        <div className="user-menu-dropdown">
          <div className="user-menu-email">{user.email}</div>
          <button type="button" className="user-menu-item" onClick={handleAction}>
            Log out
          </button>
          <button type="button" className="user-menu-item" onClick={handleAction}>
            Change account
          </button>
        </div>
      )}
    </div>
  );
}