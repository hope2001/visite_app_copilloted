import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { describeError } from '../api/errors';
import { visitsApi } from '../api/visits';
import { useNotify } from '../components/notifications';
import type { Uuid, Visit, VisitCreateRequest, VisitFilters } from '../types/api';

export const visitKeys = {
  all: ['visits'] as const,
  list: (filters: VisitFilters) => [...visitKeys.all, 'list', filters] as const,
  today: (q: string) => [...visitKeys.all, 'today', q] as const,
  detail: (id: Uuid) => [...visitKeys.all, 'detail', id] as const,
  audit: (id: Uuid) => [...visitKeys.all, 'audit', id] as const,
  pass: (id: Uuid) => [...visitKeys.all, 'pass', id] as const,
};

export function useVisits(filters: VisitFilters) {
  return useQuery({
    queryKey: visitKeys.list(filters),
    queryFn: () => visitsApi.list(filters),
    placeholderData: keepPreviousData,
  });
}

const TODAY_REFRESH_MS = 30_000;

export function useTodayVisits(q: string) {
  return useQuery({
    queryKey: visitKeys.today(q),
    queryFn: () => visitsApi.listToday(q),
    placeholderData: keepPreviousData,
    refetchInterval: TODAY_REFRESH_MS,
  });
}

export function useVisit(id: Uuid) {
  return useQuery({ queryKey: visitKeys.detail(id), queryFn: () => visitsApi.get(id) });
}

export function useVisitAudit(id: Uuid, enabled: boolean) {
  return useQuery({
    queryKey: visitKeys.audit(id),
    queryFn: () => visitsApi.auditTrail(id),
    enabled,
  });
}

export function useVisitorPass(id: Uuid, enabled: boolean) {
  return useQuery({
    queryKey: visitKeys.pass(id),
    queryFn: () => visitsApi.pass(id),
    enabled,
    // The pass of a visit never changes.
    staleTime: Infinity,
  });
}

/** Front desk: resolves a scanned pass to its visit. Does not check the visitor in. */
export function usePassLookup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => visitsApi.lookupByPass(code),
    onSuccess: (visit) => queryClient.setQueryData(visitKeys.detail(visit.id), visit),
  });
}

export function useRegisterVisit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: VisitCreateRequest) => visitsApi.register(data),
    onSuccess: (visit) => {
      queryClient.setQueryData(visitKeys.detail(visit.id), visit);
      return queryClient.invalidateQueries({ queryKey: visitKeys.all });
    },
  });
}

export type VisitAction = 'checkIn' | 'checkOut' | 'cancel';

const ACTION_SUCCESS: Record<VisitAction, (visit: Visit) => string> = {
  checkIn: (visit) => `${visit.visitor.full_name} checked in.`,
  checkOut: (visit) => `${visit.visitor.full_name} checked out.`,
  cancel: (visit) => `Visit of ${visit.visitor.full_name} cancelled.`,
};

/**
 * Status-changing actions. On 409 (someone else changed the visit first) the
 * refetch makes the UI reflect the real state.
 */
export function useVisitAction() {
  const queryClient = useQueryClient();
  const notify = useNotify();

  return useMutation({
    mutationFn: ({ id, action }: { id: Uuid; action: VisitAction }) => visitsApi[action](id),
    onSuccess: (visit, { action }) => {
      queryClient.setQueryData(visitKeys.detail(visit.id), visit);
      notify(ACTION_SUCCESS[action](visit), 'success');
    },
    onError: (error) => {
      notify(describeError(error), 'error');
    },
    // Refresh after success and after failures (e.g. 409): either way the cache may be stale.
    onSettled: () => queryClient.invalidateQueries({ queryKey: visitKeys.all }),
  });
}
