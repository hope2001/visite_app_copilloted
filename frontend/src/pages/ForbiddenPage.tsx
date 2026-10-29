import { Link } from 'react-router-dom';

export function ForbiddenPage() {
  return (
    <div className="page page--centered">
      <h1>Access denied</h1>
      <p>Your role does not allow access to this page.</p>
      <Link to="/">Back to home</Link>
    </div>
  );
}
