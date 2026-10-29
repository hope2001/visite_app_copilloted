import type { ErrorCode, ErrorDetail, ErrorEnvelope } from '../types/api';

export class ApiError extends Error {
  readonly status: number;
  readonly code: ErrorCode;
  readonly details: readonly ErrorDetail[];
  readonly requestId: string | null;

  constructor(
    status: number,
    code: ErrorCode,
    message: string,
    details: readonly ErrorDetail[] = [],
    requestId: string | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }
}

export class NetworkError extends Error {
  constructor(message = 'Unable to reach the server. Check your connection and try again.') {
    super(message);
    this.name = 'NetworkError';
  }
}

export function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false;
  const error = (value as { error: unknown }).error;
  return (
    typeof error === 'object' &&
    error !== null &&
    typeof (error as { code?: unknown }).code === 'string' &&
    typeof (error as { message?: unknown }).message === 'string'
  );
}

export function fallbackCodeForStatus(status: number): ErrorCode {
  if (status === 401) return 'AUTH_TOKEN_INVALID';
  if (status === 403) return 'FORBIDDEN';
  if (status === 404) return 'NOT_FOUND';
  if (status === 409) return 'CONFLICT';
  if (status === 422) return 'VALIDATION_ERROR';
  if (status === 429) return 'RATE_LIMITED';
  if (status === 502 || status === 503 || status === 504) return 'SERVICE_UNAVAILABLE';
  return 'INTERNAL_ERROR';
}

const GENERIC_MESSAGE = 'Something went wrong. Please try again.';

/** User-facing message for any thrown value. Adds a support reference for server errors. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.isServerError && error.requestId
      ? `${error.message} (Reference: ${error.requestId})`
      : error.message;
  }
  if (error instanceof NetworkError) return error.message;
  return GENERIC_MESSAGE;
}
