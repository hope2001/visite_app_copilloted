import { describe, expect, it } from 'vitest';
import { makeVisit } from '../test/utils';
import { countByStatus } from './visitStats';

describe('countByStatus', () => {
  it('returns zero for every status when there are no visits', () => {
    expect(countByStatus([])).toEqual({ EXPECTED: 0, CHECKED_IN: 0, CHECKED_OUT: 0, CANCELLED: 0 });
  });

  it('counts visits per status', () => {
    const visits = [
      makeVisit({ status: 'EXPECTED' }),
      makeVisit({ status: 'EXPECTED' }),
      makeVisit({ status: 'CHECKED_IN' }),
      makeVisit({ status: 'CANCELLED' }),
    ];

    expect(countByStatus(visits)).toEqual({
      EXPECTED: 2,
      CHECKED_IN: 1,
      CHECKED_OUT: 0,
      CANCELLED: 1,
    });
  });
});
