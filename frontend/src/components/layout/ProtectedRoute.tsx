import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { useCompanyRole } from '../../auth/useCompanyRole';
import { useCompanies } from '../../features/companies/useCompanies';
import { canViewPage, isPlatformPage } from '../../auth/permissions';
import AccessDenied from '../feedback/AccessDenied';
import { Loader2 } from 'lucide-react';
import PlatformTenantAccessNotice from '../feedback/PlatformTenantAccessNotice';

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** If set, restrict to specific page path for role check */
  requiredPagePath?: string;
}

export default function ProtectedRoute({ children, requiredPagePath }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();
  const { selectedCompanyId, isLoading: companiesLoading } = useCompanies();
  const { role, isLoading: roleLoading } = useCompanyRole(selectedCompanyId);
  const { pathname } = useLocation();

  // AppLayout resolves the session before it renders the Outlet, so in practice
  // this branch no longer runs. It stays as a guard for any future route that
  // uses ProtectedRoute outside the shell.
  if (isLoading) {
    return <RouteLoading />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Also enforced by AppLayout; repeated here so a future route that uses this
  // guard outside the shell is covered too. No role is exempt.
  if (user.must_change_password) {
    return <Navigate to="/auth/change-temporary-password" replace />;
  }

  // Platform routes answer to the platform flag alone, and are checked first so
  // the tenant role is never consulted for a page that has no tenant.
  if (requiredPagePath && isPlatformPage(requiredPagePath)) {
    return user.is_superuser ? <>{children}</> : <AccessDenied />;
  }

  if (user.is_superuser && !isPlatformPage(pathname)) {
    return <PlatformTenantAccessNotice />;
  }

  // Role-based page access check.
  //
  // `role` is null in three unrelated situations: the lookup is still in
  // flight, the request failed, and the membership is inactive. The previous
  // form of this check required `role` to be truthy in order to deny, so all
  // three rendered the page — the guard failed open in exactly the cases where
  // it could not establish who the user was. It now waits for an answer, and
  // refuses when the answer is "no role".
  //
  // Denial is therefore reachable on a transient network failure. That is the
  // intended direction: the API refuses the data either way, and a page that
  // renders its chrome and then fails every request is a worse answer than a
  // refusal. `requiredPagePath` is only set on /audit-logs, /company-users and
  // /settings, so AccessDenied's "back to dashboard" still leads somewhere
  // that renders.
  //
  // With no company selected there is no role to resolve and nothing
  // company-scoped to show, so that case is left to the page's own
  // "select a company" state rather than turned into a refusal.
  if (requiredPagePath) {
    if (companiesLoading || roleLoading) {
      return <RouteLoading />;
    }
    if (selectedCompanyId !== null && !canViewPage(role, requiredPagePath)) {
      return <AccessDenied />;
    }
  }

  return <>{children}</>;
}

/**
 * Sized to the content well rather than the viewport: inside the shell a
 * `min-h-screen` box would push the page taller than the window and summon a
 * scrollbar.
 */
function RouteLoading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-live="polite">
      <div className="flex flex-col items-center gap-4">
        <Loader2 aria-hidden className="w-8 h-8 text-primary animate-spin" />
        <p className="text-muted-foreground text-sm font-medium">Loading...</p>
      </div>
    </div>
  );
}
