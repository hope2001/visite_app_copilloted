import type { ReactNode } from 'react';

interface PanelProps {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}

/** White card used to group page content, with an optional titled header. */
export function Panel({ title, actions, children }: PanelProps) {
  return (
    <section className="panel">
      {(title || actions) && (
        <div className="panel__header">
          {title && <h2 className="panel__title">{title}</h2>}
          {actions && <div className="panel__actions">{actions}</div>}
        </div>
      )}
      <div className="panel__body">{children}</div>
    </section>
  );
}
