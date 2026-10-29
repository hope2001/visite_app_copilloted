import { useCurrentUser } from '../auth/AuthContext';
import { useVisitAction, type VisitAction } from '../hooks/useVisits';
import { ACTION_LABELS, availableActions } from '../lib/visitActions';
import type { Visit } from '../types/api';

const ACTION_CLASSES: Record<VisitAction, string> = {
  checkIn: 'button--success',
  checkOut: 'button--dark',
  cancel: 'button--danger-outline',
};

interface VisitActionsProps {
  visit: Visit;
  /** Smaller buttons for table rows. */
  compact?: boolean;
}

export function VisitActions({ visit, compact = false }: VisitActionsProps) {
  const user = useCurrentUser();
  const mutation = useVisitAction();
  const actions = availableActions(visit, user);

  if (actions.length === 0) return null;

  const isPendingForThisVisit = mutation.isPending && mutation.variables?.id === visit.id;

  return (
    <div className="actions">
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          className={`${ACTION_CLASSES[action]}${compact ? ' button--sm' : ''}`}
          disabled={isPendingForThisVisit}
          onClick={() => {
            if (
              action === 'cancel' &&
              !window.confirm(`Cancel the visit of ${visit.visitor.full_name}?`)
            ) {
              return;
            }
            mutation.mutate({ id: visit.id, action });
          }}
        >
          {ACTION_LABELS[action]}
        </button>
      ))}
    </div>
  );
}
