import { useNavigate } from 'react-router-dom';
import { useCurrentUser } from '../auth/AuthContext';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { PageHeader } from '../components/PageHeader';
import { useNotify } from '../components/notifications';
import { VisitForm } from '../components/VisitForm';
import { useHosts } from '../hooks/useReferenceData';
import { useRegisterVisit } from '../hooks/useVisits';
import { toVisitCreateRequest, type VisitFormValues } from '../lib/visitForm';

export function RegisterVisitPage() {
  const user = useCurrentUser();
  const hosts = useHosts();
  const registerVisit = useRegisterVisit();
  const notify = useNotify();
  const navigate = useNavigate();

  const handleSubmit = async (values: VisitFormValues) => {
    const visit = await registerVisit.mutateAsync(toVisitCreateRequest(values));
    notify(`Visit of ${visit.visitor.full_name} registered.`, 'success');
    navigate(`/visits/${visit.id}`);
  };

  return (
    <section>
      <PageHeader
        title="Register a visitor"
        description="Pre-register a guest so the front desk can welcome them on arrival."
      />
      {hosts.isPending ? (
        <LoadingState label="Loading hosts…" />
      ) : hosts.isError ? (
        <ErrorState error={hosts.error} onRetry={() => void hosts.refetch()} />
      ) : (
        <VisitForm hosts={hosts.data} defaultHostId={user.id} onSubmit={handleSubmit} />
      )}
    </section>
  );
}
