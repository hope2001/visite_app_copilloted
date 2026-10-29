import { useId } from 'react';

export type StatTone = 'expected' | 'on-site' | 'checked-out';

interface StatCardProps {
  label: string;
  /** `undefined` while loading. */
  value: number | undefined;
  hint: string;
  tone: StatTone;
}

export function StatCard({ label, value, hint, tone }: StatCardProps) {
  const labelId = useId();
  return (
    <article
      className={`stat-card stat-card--${tone}`}
      aria-labelledby={labelId}
      aria-busy={value === undefined}
    >
      <h2 id={labelId} className="stat-card__label">
        {label}
      </h2>
      <p className="stat-card__value">
        {value === undefined ? <span className="skeleton skeleton--number" /> : value}
      </p>
      <p className="stat-card__hint">{hint}</p>
    </article>
  );
}
