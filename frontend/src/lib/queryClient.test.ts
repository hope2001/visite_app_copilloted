import { describe, expect, it } from 'vitest';
import { ApiError, NetworkError } from '../api/errors';
import { shouldRetryQuery } from './queryClient';

describe('shouldRetryQuery', () => {
  it.each([
    ['network error', new NetworkError(), true],
    ['server error', new ApiError(503, 'SERVICE_UNAVAILABLE', 'down'), true],
    ['not found', new ApiError(404, 'NOT_FOUND', 'missing'), false],
    ['forbidden', new ApiError(403, 'FORBIDDEN', 'no'), false],
    ['unknown error', new Error('boom'), false],
  ])('%s → %s', (_label, error, expected) => {
    expect(shouldRetryQuery(0, error)).toBe(expected);
  });

  it('stops after two retries', () => {
    expect(shouldRetryQuery(2, new NetworkError())).toBe(false);
  });
});
