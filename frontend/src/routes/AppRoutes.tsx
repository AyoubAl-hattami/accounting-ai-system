import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from '../components/layout/ProtectedRoute';
import AppLayout from '../components/layout/AppLayout';
import LoadingState from '../components/feedback/LoadingState';
import { useAuth } from '../auth/AuthContext';
import { CompaniesProvider } from '../features/companies/CompaniesProvider';
import { defaultAuthenticatedRoute } from '../auth/defaultRoute';

const LoginPage = lazy(() => import('../features/auth/LoginPage'));
const ChangeTemporaryPasswordPage = lazy(
  () => import('../features/auth/ChangeTemporaryPasswordPage'),
);
const DashboardPage = lazy(() => import('../features/dashboard/DashboardPage'));
const AccountsPage = lazy(() => import('../features/accounts/AccountsPage'));
const JournalEntriesPage = lazy(() => import('../features/journals/JournalEntriesPage'));
const TrialBalancePage = lazy(() => import('../features/reports/trial-balance/TrialBalancePage'));
const ProfitAndLossPage = lazy(() => import('../features/reports/profit-and-loss/ProfitAndLossPage'));
const BalanceSheetPage = lazy(() => import('../features/reports/balance-sheet/BalanceSheetPage'));
const AccountLedgerPage = lazy(() => import('../features/reports/account-ledger/AccountLedgerPage'));
const GeneralLedgerPage = lazy(() => import('../features/reports/general-ledger/GeneralLedgerPage'));
const AuditLogsPage = lazy(() => import('../features/audit/AuditLogsPage'));
const CompanyUsersPage = lazy(() => import('../features/company-users/CompanyUsersPage'));
const AcceptInvitePage = lazy(() => import('../features/company-users/AcceptInvitePage'));
const SettingsPage = lazy(() => import('../features/settings/SettingsPage'));
const PlatformSubscriptionsPage = lazy(
  () => import('../features/subscriptions/PlatformSubscriptionsPage'),
);
const PlatformDashboardPage = lazy(
  () => import('../features/platform-dashboard/PlatformDashboardPage'),
);
const ClientOnboardingPage = lazy(
  () => import('../features/onboarding/ClientOnboardingPage'),
);

function RouteLoader() {
  return (
    <div className="min-h-screen bg-background p-8">
      <LoadingState />
    </div>
  );
}

/**
 * Keeps the change screen from becoming its own trap: an account that has
 * already cleared the flag is sent on to the app rather than left staring at a
 * form it cannot meaningfully submit.
 */
function ForcedPasswordChangeRoute() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <RouteLoader />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.must_change_password) {
    return <Navigate to={defaultAuthenticatedRoute(user)} replace />;
  }

  return <ChangeTemporaryPasswordPage />;
}

function HomeRedirect() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <RouteLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={defaultAuthenticatedRoute(user)} replace />;
}

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <CompaniesProvider>
        <Routes>
          {/* Public routes carry their own chrome, so they keep a full-page
              fallback and stay outside the shell. */}
          <Route
            path="/login"
            element={
              <Suspense fallback={<RouteLoader />}>
                <LoginPage />
              </Suspense>
            }
          />
          <Route
            path="/accept-invite"
            element={
              <Suspense fallback={<RouteLoader />}>
                <AcceptInvitePage />
              </Suspense>
            }
          />
          {/* Outside the shell on purpose: an account that must change its
              password can reach nothing behind that shell yet. */}
          <Route
            path="/auth/change-temporary-password"
            element={
              <Suspense fallback={<RouteLoader />}>
                <ForcedPasswordChangeRoute />
              </Suspense>
            }
          />

          {/* Everything below shares one AppLayout instance. Because the layout
              element is the same component across these routes, React keeps the
              shell mounted and swaps only what the Outlet renders. */}
          <Route element={<AppLayout />}>
            <Route
              path="/platform/dashboard"
              element={
                <ProtectedRoute requiredPagePath="/platform/dashboard">
                  <PlatformDashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/accounts"
              element={
                <ProtectedRoute>
                  <AccountsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/journal-entries"
              element={
                <ProtectedRoute>
                  <JournalEntriesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports/trial-balance"
              element={
                <ProtectedRoute>
                  <TrialBalancePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports/profit-and-loss"
              element={
                <ProtectedRoute>
                  <ProfitAndLossPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports/balance-sheet"
              element={
                <ProtectedRoute>
                  <BalanceSheetPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports/account-ledger"
              element={
                <ProtectedRoute>
                  <AccountLedgerPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports/general-ledger"
              element={
                <ProtectedRoute>
                  <GeneralLedgerPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/audit-logs"
              element={
                <ProtectedRoute requiredPagePath="/audit-logs">
                  <AuditLogsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/company-users"
              element={
                <ProtectedRoute requiredPagePath="/company-users">
                  <CompanyUsersPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute requiredPagePath="/settings">
                  <SettingsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/platform/subscriptions"
              element={
                <ProtectedRoute requiredPagePath="/platform/subscriptions">
                  <PlatformSubscriptionsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/platform/onboarding"
              element={
                <ProtectedRoute requiredPagePath="/platform/onboarding">
                  <ClientOnboardingPage />
                </ProtectedRoute>
              }
            />
          </Route>

          <Route path="/" element={<HomeRedirect />} />
          <Route path="*" element={<HomeRedirect />} />
        </Routes>
      </CompaniesProvider>
    </BrowserRouter>
  );
}
