import type { Visit, VisitStatus } from '../types/api';

export type StatusCounts = Record<VisitStatus, number>;

export function countByStatus(visits: readonly Visit[]): StatusCounts {
  const counts: StatusCounts = { EXPECTED: 0, CHECKED_IN: 0, CHECKED_OUT: 0, CANCELLED: 0 };
  for (const visit of visits) counts[visit.status] += 1;
  return counts;
}
