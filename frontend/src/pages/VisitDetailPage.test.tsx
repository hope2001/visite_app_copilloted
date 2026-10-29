import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { employee, makeVisit, renderWithProviders, security } from '../test/utils';
import type { CurrentUser, Visit } from '../types/api';
import { VisitDetailPage } from './VisitDetailPage';

const PASS_CODE = 'VP1-GMZTGMZTGMZTGMZTGMZTGMZTGMZTGMZTAAAAAAAAAAAAAAAAAAAAAAAA';

function renderPage(visit: Visit, user: CurrentUser) {
  let passRequests = 0;
  server.use(
    http.get('/api/v1/visits/:visitId', () => HttpResponse.json(visit)),
    http.get('/api/v1/visits/:visitId/audit', () => HttpResponse.json([])),
    http.get('/api/v1/visits/:visitId/pass', () => {
      passRequests += 1;
      return HttpResponse.json({ visit_id: visit.id, code: PASS_CODE });
    }),
  );
  renderWithProviders(<VisitDetailPage />, {
    user,
    route: `/visits/${visit.id}`,
    path: '/visits/:visitId',
  });
  return { passRequests: () => passRequests };
}

describe('VisitDetailPage visitor pass', () => {
  it('shows a scannable QR pass to the registrant of an expected visit', async () => {
    renderPage(makeVisit(), employee);

    const qr = await screen.findByRole('img', { name: 'QR visitor pass for Victor Visitor' });
    expect(qr.tagName.toLowerCase()).toBe('svg');
    expect(screen.getByText(PASS_CODE)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Print pass' })).toBeInTheDocument();
  });

  it('does not offer a pass once the visitor has arrived', async () => {
    const { passRequests } = renderPage(
      makeVisit({ status: 'CHECKED_IN', checked_in_at: '2026-10-28T08:00:00Z' }),
      employee,
    );

    await screen.findByRole('heading', { name: 'Victor Visitor' });
    expect(screen.queryByText('Visitor pass')).not.toBeInTheDocument();
    expect(passRequests()).toBe(0);
  });

  it('does not show or fetch the pass for security officers', async () => {
    const { passRequests } = renderPage(makeVisit(), security);

    await screen.findByRole('heading', { name: 'Victor Visitor' });
    expect(screen.queryByText('Visitor pass')).not.toBeInTheDocument();
    expect(passRequests()).toBe(0);
  });
});
