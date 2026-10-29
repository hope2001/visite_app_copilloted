import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useCurrentUser } from '../auth/AuthContext';
import { FRONT_DESK_ROLES, HOST_ROLES, hasRole } from '../auth/roles';
import { ErrorState } from '../components/ErrorState';
import { EmptyState, LoadingState } from '../components/LoadingState';
import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { StatCard } from '../components/StatCard';
import { VisitTable } from '../components/VisitTable';
import { useTodayVisits, useVisits } from '../hooks/useVisits';
import { formatLongDate, todayIsoDate } from '../lib/format';
import { countByStatus } from '../lib/visitStats';
import type { Visit } from '../types/api';

// The list endpoint caps page size at 100: more than enough for one host's visits in a day.
const MAX_HOST_VISITS_PER_DAY = 100;

export function DashboardPage() {
  const user = useCurrentUser();
  const isFrontDesk = hasRole(user.role, FRONT_DESK_ROLES);
  const canRegister = hasRole(user.role, HOST_ROLES);
  const firstName = user.full_name.trim().split(/\s+/)[0] ?? user.full_name;

  return (
    <section>
      <PageHeader
        title={`Welcome, ${firstName}`}
        description={`${formatLongDate(new Date())} · ${
          isFrontDesk ? 'All visitors for the site' : 'Visitors you registered or host'
        }`}
        actions={
          <>
            {isFrontDesk && (
              <Link className="button-link button-link--secondary" to="/today">
                Open security desk
              </Link>
            )}
            {canRegister && (
              <Link className="button-link" to="/visits/new">
                Register visitor
              </Link>
            )}
          </>
        }
      />
      {isFrontDesk ? <FrontDeskSummary /> : <HostSummary canRegister={canRegister} />}
    </section>
  );
}

function FrontDeskSummary() {
  const query = useTodayVisits('');
  return (
    <TodaySummary
      visits={query.data}
      error={query.isError ? query.error : null}
      onRetry={() => void query.refetch()}
      emptyMessage="No visitors are expected on site today."
    />
  );
}

function HostSummary({ canRegister }: { canRegister: boolean }) {
  const today = todayIsoDate();
  const query = useVisits({ date_from: today, date_to: today, size: MAX_HOST_VISITS_PER_DAY });
  return (
    <TodaySummary
      visits={query.data?.items}
      error={query.isError ? query.error : null}
      onRetry={() => void query.refetch()}
      emptyMessage="You have no visitors scheduled for today."
      emptyAction={
        canRegister ? (
          <Link className="button-link" to="/visits/new">
            Register a visitor
          </Link>
        ) : undefined
      }
    />
  );
}

interface TodaySummaryProps {
  /** `undefined` while loading. */
  visits: readonly Visit[] | undefined;
  error: unknown;
  onRetry: () => void;
  emptyMessage: string;
  emptyAction?: ReactNode;
}

function TodaySummary({ visits, error, onRetry, emptyMessage, emptyAction }: TodaySummaryProps) {
  if (error) return <ErrorState error={error} onRetry={onRetry} />;

  const counts = visits ? countByStatus(visits) : undefined;

  return (
    <>
      <div className="stat-grid">
        <StatCard
          tone="expected"
          label="Expected today"
          value={counts?.EXPECTED}
          hint="Not yet arrived"
        />
        <StatCard
          tone="on-site"
          label="Currently on site"
          value={counts?.CHECKED_IN}
          hint="Checked in, not yet out"
        />
        <StatCard
          tone="checked-out"
          label="Checked out today"
          value={counts?.CHECKED_OUT}
          hint="Visits completed"
        />
      </div>

      <Panel title="Today's visits">
        {visits === undefined ? (
          <LoadingState label="Loading today's visits…" />
        ) : visits.length === 0 ? (
          <EmptyState title="Nothing scheduled" message={emptyMessage} action={emptyAction} />
        ) : (
          <VisitTable visits={visits} emptyMessage={emptyMessage} showTimes />
        )}
      </Panel>
    </>
  );
}
