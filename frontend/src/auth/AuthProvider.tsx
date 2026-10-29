import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { fetchCurrentUser, login as loginRequest } from '../api/auth';
import { setAccessToken, setUnauthorizedHandler } from '../api/client';
import { useNotify } from '../components/notifications';
import type { CurrentUser } from '../types/api';
import { AuthContext, type AuthContextValue, type AuthStatus } from './AuthContext';
import { tokenStorage } from './tokenStorage';

interface AuthState {
  status: AuthStatus;
  user: CurrentUser | null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [state, setState] = useState<AuthState>(() => ({
    status: tokenStorage.get() ? 'loading' : 'anonymous',
    user: null,
  }));

  const logout = useCallback(() => {
    tokenStorage.clear();
    setAccessToken(null);
    queryClient.clear();
    setState({ status: 'anonymous', user: null });
  }, [queryClient]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      notify('Your session has expired. Please sign in again.', 'error');
      logout();
    });
    return () => setUnauthorizedHandler(null);
  }, [logout, notify]);

  // Restore an existing session (page reload) by validating the stored token.
  useEffect(() => {
    const token = tokenStorage.get();
    if (!token) return;
    setAccessToken(token);
    let cancelled = false;
    fetchCurrentUser()
      .then((user) => {
        if (!cancelled) setState({ status: 'authenticated', user });
      })
      .catch(() => {
        if (!cancelled) logout();
      });
    return () => {
      cancelled = true;
    };
  }, [logout]);

  const login = useCallback(
    async (email: string, password: string) => {
      const token = await loginRequest(email, password);
      setAccessToken(token.access_token);
      try {
        const user = await fetchCurrentUser();
        tokenStorage.set(token.access_token);
        setState({ status: 'authenticated', user });
      } catch (error) {
        logout();
        throw error;
      }
    },
    [logout],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, logout }),
    [state, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
