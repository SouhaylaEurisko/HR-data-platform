import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

import { login as apiLogin, signup as apiSignup, getCurrentUser } from '../api/auth';
import type { AuthResponse, User } from '../types/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_TOKEN_KEY = 'auth_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!storedToken) {
      setIsLoading(false);
      return;
    }

    setToken(storedToken);

    getCurrentUser()
      .then((u) => setUser(u))
      .catch(() => {
        // Invalid token, clear it
        localStorage.removeItem(AUTH_TOKEN_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const handleAuthSuccess = (response: AuthResponse) => {
    setToken(response.access_token);
    setUser(response.user || null);
    localStorage.setItem(AUTH_TOKEN_KEY, response.access_token);
  };

  const handleLogin = async (email: string, password: string) => {
    const response = await apiLogin(email, password);
    handleAuthSuccess(response);
  };

  const handleSignup = async (email: string, password: string, fullName?: string) => {
    const response = await apiSignup({ email, password, full_name: fullName });
    handleAuthSuccess(response);
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem(AUTH_TOKEN_KEY);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user && !!token,
        login: handleLogin,
        signup: handleSignup,
        logout: handleLogout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}