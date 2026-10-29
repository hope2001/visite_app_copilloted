export type Uuid = string;
export type IsoDate = string; // YYYY-MM-DD
export type IsoDateTime = string;

export type Role = 'EMPLOYEE' | 'SECURITY' | 'ADMIN';
export type VisitStatus = 'EXPECTED' | 'CHECKED_IN' | 'CHECKED_OUT' | 'CANCELLED';
export type AuditAction = 'VISIT_CREATED' | 'CHECKED_IN' | 'CHECKED_OUT' | 'CANCELLED';

export const VISIT_STATUSES: readonly VisitStatus[] = [
  'EXPECTED',
  'CHECKED_IN',
  'CHECKED_OUT',
  'CANCELLED',
];
export const AUDIT_ACTIONS: readonly AuditAction[] = [
  'VISIT_CREATED',
  'CHECKED_IN',
  'CHECKED_OUT',
  'CANCELLED',
];

export interface UserSummary {
  id: Uuid;
  full_name: string;
  email: string;
}

export interface CurrentUser extends UserSummary {
  role: Role;
}

export interface Visitor {
  id: Uuid;
  full_name: string;
  email: string;
  phone: string | null;
  company: string;
}

export interface Visit {
  id: Uuid;
  visitor: Visitor;
  host: UserSummary;
  registered_by: UserSummary;
  purpose: string;
  expected_date: IsoDate;
  status: VisitStatus;
  checked_in_at: IsoDateTime | null;
  checked_out_at: IsoDateTime | null;
  cancelled_at: IsoDateTime | null;
  created_at: IsoDateTime;
}

/** QR visitor pass. `code` is the QR content and contains no personal data. */
export interface VisitorPass {
  visit_id: Uuid;
  code: string;
}

export interface AuditLogEntry {
  id: Uuid;
  visit_id: Uuid;
  action: AuditAction;
  from_status: VisitStatus | null;
  to_status: VisitStatus;
  performed_by: UserSummary;
  occurred_at: IsoDateTime;
  note: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface VisitCreateRequest {
  visitor: {
    full_name: string;
    email: string;
    phone: string | null;
    company: string;
  };
  purpose: string;
  expected_date: IsoDate;
  host_id: Uuid | null;
}

export interface PageQuery {
  page?: number;
  size?: number;
}

export interface VisitFilters extends PageQuery {
  status?: VisitStatus;
  date_from?: IsoDate;
  date_to?: IsoDate;
  host_id?: Uuid;
  q?: string;
}

export interface AuditLogFilters extends PageQuery {
  visit_id?: Uuid;
  action?: AuditAction;
  date_from?: IsoDate;
  date_to?: IsoDate;
}

export type ErrorCode =
  | 'AUTH_INVALID_CREDENTIALS'
  | 'AUTH_TOKEN_INVALID'
  | 'AUTH_TOKEN_EXPIRED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'VISIT_NOT_FOUND'
  | 'HOST_NOT_FOUND'
  | 'VISIT_INVALID_TRANSITION'
  | 'VISIT_NOT_DUE_TODAY'
  | 'VISITOR_PASS_INVALID'
  | 'VALIDATION_ERROR'
  | 'CONFLICT'
  | 'METHOD_NOT_ALLOWED'
  | 'RATE_LIMITED'
  | 'SERVICE_UNAVAILABLE'
  | 'INTERNAL_ERROR';

export interface ErrorDetail {
  field: string | null;
  issue: string;
}

export interface ErrorEnvelope {
  error: {
    code: ErrorCode;
    message: string;
    details: ErrorDetail[];
    request_id: string | null;
  };
}
