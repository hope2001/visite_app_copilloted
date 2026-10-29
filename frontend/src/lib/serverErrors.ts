import type { FieldValues, Path, UseFormSetError } from 'react-hook-form';
import { ApiError } from '../api/errors';

/**
 * Maps a 422 response's field details onto react-hook-form fields.
 * Returns true when at least one field error was applied, so the caller can
 * skip the generic notification.
 */
export function applyServerFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  knownFields: readonly Path<T>[],
): boolean {
  if (!(error instanceof ApiError) || error.status !== 422) return false;

  let applied = false;
  for (const detail of error.details) {
    const field = detail.field as Path<T> | null;
    if (field && knownFields.includes(field)) {
      setError(field, { type: 'server', message: detail.issue }, { shouldFocus: !applied });
      applied = true;
    }
  }
  return applied;
}
