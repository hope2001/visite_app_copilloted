import type { CurrentUser, TokenResponse } from '../types/api';
import { apiRequest } from './client';

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    form: { username: email, password },
    skipUnauthorizedHandler: true,
  });
}

export function fetchCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/auth/me');
}
