import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { setAccessToken, setUnauthorizedHandler } from '../api/client';
import { server } from './server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
  setAccessToken(null);
  setUnauthorizedHandler(null);
  window.sessionStorage.clear();
});
afterAll(() => server.close());
