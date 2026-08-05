import { Navigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { useCompanyRole } from '../../auth/useCompanyRole';
import { useCompanies } from '../../features/companies/useCompanies';
import { canViewPage, isPlatformPage } from '../../auth/permissions';
import AccessDenied from '../feedback/AccessDenied';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** If set, restrict to specific page path for role check */
  requiredPagePath?: string;
}

export default function ProtectedRoute({ children, requiredPagePath }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();
  const { selectedCompanyId } = useCompanies();
  const { role, isLoading: roleLoading } = useCompanyRole(selectedCompanyId);

  // AppLayout resolves the session before it renders the Outlet, so in practice
  // this branch no longer runs. It stays as a guard for any future route that
  // uses ProtectedRoute outside the shell — but it is sized to the content well
  // rather than the viewport, because inside the shell a `min-h-screen` box
  // would push the page taller than the window and summon a scrollbar.
  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-live="polite">
        <div className="flex flex-col items-center gap-4">
          <Loader2 aria-hidden className="w-8 h-8 text-primary animate-spin" />
          <p className="text-muted-foreground text-sm font-medium">Loading...</p>
        </div>
      </div>
    );
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

  // Role-based page access check
  if (requiredPagePath && !roleLoading && role && !canViewPage(role, requiredPagePath)) {
    return <AccessDenied />;
  }

  return <>{children}</>;
}
