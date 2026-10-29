import type {
  AuditLogEntry,
  Page,
  Uuid,
  Visit,
  VisitCreateRequest,
  VisitFilters,
  VisitorPass,
} from '../types/api';
import { apiRequest } from './client';

const segment = (id: Uuid) => encodeURIComponent(id);

export const visitsApi = {
  list: (filters: VisitFilters) => apiRequest<Page<Visit>>('/visits', { query: filters }),
  listToday: (q?: string) => apiRequest<Visit[]>('/visits/today', { query: { q } }),
  get: (id: Uuid) => apiRequest<Visit>(`/visits/${segment(id)}`),
  register: (data: VisitCreateRequest) =>
    apiRequest<Visit>('/visits', { method: 'POST', json: data }),
  checkIn: (id: Uuid) => apiRequest<Visit>(`/visits/${segment(id)}/check-in`, { method: 'POST' }),
  checkOut: (id: Uuid) => apiRequest<Visit>(`/visits/${segment(id)}/check-out`, { method: 'POST' }),
  cancel: (id: Uuid) => apiRequest<Visit>(`/visits/${segment(id)}/cancel`, { method: 'POST' }),
  auditTrail: (id: Uuid) => apiRequest<AuditLogEntry[]>(`/visits/${segment(id)}/audit`),
  pass: (id: Uuid) => apiRequest<VisitorPass>(`/visits/${segment(id)}/pass`),
  /** POST keeps the scanned code out of URLs and access logs. */
  lookupByPass: (code: string) =>
    apiRequest<Visit>('/visits/pass-lookup', { method: 'POST', json: { code } }),
};
