import { Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../contexts/AuthContext';

const HR_MANAGER = 'hr_manager';

interface HrManagerRouteProps {
  children: ReactNode;
}

/**
 * Only users with role hr_manager may access child routes (e.g. Add user).
 */
export default function HrManagerRoute({ children }: HrManagerRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="auth-loading">Loading...</div>;
  }

  if (!user || user.role !== HR_MANAGER) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
