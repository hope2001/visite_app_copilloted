import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { listAuditLogs } from '../api/audit';
import { listHosts } from '../api/users';
import type { AuditLogFilters } from '../types/api';

export function useHosts() {
  return useQuery({ queryKey: ['users', 'hosts'], queryFn: listHosts, staleTime: 5 * 60_000 });
}

export function useAuditLogs(filters: AuditLogFilters) {
  return useQuery({
    queryKey: ['audit-logs', filters],
    queryFn: () => listAuditLogs(filters),
    placeholderData: keepPreviousData,
  });
}
