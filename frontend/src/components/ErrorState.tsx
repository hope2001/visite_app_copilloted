import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, describeError } from '../api/errors';

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
}

/** Inline error for a failed query. 403/404 get dedicated wording; others offer a retry. */
export function ErrorState({ error, onRetry }: ErrorStateProps) {
  if (error instanceof ApiError && error.status === 404) {
    return (
      <ErrorBox title="Not found">
        <p>We couldn't find what you were looking for.</p>
        <Link to="/">Back to dashboard</Link>
      </ErrorBox>
    );
  }
  if (error instanceof ApiError && error.status === 403) {
    return (
      <ErrorBox title="Access denied">
        <p>You don't have permission to view this.</p>
      </ErrorBox>
    );
  }
  return (
    <ErrorBox title="Something went wrong">
      <p>{describeError(error)}</p>
      {onRetry && (
        <button type="button" className="button--secondary" onClick={onRetry}>
          Try again
        </button>
      )}
    </ErrorBox>
  );
}

function ErrorBox({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="state state--error" role="alert">
      <svg className="state__icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2 1 21h22L12 2Zm1 15h-2v-2h2v2Zm0-4h-2V9h2v4Z" />
      </svg>
      <p className="state__title">{title}</p>
      {children}
    </div>
  );
}
