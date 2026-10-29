import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { employee, makeVisit, renderWithProviders } from '../test/utils';
import type { VisitCreateRequest } from '../types/api';
import { RegisterVisitPage } from './RegisterVisitPage';

function renderPage() {
  server.use(http.get('/api/v1/users/hosts', () => HttpResponse.json([employee])));
  return renderWithProviders(<RegisterVisitPage />, {
    route: '/visits/new',
    path: '/visits/new',
    extraRoutes: <Route path="/visits/:visitId" element={<p>visit detail</p>} />,
  });
}

async function fillValidForm() {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText('Full name'), 'Victor Visitor');
  await user.type(screen.getByLabelText('Email'), 'victor@example.com');
  await user.type(screen.getByLabelText('Company'), 'Globex');
  await user.type(screen.getByLabelText('Purpose'), 'Quarterly review');
  return user;
}

describe('RegisterVisitPage', () => {
  it('shows client-side validation errors without calling the API', async () => {
    renderPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: 'Register visit' }));

    expect(await screen.findByText('Visitor name is required')).toBeInTheDocument();
    expect(screen.getByText('Email is required')).toBeInTheDocument();
  });

  it('maps API 422 field errors onto the form', async () => {
    renderPage();
    server.use(
      http.post('/api/v1/visits', () =>
        HttpResponse.json(
          {
            error: {
              code: 'VALIDATION_ERROR',
              message: 'The request contains invalid data.',
              details: [{ field: 'visitor.email', issue: 'This email domain is not accepted' }],
              request_id: 'req-12345678',
            },
          },
          { status: 422 },
        ),
      ),
    );
    const user = await fillValidForm();

    await user.click(screen.getByRole('button', { name: 'Register visit' }));

    expect(await screen.findByText('This email domain is not accepted')).toBeInTheDocument();
  });

  it('shows a form-level error with a reference for server failures', async () => {
    renderPage();
    server.use(
      http.post('/api/v1/visits', () =>
        HttpResponse.json(
          {
            error: {
              code: 'INTERNAL_ERROR',
              message: 'An unexpected error occurred. Please try again later.',
              details: [],
              request_id: 'req-87654321',
            },
          },
          { status: 500 },
        ),
      ),
    );
    const user = await fillValidForm();

    await user.click(screen.getByRole('button', { name: 'Register visit' }));

    expect(await screen.findByText(/Reference: req-87654321/)).toBeInTheDocument();
  });

  it('submits the visit and opens its detail page', async () => {
    renderPage();
    let received: VisitCreateRequest | null = null;
    server.use(
      http.post('/api/v1/visits', async ({ request }) => {
        received = (await request.json()) as VisitCreateRequest;
        return HttpResponse.json(makeVisit(), { status: 201 });
      }),
    );
    const user = await fillValidForm();

    await user.click(screen.getByRole('button', { name: 'Register visit' }));

    expect(await screen.findByText('visit detail')).toBeInTheDocument();
    expect(received).toMatchObject({
      visitor: { full_name: 'Victor Visitor', email: 'victor@example.com', phone: null },
      host_id: employee.id,
    });
  });
});
