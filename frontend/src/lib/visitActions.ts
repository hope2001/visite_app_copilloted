import { FRONT_DESK_ROLES, hasRole } from '../auth/roles';
import type { CurrentUser, Visit } from '../types/api';
import type { VisitAction } from '../hooks/useVisits';

/**
 * UI hints mirroring the backend rules. The API remains the source of truth:
 * it re-checks role, ownership, status and date on every call.
 */
export function availableActions(visit: Visit, user: CurrentUser): VisitAction[] {
  const actions: VisitAction[] = [];
  const isFrontDesk = hasRole(user.role, FRONT_DESK_ROLES);

  if (visit.status === 'EXPECTED' && isFrontDesk) actions.push('checkIn');
  if (visit.status === 'CHECKED_IN' && isFrontDesk) actions.push('checkOut');
  if (
    visit.status === 'EXPECTED' &&
    (user.role === 'ADMIN' || visit.registered_by.id === user.id)
  ) {
    actions.push('cancel');
  }
  return actions;
}

export const ACTION_LABELS: Record<VisitAction, string> = {
  checkIn: 'Check in',
  checkOut: 'Check out',
  cancel: 'Cancel visit',
};
