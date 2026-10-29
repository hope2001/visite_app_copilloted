import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ErrorState } from '../components/ErrorState';
import { EmptyState, LoadingState } from '../components/LoadingState';
import { Pagination } from '../components/Pagination';
import { STATUS_LABELS } from '../components/StatusBadge';
import { useAuditLogs } from '../hooks/useReferenceData';
import { formatDateTime } from '../lib/format';
import { AUDIT_ACTIONS, type AuditAction } from '../types/api';

const PAGE_SIZE = 50;

const ACTION_LABELS: Record<AuditAction, string> = {
  VISIT_CREATED: 'Registered',
  CHECKED_IN: 'Checked in',
  CHECKED_OUT: 'Checked out',
  CANCELLED: 'Cancelled',
};

export function AuditLogPage() {
  const [action, setAction] = useState<AuditAction | ''>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);

  const query = useAuditLogs({
    action: action || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page,
    size: PAGE_SIZE,
  });

  return (
    <section>
      <h1>Audit log</h1>
      <div className="filters">
        <label>
          Action
          <select
            value={action}
            onChange={(event) => {
              setAction(event.target.value as AuditAction | '');
              setPage(1);
            }}
          >
            <option value="">All</option>
            {AUDIT_ACTIONS.map((value) => (
              <option key={value} value={value}>
                {ACTION_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
        <label>
          From
          <input
            type="date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(event) => {
              setDateFrom(event.target.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          To
          <input
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(event) => {
              setDateTo(event.target.value);
              setPage(1);
            }}
          />
        </label>
      </div>

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : query.data.items.length === 0 ? (
        <EmptyState message="No audit entries match these filters." />
      ) : (
        <>
          <table className="table">
            <thead>
              <tr>
                <th scope="col">When</th>
                <th scope="col">Action</th>
                <th scope="col">Status change</th>
                <th scope="col">By</th>
                <th scope="col">Visit</th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((entry) => (
                <tr key={entry.id}>
                  <td>{formatDateTime(entry.occurred_at)}</td>
                  <td>{ACTION_LABELS[entry.action]}</td>
                  <td>
                    {entry.from_status ? `${STATUS_LABELS[entry.from_status]} → ` : ''}
                    {STATUS_LABELS[entry.to_status]}
                  </td>
                  <td>{entry.performed_by.full_name}</td>
                  <td>
                    <Link to={`/visits/${entry.visit_id}`}>View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination
            page={query.data.page}
            size={query.data.size}
            total={query.data.total}
            onPageChange={setPage}
          />
        </>
      )}
    </section>
  );
}
