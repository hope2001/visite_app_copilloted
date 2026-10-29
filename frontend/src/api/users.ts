import type { UserSummary } from '../types/api';
import { apiRequest } from './client';

export function listHosts(): Promise<UserSummary[]> {
  return apiRequest<UserSummary[]>('/users/hosts');
}
