import { useParams } from 'react-router-dom';
import { useCurrentUser } from '../auth/AuthContext';
import { FRONT_DESK_ROLES, HOST_ROLES, hasRole } from '../auth/roles';
import { ErrorState } from '../components/ErrorState';
import { EmptyState, LoadingState } from '../components/LoadingState';
import { StatusBadge, STATUS_LABELS } from '../components/StatusBadge';
import { VisitActions } from '../components/VisitActions';
import { VisitorPassCard } from '../components/VisitorPassCard';
import { useVisit, useVisitAudit } from '../hooks/useVisits';
import { formatDate, formatDateTime } from '../lib/format';
import type { AuditLogEntry } from '../types/api';

export function VisitDetailPage() {
  const { visitId = '' } = useParams();
  const user = useCurrentUser();
  const canSeeAudit = hasRole(user.role, FRONT_DESK_ROLES);
  const visitQuery = useVisit(visitId);
  const auditQuery = useVisitAudit(visitId, canSeeAudit && visitQuery.isSuccess);

  if (visitQuery.isPending) return <LoadingState />;
  if (visitQuery.isError) {
    return <ErrorState error={visitQuery.error} onRetry={() => void visitQuery.refetch()} />;
  }

  const visit = visitQuery.data;
  // Passes are handed out by the people who register visits, and only until arrival.
  const showPass = hasRole(user.role, HOST_ROLES) && visit.status === 'EXPECTED';

  return (
    <section>
      <div className="page-title">
        <h1>{visit.visitor.full_name}</h1>
        <StatusBadge status={visit.status} />
      </div>
      <VisitActions visit={visit} />

      <dl className="details">
        <dt>Company</dt>
        <dd>{visit.visitor.company}</dd>
        <dt>Email</dt>
        <dd>{visit.visitor.email}</dd>
        <dt>Phone</dt>
        <dd>{visit.visitor.phone ?? '—'}</dd>
        <dt>Date</dt>
        <dd>{formatDate(visit.expected_date)}</dd>
        <dt>Host</dt>
        <dd>{visit.host.full_name}</dd>
        <dt>Registered by</dt>
        <dd>{visit.registered_by.full_name}</dd>
        <dt>Purpose</dt>
        <dd>{visit.purpose}</dd>
        <dt>Checked in</dt>
        <dd>{formatDateTime(visit.checked_in_at)}</dd>
        <dt>Checked out</dt>
        <dd>{formatDateTime(visit.checked_out_at)}</dd>
        {visit.cancelled_at && (
          <>
            <dt>Cancelled</dt>
            <dd>{formatDateTime(visit.cancelled_at)}</dd>
          </>
        )}
      </dl>

      {showPass && (
        <div className="pass-panel-wrap">
          <VisitorPassCard visit={visit} />
        </div>
      )}

      {canSeeAudit && (
        <>
          <h2>History</h2>
          {auditQuery.isPending ? (
            <LoadingState />
          ) : auditQuery.isError ? (
            <ErrorState error={auditQuery.error} onRetry={() => void auditQuery.refetch()} />
          ) : (
            <AuditTrail entries={auditQuery.data} />
          )}
        </>
      )}
    </section>
  );
}

function AuditTrail({ entries }: { entries: readonly AuditLogEntry[] }) {
  if (entries.length === 0) return <EmptyState message="No history recorded." />;
  return (
    <ol className="timeline">
      {entries.map((entry) => (
        <li key={entry.id}>
          <strong>{STATUS_LABELS[entry.to_status]}</strong> by {entry.performed_by.full_name}
          <span className="muted"> — {formatDateTime(entry.occurred_at)}</span>
        </li>
      ))}
    </ol>
  );
}
