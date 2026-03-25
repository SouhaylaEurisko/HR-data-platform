import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

import { login as apiLogin, createUserAsAdmin as apiCreateUserAdmin, getCurrentUser } from '../api/auth';
import { clearChatLocalStorage } from '../constants/chatStorage';
import type { AuthResponse, User } from '../types/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  /** True when user can mutate data (import, HR comments, status, etc.). Only hr_manager. */
  canWrite: boolean;
  login: (email: string, password: string) => Promise<void>;
  /** HR manager only — creates a user in the same org; does not switch session. */
  createUserAsAdmin: (
    email: string,
    password: string,
    firstName: string,
    lastName: string,
    role: 'hr_manager' | 'hr_viewer'
  ) => Promise<User>;
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
    clearChatLocalStorage();
    setToken(response.access_token);
    setUser(response.user || null);
    localStorage.setItem(AUTH_TOKEN_KEY, response.access_token);
  };

  const handleLogin = async (email: string, password: string) => {
    const response = await apiLogin(email, password);
    handleAuthSuccess(response);
  };

  const handleCreateUserAsAdmin = async (
    email: string,
    password: string,
    firstName: string,
    lastName: string,
    role: 'hr_manager' | 'hr_viewer'
  ) => {
    return apiCreateUserAdmin({
      email,
      password,
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      role,
    });
  };

  const handleLogout = () => {
    clearChatLocalStorage();
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
        canWrite: user?.role === 'hr_manager',
        login: handleLogin,
        createUserAsAdmin: handleCreateUserAsAdmin,
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