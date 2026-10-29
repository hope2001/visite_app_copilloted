import { zodResolver } from '@hookform/resolvers/zod';
import type { ReactElement } from 'react';
import { useForm, type FieldError } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { describeError } from '../api/errors';
import { applyServerFieldErrors } from '../lib/serverErrors';
import { todayIsoDate } from '../lib/format';
import {
  VISIT_FORM_FIELDS,
  emptyVisitForm,
  visitFormSchema,
  type VisitFormValues,
} from '../lib/visitForm';
import type { UserSummary } from '../types/api';

interface VisitFormProps {
  hosts: readonly UserSummary[];
  defaultHostId: string;
  onSubmit: (values: VisitFormValues) => Promise<unknown>;
}

export function VisitForm({ hosts, defaultHostId, onSubmit }: VisitFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<VisitFormValues>({
    resolver: zodResolver(visitFormSchema),
    defaultValues: emptyVisitForm(defaultHostId),
  });

  const submit = handleSubmit(async (values) => {
    try {
      await onSubmit(values);
    } catch (error) {
      if (!applyServerFieldErrors(error, setError, VISIT_FORM_FIELDS)) {
        setError('root.server', { type: 'server', message: describeError(error) });
      }
    }
  });

  return (
    <form className="form form--wide" onSubmit={submit} noValidate>
      {errors.root?.server && (
        <p className="form-error" role="alert">
          {errors.root.server.message}
        </p>
      )}

      <fieldset className="form-section">
        <legend>Visitor</legend>
        <p className="form-section__hint">Who is coming? Details are shown to the front desk.</p>
        <div className="form-grid">
          <Field id="visitor-name" label="Full name" error={errors.visitor?.full_name}>
            <input id="visitor-name" autoComplete="off" {...register('visitor.full_name')} />
          </Field>
          <Field id="visitor-company" label="Company" error={errors.visitor?.company}>
            <input id="visitor-company" autoComplete="off" {...register('visitor.company')} />
          </Field>
          <Field id="visitor-email" label="Email" error={errors.visitor?.email}>
            <input
              id="visitor-email"
              type="email"
              autoComplete="off"
              {...register('visitor.email')}
            />
          </Field>
          <Field id="visitor-phone" label="Phone (optional)" error={errors.visitor?.phone}>
            <input id="visitor-phone" type="tel" autoComplete="off" {...register('visitor.phone')} />
          </Field>
        </div>
      </fieldset>

      <fieldset className="form-section">
        <legend>Visit</legend>
        <p className="form-section__hint">When, who they are meeting, and why.</p>
        <div className="form-grid">
          <Field id="visit-date" label="Date" error={errors.expected_date}>
            <input id="visit-date" type="date" min={todayIsoDate()} {...register('expected_date')} />
          </Field>
          <Field id="visit-host" label="Host" error={errors.host_id}>
            <select id="visit-host" {...register('host_id')}>
              <option value="">Select a host…</option>
              {hosts.map((host) => (
                <option key={host.id} value={host.id}>
                  {host.full_name}
                </option>
              ))}
            </select>
          </Field>
          <Field id="visit-purpose" label="Purpose" error={errors.purpose} fullWidth>
            <textarea id="visit-purpose" rows={3} {...register('purpose')} />
          </Field>
        </div>
      </fieldset>

      <div className="form-actions">
        <Link className="button-link button-link--secondary" to="/">
          Cancel
        </Link>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Registering…' : 'Register visit'}
        </button>
      </div>
    </form>
  );
}

interface FieldProps {
  id: string;
  label: string;
  error: FieldError | undefined;
  children: ReactElement;
  fullWidth?: boolean;
}

function Field({ id, label, error, children, fullWidth = false }: FieldProps) {
  const className = ['field', fullWidth && 'field--full', error && 'field--invalid']
    .filter(Boolean)
    .join(' ');
  return (
    <div className={className}>
      <label htmlFor={id}>{label}</label>
      {children}
      {error?.message && (
        <span className="field-error" role="alert">
          {error.message}
        </span>
      )}
    </div>
  );
}
