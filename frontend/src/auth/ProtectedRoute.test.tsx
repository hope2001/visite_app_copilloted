import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Route } from 'react-router-dom';
import { renderWithProviders, security } from '../test/utils';
import { ProtectedRoute } from './ProtectedRoute';

describe('ProtectedRoute', () => {
  it('redirects anonymous users to the login page', () => {
    renderWithProviders(
      <ProtectedRoute>
        <p>secret</p>
      </ProtectedRoute>,
      { user: null, route: '/today', path: '/today', extraRoutes: <Route path="/login" element={<p>login page</p>} /> },
    );

    expect(screen.getByText('login page')).toBeInTheDocument();
    expect(screen.queryByText('secret')).not.toBeInTheDocument();
  });

  it('shows the forbidden page when the role is not allowed', () => {
    renderWithProviders(
      <ProtectedRoute roles={['ADMIN']}>
        <p>admin only</p>
      </ProtectedRoute>,
      { user: security },
    );

    expect(screen.getByRole('heading', { name: 'Access denied' })).toBeInTheDocument();
    expect(screen.queryByText('admin only')).not.toBeInTheDocument();
  });

  it('renders children for an allowed role', () => {
    renderWithProviders(
      <ProtectedRoute roles={['SECURITY', 'ADMIN']}>
        <p>front desk</p>
      </ProtectedRoute>,
      { user: security },
    );

    expect(screen.getByText('front desk')).toBeInTheDocument();
  });
});
