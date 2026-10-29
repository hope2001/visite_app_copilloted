import { useState } from 'react';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { PassScanner } from '../components/PassScanner';
import { SearchField } from '../components/SearchField';
import { STATUS_LABELS } from '../components/StatusBadge';
import { VisitTable } from '../components/VisitTable';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { useTodayVisits } from '../hooks/useVisits';
import { countByStatus } from '../lib/visitStats';
import { VISIT_STATUSES, type VisitStatus } from '../types/api';

type StatusFilter = VisitStatus | 'ALL';

/** Front-desk view of today's visitors: search, filter by status, check in and out. */
export function TodayVisitsPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');
  const q = useDebouncedValue(search.trim());
  const query = useTodayVisits(q);

  const visits = query.data ?? [];
  const counts = countByStatus(visits);
  const shown =
    statusFilter === 'ALL' ? visits : visits.filter((visit) => visit.status === statusFilter);

  const filters: { value: StatusFilter; label: string; count: number }[] = [
    { value: 'ALL', label: 'All', count: visits.length },
    ...VISIT_STATUSES.map((status) => ({
      value: status,
      label: STATUS_LABELS[status],
      count: counts[status],
    })),
  ];

  return (
    <section>
      <PageHeader
        title="Security desk"
        description="Today's visitors. The list refreshes automatically every 30 seconds."
      />

      <PassScanner />

      <div className="toolbar">
        <SearchField
          id="security-search"
          label="Search visitors"
          placeholder="Search by visitor, email or company"
          value={search}
          onChange={setSearch}
        />
        <div className="chip-group" role="group" aria-label="Filter by status">
          {filters.map((filter) => (
            <button
              key={filter.value}
              type="button"
              className="chip"
              aria-pressed={statusFilter === filter.value}
              onClick={() => setStatusFilter(filter.value)}
            >
              {filter.label}
              <span className="chip__count">{filter.count}</span>
            </button>
          ))}
        </div>
      </div>

      <Panel>
        {query.isPending ? (
          <LoadingState label="Loading today's visitors…" />
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : (
          <VisitTable
            visits={shown}
            emptyMessage={
              q || statusFilter !== 'ALL'
                ? 'No visitors match your search or filter.'
                : 'No visitors are expected today.'
            }
            showTimes
          />
        )}
      </Panel>
    </section>
  );
}
