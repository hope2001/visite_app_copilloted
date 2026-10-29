import { useRef, useState, type FormEvent } from 'react';
import { describeError } from '../api/errors';
import { usePassLookup, useVisit } from '../hooks/useVisits';
import { formatDate } from '../lib/format';
import type { Uuid } from '../types/api';
import { ErrorState } from './ErrorState';
import { LoadingState } from './LoadingState';
import { Panel } from './Panel';
import { StatusBadge } from './StatusBadge';
import { VisitActions } from './VisitActions';

/** Matches the server limit; longer input is never a valid pass. */
const MAX_PASS_CODE_LENGTH = 100;

/**
 * Front-desk pass scanning. Works with keyboard-wedge QR scanners (they type the
 * code and press Enter) and with pasted codes. Scanning only identifies the
 * visit; checking in stays an explicit action with the normal rules.
 */
export function PassScanner() {
  const [code, setCode] = useState('');
  const [scannedId, setScannedId] = useState<Uuid | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const lookup = usePassLookup();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const value = code.trim();
    if (!value) return;
    setScannedId(null);
    lookup.mutate(value, {
      onSuccess: (visit) => setScannedId(visit.id),
      onSettled: () => {
        // Ready for the next scan.
        setCode('');
        inputRef.current?.focus();
      },
    });
  };

  return (
    <div className="pass-panel-wrap">
      <Panel title="Scan visitor pass">
        <div className="pass-panel">
          <form className="pass-scanner" onSubmit={submit} noValidate>
            <div className="field pass-scanner__field">
              <label htmlFor="pass-code">Pass code</label>
              <input
                id="pass-code"
                ref={inputRef}
                value={code}
                onChange={(event) => setCode(event.target.value)}
                maxLength={MAX_PASS_CODE_LENGTH}
                placeholder="Scan the QR code or paste the pass code"
                autoComplete="off"
                autoCapitalize="characters"
                spellCheck={false}
              />
            </div>
            <button type="submit" disabled={lookup.isPending || !code.trim()}>
              Find visit
            </button>
          </form>

          {lookup.isError && (
            <p className="form-error" role="alert">
              {describeError(lookup.error)}
            </p>
          )}
          {scannedId && <ScannedVisit id={scannedId} />}
        </div>
      </Panel>
    </div>
  );
}

function ScannedVisit({ id }: { id: Uuid }) {
  const query = useVisit(id);

  if (query.isPending) return <LoadingState />;
  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  }

  const visit = query.data;
  return (
    <div className="scanned-visit" aria-live="polite">
      <div className="page-title">
        <h3>{visit.visitor.full_name}</h3>
        <StatusBadge status={visit.status} />
      </div>
      <dl className="details">
        <dt>Company</dt>
        <dd>{visit.visitor.company}</dd>
        <dt>Date</dt>
        <dd>{formatDate(visit.expected_date)}</dd>
        <dt>Host</dt>
        <dd>{visit.host.full_name}</dd>
        <dt>Purpose</dt>
        <dd>{visit.purpose}</dd>
      </dl>
      <p className="muted">Verify the visitor&apos;s photo ID before checking in.</p>
      <VisitActions visit={visit} />
    </div>
  );
}
