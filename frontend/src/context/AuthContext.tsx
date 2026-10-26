import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { UserProfile, UserRole } from '../types';
import { api, getStoredToken, setStoredToken } from '../services/api';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<UserProfile>;
  register: (email: string, password: string, fullName: string) => Promise<UserProfile>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  deleteAccount: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCurrentUser = useCallback(async (): Promise<UserProfile | null> => {
    const currentToken = getStoredToken();
    if (!currentToken) {
      setUser(null);
      setIsLoading(false);
      return null;
    }

    try {
      setIsLoading(true);
      const profile = await api.getMe();
      setUser(profile);
      setError(null);
      return profile;
    } catch (err: any) {
      console.warn('Authentication session expired or invalid:', err?.message);
      setStoredToken(null);
      setToken(null);
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  const login = async (email: string, password: string): Promise<UserProfile> => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.login({ email, password });
      setStoredToken(res.access_token);
      setToken(res.access_token);
      const profile = await fetchCurrentUser();
      if (!profile) {
        throw new Error('Failed to retrieve user profile.');
      }
      return profile;
    } catch (err: any) {
      const msg = err?.message || 'Login failed. Please check your credentials.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, fullName: string): Promise<UserProfile> => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.register({ email, password, full_name: fullName });
      setStoredToken(res.access_token);
      setToken(res.access_token);
      const profile = await fetchCurrentUser();
      if (!profile) {
        throw new Error('Failed to retrieve user profile after registration.');
      }
      return profile;
    } catch (err: any) {
      const msg = err?.message || 'Registration failed.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.logout().catch(() => {});
    setStoredToken(null);
    setToken(null);
    setUser(null);
    setError(null);
  };

  const deleteAccount = async () => {
    try {
      setIsLoading(true);
      await api.deleteMyAccount();
      logout();
    } catch (err: any) {
      const msg = err?.message || 'Failed to delete account.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => setError(null);

  const isAuthenticated = !!user;
  const isAdmin = user?.role === 'admin';
  const role = user?.role || null;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role,
        isAuthenticated,
        isAdmin,
        isLoading,
        error,
        login,
        register,
        logout,
        refreshUser: async () => {
          await fetchCurrentUser();
        },
        deleteAccount,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
