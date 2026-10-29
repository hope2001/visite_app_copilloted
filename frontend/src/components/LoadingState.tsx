import type { ReactNode } from 'react';

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="state state--loading" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

interface EmptyStateProps {
  message: string;
  title?: string;
  action?: ReactNode;
}

export function EmptyState({ message, title, action }: EmptyStateProps) {
  return (
    <div className="state state--empty">
      <svg className="state__icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 5h16v2H4V5Zm0 6h16v2H4v-2Zm0 6h10v2H4v-2Z" />
      </svg>
      {title && <p className="state__title">{title}</p>}
      <p>{message}</p>
      {action}
    </div>
  );
}
