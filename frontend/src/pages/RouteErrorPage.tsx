import { useEffect } from 'react';
import { Link, useRouteError } from 'react-router-dom';

/** Router-level fallback for errors thrown while rendering a page. */
export function RouteErrorPage() {
  const error = useRouteError();

  useEffect(() => {
    console.error('Route render error', error);
  }, [error]);

  return (
    <div className="page page--centered" role="alert">
      <h1>Something went wrong</h1>
      <p>This page failed to load. Try again or go back to the home page.</p>
      <div className="actions">
        <button type="button" onClick={() => window.location.reload()}>
          Reload
        </button>
        <Link to="/">Home</Link>
      </div>
    </div>
  );
}
