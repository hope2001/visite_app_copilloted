import { QRCodeSVG } from 'qrcode.react';
import { useVisitorPass } from '../hooks/useVisits';
import { formatDate } from '../lib/format';
import type { Visit } from '../types/api';
import { ErrorState } from './ErrorState';
import { LoadingState } from './LoadingState';
import { Panel } from './Panel';

/**
 * Printable QR visitor pass. The QR only carries the signed pass code (no
 * personal data); the security desk scans it to find the visit and check in.
 */
export function VisitorPassCard({ visit }: { visit: Visit }) {
  const passQuery = useVisitorPass(visit.id, true);

  return (
    <Panel
      title="Visitor pass"
      actions={
        passQuery.isSuccess && (
          <button
            type="button"
            className="button--secondary no-print"
            onClick={() => window.print()}
          >
            Print pass
          </button>
        )
      }
    >
      {passQuery.isPending ? (
        <LoadingState label="Generating visitor pass…" />
      ) : passQuery.isError ? (
        <ErrorState error={passQuery.error} onRetry={() => void passQuery.refetch()} />
      ) : (
        <div className="visitor-pass">
          <QRCodeSVG
            className="visitor-pass__qr"
            value={passQuery.data.code}
            size={192}
            level="M"
            marginSize={2}
            role="img"
            aria-label={`QR visitor pass for ${visit.visitor.full_name}`}
          />
          <div className="visitor-pass__info">
            <p className="visitor-pass__name">{visit.visitor.full_name}</p>
            <p>{visit.visitor.company}</p>
            <p>
              {formatDate(visit.expected_date)} · Host: {visit.host.full_name}
            </p>
            <p className="muted">
              Show this pass at the security desk on arrival, together with photo ID.
            </p>
            <p className="visitor-pass__code">
              <span className="muted">Pass code</span>
              <code>{passQuery.data.code}</code>
            </p>
          </div>
        </div>
      )}
    </Panel>
  );
}
