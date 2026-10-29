import { Link } from 'react-router-dom';
import { formatDate, formatTime } from '../lib/format';
import type { Visit } from '../types/api';
import { EmptyState } from './LoadingState';
import { StatusBadge } from './StatusBadge';
import { VisitActions } from './VisitActions';

interface VisitTableProps {
  visits: readonly Visit[];
  emptyMessage: string;
  showTimes?: boolean;
}

export function VisitTable({ visits, emptyMessage, showTimes = false }: VisitTableProps) {
  if (visits.length === 0) return <EmptyState message={emptyMessage} />;

  return (
    <div className="table-wrap">
    <table className="table">
      <thead>
        <tr>
          <th scope="col">Visitor</th>
          <th scope="col">Date</th>
          <th scope="col">Host</th>
          <th scope="col">Purpose</th>
          <th scope="col">Status</th>
          {showTimes && <th scope="col">In / Out</th>}
          <th scope="col">
            <span className="visually-hidden">Actions</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {visits.map((visit) => (
          <tr key={visit.id}>
            <td>
              <Link className="table__primary" to={`/visits/${visit.id}`}>
                {visit.visitor.full_name}
              </Link>
              <div className="muted">{visit.visitor.company}</div>
            </td>
            <td className="nowrap">{formatDate(visit.expected_date)}</td>
            <td>{visit.host.full_name}</td>
            <td className="truncate" title={visit.purpose}>
              {visit.purpose}
            </td>
            <td>
              <StatusBadge status={visit.status} />
            </td>
            {showTimes && (
              <td className="nowrap">
                {formatTime(visit.checked_in_at)} / {formatTime(visit.checked_out_at)}
              </td>
            )}
            <td>
              <VisitActions visit={visit} compact />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  );
}
