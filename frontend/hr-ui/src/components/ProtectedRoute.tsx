import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    // Simple loading state; could be replaced with a spinner
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}