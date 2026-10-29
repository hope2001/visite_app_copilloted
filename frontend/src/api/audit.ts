import type { AuditLogEntry, AuditLogFilters, Page } from '../types/api';
import { apiRequest } from './client';

export function listAuditLogs(filters: AuditLogFilters): Promise<Page<AuditLogEntry>> {
  return apiRequest<Page<AuditLogEntry>>('/audit-logs', { query: filters });
}
