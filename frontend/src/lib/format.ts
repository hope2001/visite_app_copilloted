const dateFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' });
const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});
const timeFormatter = new Intl.DateTimeFormat(undefined, { timeStyle: 'short' });
const longDateFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'full' });

export function formatLongDate(date: Date): string {
  return longDateFormatter.format(date);
}

/** Formats a calendar date (YYYY-MM-DD) without shifting it across time zones. */
export function formatDate(isoDate: string): string {
  return dateFormatter.format(new Date(`${isoDate}T00:00:00`));
}

export function formatDateTime(isoDateTime: string | null): string {
  return isoDateTime ? dateTimeFormatter.format(new Date(isoDateTime)) : '—';
}

export function formatTime(isoDateTime: string | null): string {
  return isoDateTime ? timeFormatter.format(new Date(isoDateTime)) : '—';
}

/** Today's date in the browser's time zone, as YYYY-MM-DD. */
export function todayIsoDate(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}
