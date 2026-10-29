import { useState } from 'react';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { PageHeader } from '../components/PageHeader';
import { Pagination } from '../components/Pagination';
import { Panel } from '../components/Panel';
import { STATUS_LABELS } from '../components/StatusBadge';
import { VisitTable } from '../components/VisitTable';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { useVisits } from '../hooks/useVisits';
import { VISIT_STATUSES, type VisitStatus } from '../types/api';

const PAGE_SIZE = 20;

interface VisitListPageProps {
  title: string;
  description?: string;
  emptyMessage: string;
}

/** Paginated, filterable visit list. The API scopes results to what the user may see. */
export function VisitListPage({ title, description, emptyMessage }: VisitListPageProps) {
  const [status, setStatus] = useState<VisitStatus | ''>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const q = useDebouncedValue(search.trim());

  const query = useVisits({
    status: status || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    q: q || undefined,
    page,
    size: PAGE_SIZE,
  });

  const resetPage = <T,>(setter: (value: T) => void) => (value: T) => {
    setter(value);
    setPage(1);
  };

  return (
    <section>
      <PageHeader title={title} description={description} />
      <div className="filters filters--card">
        <label>
          Status
          <select
            value={status}
            onChange={(event) => resetPage(setStatus)(event.target.value as VisitStatus | '')}
          >
            <option value="">All</option>
            {VISIT_STATUSES.map((value) => (
              <option key={value} value={value}>
                {STATUS_LABELS[value]}
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
            onChange={(event) => resetPage(setDateFrom)(event.target.value)}
          />
        </label>
        <label>
          To
          <input
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(event) => resetPage(setDateTo)(event.target.value)}
          />
        </label>
        <label>
          Search
          <input
            type="search"
            placeholder="Visitor, email or company"
            maxLength={100}
            value={search}
            onChange={(event) => resetPage(setSearch)(event.target.value)}
          />
        </label>
      </div>

      <Panel>
        {query.isPending ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : (
          <>
            <VisitTable visits={query.data.items} emptyMessage={emptyMessage} />
            <Pagination
              page={query.data.page}
              size={query.data.size}
              total={query.data.total}
              onPageChange={setPage}
            />
          </>
        )}
      </Panel>
    </section>
  );
}
