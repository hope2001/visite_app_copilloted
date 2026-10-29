import { createBrowserRouter, Outlet, RouterProvider, type RouteObject } from 'react-router-dom';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { ADMIN_ROLES, FRONT_DESK_ROLES, HOST_ROLES } from './auth/roles';
import { Layout } from './components/Layout';
import { AuditLogPage } from './pages/AuditLogPage';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { RegisterVisitPage } from './pages/RegisterVisitPage';
import { RouteErrorPage } from './pages/RouteErrorPage';
import { TodayVisitsPage } from './pages/TodayVisitsPage';
import { VisitDetailPage } from './pages/VisitDetailPage';
import { VisitListPage } from './pages/VisitListPage';

export const routes: RouteObject[] = [
  {
    errorElement: <RouteErrorPage />,
    element: <Outlet />,
    children: [
      { path: '/login', element: <LoginPage /> },
      {
        path: '/',
        element: (
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        ),
        children: [
          { index: true, element: <DashboardPage /> },
          {
            path: 'visits/new',
            element: (
              <ProtectedRoute roles={HOST_ROLES}>
                <RegisterVisitPage />
              </ProtectedRoute>
            ),
          },
          {
            path: 'visits/mine',
            element: (
              <ProtectedRoute roles={HOST_ROLES}>
                <VisitListPage
                  title="My visitors"
                  description="Visitors you registered or are hosting."
                  emptyMessage="You have no visitors matching these filters."
                />
              </ProtectedRoute>
            ),
          },
          { path: 'visits/:visitId', element: <VisitDetailPage /> },
          {
            path: 'today',
            element: (
              <ProtectedRoute roles={FRONT_DESK_ROLES}>
                <TodayVisitsPage />
              </ProtectedRoute>
            ),
          },
          {
            path: 'admin/visits',
            element: (
              <ProtectedRoute roles={ADMIN_ROLES}>
                <VisitListPage
                  title="All visits"
                  description="Every visit across the site, with full history."
                  emptyMessage="No visits match these filters."
                />
              </ProtectedRoute>
            ),
          },
          {
            path: 'admin/audit',
            element: (
              <ProtectedRoute roles={ADMIN_ROLES}>
                <AuditLogPage />
              </ProtectedRoute>
            ),
          },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
];

const router = createBrowserRouter(routes);

export function App() {
  return <RouterProvider router={router} />;
}
