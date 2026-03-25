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

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ');
  const initials = fullName
    ? fullName
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((n) => n[0]?.toUpperCase())
        .join('')
    : user.email[0]?.toUpperCase();

  const handleLogout = () => {
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
          {user.role === 'hr_manager' && (
            <>
              <button
                type="button"
                className="user-menu-item"
                onClick={() => {
                  setOpen(false);
                  navigate('/auth/signup');
                }}
              >
                Add user
              </button>
              <button
                type="button"
                className="user-menu-item"
                onClick={() => {
                  setOpen(false);
                  navigate('/settings/users');
                }}
              >
                Manage users
              </button>
            </>
          )}
          <button
            type="button"
            className="user-menu-item"
            onClick={() => {
              setOpen(false);
              navigate('/settings/change-password');
            }}
          >
            Change password
          </button>
          <button type="button" className="user-menu-item" onClick={handleLogout}>
            Log out
          </button>
        </div>
      )}
    </div>
  );
}