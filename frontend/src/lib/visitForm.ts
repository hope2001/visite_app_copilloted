import type { Path } from 'react-hook-form';
import { z } from 'zod';
import type { VisitCreateRequest } from '../types/api';
import { todayIsoDate } from './format';

const OPTIONAL_PHONE = /^$|^\+?[0-9][0-9 ()-]{5,30}$/;

/** Client-side validation mirrors the API for fast feedback; the API remains authoritative. */
export const visitFormSchema = z.object({
  visitor: z.object({
    full_name: z
      .string()
      .trim()
      .min(1, 'Visitor name is required')
      .max(120, 'Use at most 120 characters'),
    email: z.string().trim().min(1, 'Email is required').email('Enter a valid email address'),
    phone: z.string().trim().regex(OPTIONAL_PHONE, 'Enter a valid phone number'),
    company: z.string().trim().min(1, 'Company is required').max(120, 'Use at most 120 characters'),
  }),
  purpose: z.string().trim().min(1, 'Purpose is required').max(500, 'Use at most 500 characters'),
  expected_date: z
    .string()
    .min(1, 'Choose a date')
    .refine((value) => value >= todayIsoDate(), 'The visit date cannot be in the past'),
  host_id: z.string().min(1, 'Choose a host'),
});

export type VisitFormValues = z.infer<typeof visitFormSchema>;

/** Field paths shared by the form and the API's 422 `details[].field`. */
export const VISIT_FORM_FIELDS: readonly Path<VisitFormValues>[] = [
  'visitor.full_name',
  'visitor.email',
  'visitor.phone',
  'visitor.company',
  'purpose',
  'expected_date',
  'host_id',
];

export function emptyVisitForm(hostId: string): VisitFormValues {
  return {
    visitor: { full_name: '', email: '', phone: '', company: '' },
    purpose: '',
    expected_date: todayIsoDate(),
    host_id: hostId,
  };
}

export function toVisitCreateRequest(values: VisitFormValues): VisitCreateRequest {
  return {
    visitor: { ...values.visitor, phone: values.visitor.phone || null },
    purpose: values.purpose,
    expected_date: values.expected_date,
    host_id: values.host_id,
  };
}
