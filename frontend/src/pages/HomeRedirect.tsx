import { Navigate } from 'react-router-dom';
import { useCurrentUser } from '../auth/AuthContext';
import { homePathFor } from '../auth/roles';

export function HomeRedirect() {
  const user = useCurrentUser();
  return <Navigate to={homePathFor(user.role)} replace />;
}
