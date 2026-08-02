import { Navigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { useCompanyRole } from '../../auth/useCompanyRole';
import { useCompanies } from '../../features/companies/useCompanies';
import { canViewPage } from '../../auth/permissions';
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

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-muted-foreground text-sm font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Role-based page access check
  if (requiredPagePath && !roleLoading && role && !canViewPage(role, requiredPagePath)) {
    return <AccessDenied />;
  }

  return <>{children}</>;
}
