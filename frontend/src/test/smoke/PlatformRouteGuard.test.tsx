import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProtectedRoute from '../../components/layout/ProtectedRoute';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';

// AuthContext keeps its User shape private, so the mock declares the fields the
// guard actually reads.
interface SessionUser {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  must_change_password: boolean;
}

const authState = { user: null as SessionUser | null, isLoading: false };

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => authState,
}));

vi.mock('../../features/companies/useCompanies', () => ({
  useCompanies: () => ({ selectedCompanyId: 1 }),
}));

vi.mock('../../auth/useCompanyRole', () => ({
  useCompanyRole: () => ({ role: 'admin', isLoading: false }),
}));

function makeUser(isSuperuser: boolean, mustChangePassword = false): SessionUser {
  return {
    id: 1,
    email: 'someone@example.com',
    full_name: 'Someone',
    is_active: true,
    is_superuser: isSuperuser,
    must_change_password: mustChangePassword,
  };
}

const PLATFORM_CONTENT = 'platform-page-content';

function renderPlatformRoute() {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <ProtectedRoute requiredPagePath="/platform/subscriptions">
          <p>{PLATFORM_CONTENT}</p>
        </ProtectedRoute>
      </I18nProvider>
    </MemoryRouter>,
  );
}

describe('platform route guard', () => {
  beforeEach(() => {
    authState.user = null;
    authState.isLoading = false;
  });

  it('renders the page for a platform admin', () => {
    authState.user = makeUser(true);
    renderPlatformRoute();
    expect(screen.getByText(PLATFORM_CONTENT)).toBeInTheDocument();
  });

  // A company admin is the strongest tenant role there is, so it is the case
  // that proves the guard reads the platform flag rather than the company role.
  it('denies a company admin without leaking the page', () => {
    authState.user = makeUser(false);
    renderPlatformRoute();
    expect(screen.getByText(en.permissions.accessDenied)).toBeInTheDocument();
    expect(screen.queryByText(PLATFORM_CONTENT)).not.toBeInTheDocument();
  });

  // The platform owner is the one role that could plausibly be exempted, so it
  // is the case that proves nobody is.
  it('sends even a platform admin to the password change while the flag is set', () => {
    authState.user = makeUser(true, true);
    renderPlatformRoute();
    expect(screen.queryByText(PLATFORM_CONTENT)).not.toBeInTheDocument();
    expect(screen.queryByText(en.permissions.accessDenied)).not.toBeInTheDocument();
  });

  it('shows platform guidance instead of rendering a tenant page', () => {
    authState.user = makeUser(true);
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <I18nProvider>
          <ProtectedRoute>
            <p>tenant-dashboard-content</p>
          </ProtectedRoute>
        </I18nProvider>
      </MemoryRouter>,
    );

    expect(screen.getByText(en.platformAccessNotice.title)).toBeInTheDocument();
    expect(screen.getByText(en.platformAccessNotice.message)).toBeInTheDocument();
    expect(screen.queryByText('tenant-dashboard-content')).not.toBeInTheDocument();
  });
});
