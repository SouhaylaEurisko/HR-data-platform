import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { listUsers, setUserActive } from '../api/auth';
import type { User } from '../types/api';
import './ManageUsersPage.css';

export default function ManageUsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    listUsers()
      .then(setUsers)
      .catch(() => setError('Failed to load users.'))
      .finally(() => setLoading(false));
  }, []);

  const handleToggle = async (userId: number, newActive: boolean) => {
    setTogglingId(userId);
    setError(null);
    try {
      const updated = await setUserActive(userId, newActive);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update user status.');
    } finally {
      setTogglingId(null);
    }
  };

  if (loading) {
    return (
      <div className="manage-users-page">
        <div className="mu-loading">Loading users...</div>
      </div>
    );
  }

  return (
    <div className="manage-users-page">
      <h1>Manage Users</h1>
      <p className="mu-subtitle">Activate or deactivate user accounts in your organization.</p>

      {error && <div className="mu-error" role="alert">{error}</div>}

      <div className="mu-table-wrapper">
        <table className="mu-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const isSelf = u.id === currentUser?.id;
              const name = [u.first_name, u.last_name].filter(Boolean).join(' ') || '—';
              return (
                <tr key={u.id} className={!u.is_active ? 'mu-row-inactive' : ''}>
                  <td>{name}</td>
                  <td>{u.email}</td>
                  <td>
                    <span className={`mu-role mu-role-${u.role}`}>
                      {u.role === 'hr_manager' ? 'Manager' : 'Viewer'}
                    </span>
                  </td>
                  <td>
                    <span className={`mu-status ${u.is_active ? 'mu-status-active' : 'mu-status-inactive'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    {isSelf ? (
                      <span className="mu-self-label">You</span>
                    ) : (
                      <button
                        type="button"
                        className={`mu-toggle-btn ${u.is_active ? 'mu-toggle-deactivate' : 'mu-toggle-activate'}`}
                        disabled={togglingId === u.id}
                        onClick={() => handleToggle(u.id, !u.is_active)}
                      >
                        {togglingId === u.id
                          ? 'Saving...'
                          : u.is_active
                          ? 'Deactivate'
                          : 'Activate'}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
