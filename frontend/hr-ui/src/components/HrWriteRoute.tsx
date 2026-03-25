import { Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface HrWriteRouteProps {
  children: ReactNode;
}

/**
 * Only hr_manager may access write-heavy routes (e.g. upload).
 * hr_viewer is redirected to home (read-only).
 */
export default function HrWriteRoute({ children }: HrWriteRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="auth-loading">Loading...</div>;
  }

  if (!user || user.role !== 'hr_manager') {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
