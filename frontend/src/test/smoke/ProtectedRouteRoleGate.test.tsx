import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProtectedRoute from '../../components/layout/ProtectedRoute';
import { I18nProvider } from '../../i18n';

const authState = { user: { id: 1, is_superuser: false, must_change_password: false }, isLoading: false };
const companiesState: { selectedCompanyId: number | null; isLoading: boolean } = {
  selectedCompanyId: 4,
  isLoading: false,
};
const roleState: { role: string | null; isLoading: boolean } = { role: 'admin', isLoading: false };

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => authState }));
vi.mock('../../features/companies/useCompanies', () => ({ useCompanies: () => companiesState }));
vi.mock('../../auth/useCompanyRole', () => ({ useCompanyRole: () => roleState }));

function renderGuard(path = '/settings') {
  return render(
    <I18nProvider>
      <MemoryRouter initialEntries={[path]}>
        <ProtectedRoute requiredPagePath={path}>
          <div>SECRET PAGE</div>
        </ProtectedRoute>
      </MemoryRouter>
    </I18nProvider>,
  );
}

const shown = () => screen.queryByText('SECRET PAGE') !== null;

describe('ProtectedRoute does not render a gated page on an unresolved role', () => {
  beforeEach(() => {
    authState.user = { id: 1, is_superuser: false, must_change_password: false };
    authState.isLoading = false;
    companiesState.selectedCompanyId = 4;
    companiesState.isLoading = false;
    roleState.role = 'admin';
    roleState.isLoading = false;
  });

  it('renders the page for a role that is allowed', () => {
    renderGuard();
    expect(shown()).toBe(true);
  });

  it('refuses a role that is not allowed', () => {
    roleState.role = 'viewer';
    renderGuard();
    expect(shown()).toBe(false);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  // The regression this file exists for. `role` is null while the lookup is in
  // flight, when it fails, and when the membership is inactive; the guard used
  // to require a truthy role in order to deny, so every one of those rendered
  // the page.
  it('waits rather than rendering while the role lookup is in flight', () => {
    roleState.role = null;
    roleState.isLoading = true;
    renderGuard();
    expect(shown()).toBe(false);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('refuses when the role lookup resolved to no role', () => {
    roleState.role = null;
    roleState.isLoading = false;
    renderGuard();
    expect(shown()).toBe(false);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('waits rather than rendering while the company list is still loading', () => {
    companiesState.selectedCompanyId = null;
    companiesState.isLoading = true;
    roleState.role = null;
    renderGuard();
    expect(shown()).toBe(false);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  // Deliberately preserved: with no company there is no role to resolve and
  // nothing company-scoped to leak, so the page's own empty state answers.
  it('still renders when no company is selected', () => {
    companiesState.selectedCompanyId = null;
    companiesState.isLoading = false;
    roleState.role = null;
    renderGuard();
    expect(shown()).toBe(true);
  });
});
