import { describe, expect, it } from 'vitest';
import { employee, makeVisit, security } from '../test/utils';
import type { CurrentUser } from '../types/api';
import { availableActions } from './visitActions';

const admin: CurrentUser = { ...security, id: 'admin-id', role: 'ADMIN' };
const otherEmployee: CurrentUser = { ...employee, id: 'other-id' };

describe('availableActions', () => {
  it('lets the front desk check in an expected visit', () => {
    expect(availableActions(makeVisit(), security)).toEqual(['checkIn']);
  });

  it('lets the front desk check out a visitor on site', () => {
    expect(availableActions(makeVisit({ status: 'CHECKED_IN' }), security)).toEqual(['checkOut']);
  });

  it('lets only the registrant or an admin cancel', () => {
    expect(availableActions(makeVisit(), employee)).toEqual(['cancel']);
    expect(availableActions(makeVisit(), otherEmployee)).toEqual([]);
    expect(availableActions(makeVisit(), admin)).toEqual(['checkIn', 'cancel']);
  });

  it('offers nothing for finished visits', () => {
    expect(availableActions(makeVisit({ status: 'CHECKED_OUT' }), admin)).toEqual([]);
    expect(availableActions(makeVisit({ status: 'CANCELLED' }), admin)).toEqual([]);
  });
});
