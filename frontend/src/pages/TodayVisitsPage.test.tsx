import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { makeVisit, renderWithProviders, security } from '../test/utils';
import { TodayVisitsPage } from './TodayVisitsPage';

const expected = makeVisit({ id: 'b0000000-0000-4000-8000-000000000001', status: 'EXPECTED' });
const onSite = makeVisit({
  id: 'b0000000-0000-4000-8000-000000000002',
  status: 'CHECKED_IN',
  checked_in_at: '2026-10-28T08:00:00Z',
  visitor: { ...expected.visitor, full_name: 'Olivia Onsite' },
});

function renderPage() {
  server.use(http.get('/api/v1/visits/today', () => HttpResponse.json([expected, onSite])));
  return renderWithProviders(<TodayVisitsPage />, { user: security, route: '/today' });
}

describe('TodayVisitsPage (security desk)', () => {
  it('filters the list by status', async () => {
    renderPage();
    const user = userEvent.setup();
    await screen.findByText('Olivia Onsite');

    await user.click(screen.getByRole('button', { name: /^On site/ }));

    expect(screen.getByRole('button', { name: /^On site/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByText('Olivia Onsite')).toBeInTheDocument();
    expect(screen.queryByText('Victor Visitor')).not.toBeInTheDocument();
  });

  it('checks a visitor in and confirms with a notification', async () => {
    let checkedIn: string | undefined;
    renderPage();
    server.use(
      http.post('/api/v1/visits/:visitId/check-in', ({ params }) => {
        checkedIn = String(params.visitId);
        return HttpResponse.json({ ...expected, status: 'CHECKED_IN' });
      }),
    );
    const user = userEvent.setup();

    const row = (await screen.findByText('Victor Visitor')).closest('tr');
    expect(row).not.toBeNull();
    await user.click(within(row as HTMLElement).getByRole('button', { name: 'Check in' }));

    expect(await screen.findByText('Victor Visitor checked in.')).toBeInTheDocument();
    expect(checkedIn).toBe(expected.id);
  });
});

describe('TodayVisitsPage visitor pass scanning', () => {
  const PASS_CODE = 'VP1-ABCDEFGHIJKLMNOPQRSTUVWXYZ234567ABCDEFGHIJKLMNOPQRSTUV';
  const scanned = makeVisit({
    id: 'b0000000-0000-4000-8000-000000000003',
    visitor: { ...expected.visitor, full_name: 'Paula Pass' },
  });

  function scanPanel() {
    return screen
      .getByRole('heading', { name: 'Scan visitor pass' })
      .closest('section') as HTMLElement;
  }

  it('identifies the visit from a scanned pass, then checks in through the normal flow', async () => {
    let lookupBody: unknown;
    let checkedIn: string | undefined;
    let current: typeof scanned = scanned;
    renderPage();
    server.use(
      http.post('/api/v1/visits/pass-lookup', async ({ request }) => {
        lookupBody = await request.json();
        return HttpResponse.json(current);
      }),
      http.get(`/api/v1/visits/${scanned.id}`, () => HttpResponse.json(current)),
      http.post('/api/v1/visits/:visitId/check-in', ({ params }) => {
        checkedIn = String(params.visitId);
        current = { ...scanned, status: 'CHECKED_IN', checked_in_at: '2026-10-28T09:00:00Z' };
        return HttpResponse.json(current);
      }),
    );
    const user = userEvent.setup();

    // Keyboard-wedge scanners type the code and press Enter.
    await user.type(screen.getByLabelText('Pass code'), `${PASS_CODE}{Enter}`);

    const panel = scanPanel();
    expect(await within(panel).findByRole('heading', { name: 'Paula Pass' })).toBeInTheDocument();
    expect(lookupBody).toEqual({ code: PASS_CODE });
    // The code is sent in the body only, and the field is cleared for the next scan.
    expect(screen.getByLabelText('Pass code')).toHaveValue('');
    expect(checkedIn).toBeUndefined();

    await user.click(within(panel).getByRole('button', { name: 'Check in' }));

    expect(await screen.findByText('Paula Pass checked in.')).toBeInTheDocument();
    expect(checkedIn).toBe(scanned.id);
    expect(await within(panel).findByText('On site')).toBeInTheDocument();
    expect(within(panel).queryByRole('button', { name: 'Check in' })).not.toBeInTheDocument();
  });

  it('shows a clear error for an invalid pass', async () => {
    renderPage();
    server.use(
      http.post('/api/v1/visits/pass-lookup', () =>
        HttpResponse.json(
          {
            error: {
              code: 'VISITOR_PASS_INVALID',
              message: "This visitor pass is not valid. Find the visitor in today's list instead.",
              details: [],
              request_id: 'req-12345678',
            },
          },
          { status: 404 },
        ),
      ),
    );
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Pass code'), 'VP1-FORGED{Enter}');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "This visitor pass is not valid. Find the visitor in today's list instead.",
    );
    expect(within(scanPanel()).queryByRole('button', { name: 'Check in' })).not.toBeInTheDocument();
  });
});
