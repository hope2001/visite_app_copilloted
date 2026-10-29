import type { Role } from '../types/api';

export const HOST_ROLES: readonly Role[] = ['EMPLOYEE', 'ADMIN'];
export const FRONT_DESK_ROLES: readonly Role[] = ['SECURITY', 'ADMIN'];
export const ADMIN_ROLES: readonly Role[] = ['ADMIN'];

export const ROLE_LABELS: Record<Role, string> = {
  EMPLOYEE: 'Employee',
  SECURITY: 'Security',
  ADMIN: 'Administrator',
};

export interface NavItem {
  to: string;
  label: string;
  roles: readonly Role[];
  /** Only active on an exact path match. */
  end?: boolean;
}

export const NAV_ITEMS: readonly NavItem[] = [
  { to: '/', label: 'Dashboard', roles: ['EMPLOYEE', 'SECURITY', 'ADMIN'], end: true },
  { to: '/visits/new', label: 'Register visitor', roles: HOST_ROLES },
  { to: '/visits/mine', label: 'My visitors', roles: ['EMPLOYEE'] },
  { to: '/today', label: 'Security desk', roles: FRONT_DESK_ROLES },
  { to: '/admin/visits', label: 'All visits', roles: ADMIN_ROLES },
  { to: '/admin/audit', label: 'Audit log', roles: ADMIN_ROLES },
];

export function homePathFor(role: Role): string {
  switch (role) {
    case 'SECURITY':
      return '/today';
    case 'ADMIN':
      return '/admin/visits';
    case 'EMPLOYEE':
      return '/visits/mine';
  }
}

export function hasRole(role: Role, allowed: readonly Role[]): boolean {
  return allowed.includes(role);
}
