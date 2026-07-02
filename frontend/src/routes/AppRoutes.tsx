import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from '../components/layout/ProtectedRoute';
import LoadingState from '../components/feedback/LoadingState';

const LoginPage = lazy(() => import('../features/auth/LoginPage'));
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

function RouteLoader() {
  return (
    <div className="min-h-screen bg-surface-900 p-8">
      <LoadingState />
    </div>
  );
}

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteLoader />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/accept-invite" element={<AcceptInvitePage />} />
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
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
