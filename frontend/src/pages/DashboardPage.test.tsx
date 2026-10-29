import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { todayIsoDate } from '../lib/format';
import { server } from '../test/server';
import { employee, makeVisit, renderWithProviders, security } from '../test/utils';
import { DashboardPage } from './DashboardPage';

const TODAY_VISITS = [
  makeVisit({ id: 'a0000000-0000-4000-8000-000000000001', status: 'EXPECTED' }),
  makeVisit({ id: 'a0000000-0000-4000-8000-000000000002', status: 'EXPECTED' }),
  makeVisit({ id: 'a0000000-0000-4000-8000-000000000003', status: 'CHECKED_IN' }),
  makeVisit({ id: 'a0000000-0000-4000-8000-000000000004', status: 'CHECKED_OUT' }),
];

async function expectStat(label: string, value: string) {
  const card = await screen.findByRole('article', { name: label });
  expect(await within(card).findByText(value)).toBeInTheDocument();
}

describe('DashboardPage', () => {
  it('shows site-wide counts for the front desk', async () => {
    server.use(http.get('/api/v1/visits/today', () => HttpResponse.json(TODAY_VISITS)));

    renderWithProviders(<DashboardPage />, { user: security });

    await expectStat('Expected today', '2');
    await expectStat('Currently on site', '1');
    await expectStat('Checked out today', '1');
    expect(screen.getByRole('link', { name: 'Open security desk' })).toHaveAttribute(
      'href',
      '/today',
    );
    expect(screen.queryByRole('link', { name: 'Register visitor' })).not.toBeInTheDocument();
  });

  it("shows an employee's own visits for today", async () => {
    let requested: URLSearchParams | undefined;
    server.use(
      http.get('/api/v1/visits', ({ request }) => {
        requested = new URL(request.url).searchParams;
        return HttpResponse.json({ items: TODAY_VISITS.slice(2), total: 2, page: 1, size: 100 });
      }),
    );

    renderWithProviders(<DashboardPage />, { user: employee });

    await expectStat('Currently on site', '1');
    await expectStat('Expected today', '0');
    expect(requested?.get('date_from')).toBe(todayIsoDate());
    expect(requested?.get('date_to')).toBe(todayIsoDate());
    expect(screen.getByRole('link', { name: 'Register visitor' })).toHaveAttribute(
      'href',
      '/visits/new',
    );
  });

  it('shows an empty state when nothing is scheduled', async () => {
    server.use(http.get('/api/v1/visits/today', () => HttpResponse.json([])));

    renderWithProviders(<DashboardPage />, { user: security });

    expect(await screen.findByText('No visitors are expected on site today.')).toBeInTheDocument();
  });

  it('shows an error with a working retry', async () => {
    let fail = true;
    server.use(
      http.get('/api/v1/visits/today', () =>
        fail
          ? HttpResponse.json(
              {
                error: {
                  code: 'INTERNAL_ERROR',
                  message: 'An unexpected error occurred. Please try again later.',
                  details: [],
                  request_id: 'req-11112222',
                },
              },
              { status: 500 },
            )
          : HttpResponse.json(TODAY_VISITS),
      ),
    );
    renderWithProviders(<DashboardPage />, { user: security });

    const retry = await screen.findByRole('button', { name: 'Try again' });
    fail = false;
    await userEvent.setup().click(retry);

    await expectStat('Expected today', '2');
  });
});
