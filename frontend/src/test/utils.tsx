import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthContext, type AuthContextValue } from '../auth/AuthContext';
import { NotificationsProvider } from '../components/NotificationsProvider';
import type { CurrentUser, Visit } from '../types/api';

export const employee: CurrentUser = {
  id: '11111111-1111-4111-8111-111111111111',
  full_name: 'Alice Employee',
  email: 'alice@acme-corp.com',
  role: 'EMPLOYEE',
};

export const security: CurrentUser = {
  id: '22222222-2222-4222-8222-222222222222',
  full_name: 'Sam Security',
  email: 'sam@acme-corp.com',
  role: 'SECURITY',
};

export function makeVisit(overrides: Partial<Visit> = {}): Visit {
  return {
    id: '33333333-3333-4333-8333-333333333333',
    visitor: {
      id: '44444444-4444-4444-8444-444444444444',
      full_name: 'Victor Visitor',
      email: 'victor@example.com',
      phone: null,
      company: 'Globex',
    },
    host: employee,
    registered_by: employee,
    purpose: 'Quarterly review',
    expected_date: '2026-10-28',
    status: 'EXPECTED',
    checked_in_at: null,
    checked_out_at: null,
    cancelled_at: null,
    created_at: '2026-10-27T10:00:00Z',
    ...overrides,
  };
}

interface RenderOptions {
  user?: CurrentUser | null;
  route?: string;
  path?: string;
  extraRoutes?: ReactElement;
}

export function renderWithProviders(
  ui: ReactElement,
  { user = employee, route = '/', path = '*', extraRoutes }: RenderOptions = {},
): RenderResult {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const auth: AuthContextValue = {
    status: user ? 'authenticated' : 'anonymous',
    user,
    login: async () => undefined,
    logout: () => undefined,
  };

  return render(
    <QueryClientProvider client={queryClient}>
      <NotificationsProvider>
        <AuthContext.Provider value={auth}>
          <MemoryRouter initialEntries={[route]}>
            <Routes>
              <Route path={path} element={ui} />
              {extraRoutes}
            </Routes>
          </MemoryRouter>
        </AuthContext.Provider>
      </NotificationsProvider>
    </QueryClientProvider>,
  );
}
