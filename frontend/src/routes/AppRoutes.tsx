import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from '../features/auth/LoginPage';
import DashboardPage from '../features/dashboard/DashboardPage';
import AccountsPage from '../features/accounts/AccountsPage';
import JournalEntriesPage from '../features/journals/JournalEntriesPage';
import TrialBalancePage from '../features/reports/trial-balance/TrialBalancePage';
import ProfitAndLossPage from '../features/reports/profit-and-loss/ProfitAndLossPage';
import BalanceSheetPage from '../features/reports/balance-sheet/BalanceSheetPage';
import AccountLedgerPage from '../features/reports/account-ledger/AccountLedgerPage';
import GeneralLedgerPage from '../features/reports/general-ledger/GeneralLedgerPage';
import AuditLogsPage from '../features/audit/AuditLogsPage';
import CompanyUsersPage from '../features/company-users/CompanyUsersPage';
import SettingsPage from '../features/settings/SettingsPage';
import ProtectedRoute from '../components/layout/ProtectedRoute';

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
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
            <ProtectedRoute>
              <AuditLogsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/company-users"
          element={
            <ProtectedRoute>
              <CompanyUsersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
