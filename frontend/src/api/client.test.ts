import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { server } from '../test/server';
import { apiRequest, buildUrl, setAccessToken, setUnauthorizedHandler } from './client';
import { ApiError, NetworkError, describeError } from './errors';

describe('apiRequest', () => {
  it('sends the bearer token and returns the parsed body', async () => {
    let authorization: string | null = null;
    server.use(
      http.get('/api/v1/auth/me', ({ request }) => {
        authorization = request.headers.get('Authorization');
        return HttpResponse.json({ id: '1' });
      }),
    );
    setAccessToken('abc');

    await expect(apiRequest('/auth/me')).resolves.toEqual({ id: '1' });
    expect(authorization).toBe('Bearer abc');
  });

  it('turns the error envelope into an ApiError', async () => {
    server.use(
      http.post('/api/v1/visits', () =>
        HttpResponse.json(
          {
            error: {
              code: 'VALIDATION_ERROR',
              message: 'The request contains invalid data.',
              details: [{ field: 'visitor.email', issue: 'Invalid email' }],
              request_id: 'req-12345678',
            },
          },
          { status: 422 },
        ),
      ),
    );

    const error = await apiRequest('/visits', { method: 'POST', json: {} }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      code: 'VALIDATION_ERROR',
      details: [{ field: 'visitor.email', issue: 'Invalid email' }],
      requestId: 'req-12345678',
    });
  });

  it('handles non-JSON gateway errors', async () => {
    server.use(
      http.get('/api/v1/visits/today', () =>
        new HttpResponse('<html>Bad gateway</html>', {
          status: 502,
          headers: { 'Content-Type': 'text/html', 'X-Request-ID': 'proxy-123456' },
        }),
      ),
    );

    const error = await apiRequest('/visits/today').catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 502, code: 'SERVICE_UNAVAILABLE' });
    expect(describeError(error)).toContain('Reference: proxy-123456');
  });

  it('raises NetworkError when the server is unreachable', async () => {
    server.use(http.get('/api/v1/health', () => HttpResponse.error()));

    await expect(apiRequest('/health')).rejects.toBeInstanceOf(NetworkError);
  });

  it('calls the unauthorized handler on 401 for authenticated requests only', async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    server.use(
      http.get('/api/v1/auth/me', () =>
        HttpResponse.json(
          { error: { code: 'AUTH_TOKEN_EXPIRED', message: 'Expired', details: [], request_id: null } },
          { status: 401 },
        ),
      ),
    );

    await apiRequest('/auth/me').catch(() => undefined);
    expect(onUnauthorized).not.toHaveBeenCalled();

    setAccessToken('expired');
    await apiRequest('/auth/me').catch(() => undefined);
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });
});

describe('buildUrl', () => {
  it('skips empty query values', () => {
    const url = new URL(buildUrl('/visits', { status: 'EXPECTED', q: '', host_id: undefined }));
    expect(url.pathname).toBe('/api/v1/visits');
    expect(url.search).toBe('?status=EXPECTED');
  });
});
