import type { VisitStatus } from '../types/api';

export const STATUS_LABELS: Record<VisitStatus, string> = {
  EXPECTED: 'Expected',
  CHECKED_IN: 'On site',
  CHECKED_OUT: 'Checked out',
  CANCELLED: 'Cancelled',
};

export function StatusBadge({ status }: { status: VisitStatus }) {
  return (
    <span className={`badge badge--${status.toLowerCase().replace('_', '-')}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}
