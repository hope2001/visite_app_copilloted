import { ApiError, NetworkError, fallbackCodeForStatus, isErrorEnvelope } from './errors';

const API_BASE = '/api/v1';

type QueryValue = string | number | undefined | null;

export interface RequestOptions {
  method?: 'GET' | 'POST';
  json?: unknown;
  form?: Record<string, string>;
  query?: object;
  /** Do not trigger the global "session expired" handler on 401 (e.g. the login call). */
  skipUnauthorizedHandler?: boolean;
}

let accessToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options);

  if (!response.ok) {
    const error = await toApiError(response);
    if (error.status === 401 && accessToken && !options.skipUnauthorizedHandler) {
      unauthorizedHandler?.();
    }
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  const headers = new Headers({ Accept: 'application/json' });
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);

  let body: BodyInit | undefined;
  if (options.json !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(options.json);
  } else if (options.form) {
    body = new URLSearchParams(options.form);
  }

  try {
    return await fetch(buildUrl(path, options.query), {
      method: options.method ?? 'GET',
      headers,
      body,
    });
  } catch {
    throw new NetworkError();
  }
}

export function buildUrl(path: string, query?: object): string {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  for (const [key, value] of Object.entries(query ?? {}) as [string, QueryValue][]) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function toApiError(response: Response): Promise<ApiError> {
  const headerRequestId = response.headers.get('X-Request-ID');
  try {
    const body: unknown = await response.json();
    if (isErrorEnvelope(body)) {
      const { code, message, details, request_id } = body.error;
      return new ApiError(
        response.status,
        code,
        message,
        details ?? [],
        request_id ?? headerRequestId,
      );
    }
  } catch {
    // Not JSON (e.g. proxy error page): fall through to a generic error.
  }
  return new ApiError(
    response.status,
    fallbackCodeForStatus(response.status),
    response.status >= 500
      ? 'The service is temporarily unavailable. Please try again.'
      : 'The request could not be completed.',
    [],
    headerRequestId,
  );
}
