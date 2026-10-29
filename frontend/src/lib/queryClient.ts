import { QueryClient } from '@tanstack/react-query';
import { ApiError, NetworkError } from '../api/errors';

const MAX_QUERY_RETRIES = 2;

/** Retry reads only for transient failures; client errors (4xx) are never retried. */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_QUERY_RETRIES) return false;
  if (error instanceof NetworkError) return true;
  return error instanceof ApiError && error.isServerError;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetryQuery, staleTime: 15_000 },
      mutations: { retry: false },
    },
  });
}
