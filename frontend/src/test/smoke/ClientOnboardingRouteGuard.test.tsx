import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProtectedRoute from '../../components/layout/ProtectedRoute';
import { isPlatformPage } from '../../auth/permissions';
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

function makeUser(isSuperuser: boolean): SessionUser {
  return {
    id: 1,
    email: 'someone@example.com',
    full_name: 'Someone',
    is_active: true,
    is_superuser: isSuperuser,
  };
}

const ONBOARDING_CONTENT = 'client-onboarding-wizard';

function renderOnboardingRoute() {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <ProtectedRoute requiredPagePath="/platform/onboarding">
          <p>{ONBOARDING_CONTENT}</p>
        </ProtectedRoute>
      </I18nProvider>
    </MemoryRouter>,
  );
}

describe('client onboarding route guard', () => {
  beforeEach(() => {
    authState.user = null;
    authState.isLoading = false;
  });

  // Without this registration the route would fall through to canViewPage,
  // which lets unknown paths past, and every tenant role would see the wizard.
  it('treats the onboarding route as a platform page', () => {
    expect(isPlatformPage('/platform/onboarding')).toBe(true);
  });

  it('renders the wizard for a platform admin', () => {
    authState.user = makeUser(true);
    renderOnboardingRoute();
    expect(screen.getByText(ONBOARDING_CONTENT)).toBeInTheDocument();
  });

  // A company admin is the strongest tenant role there is, so it is the case
  // that proves the guard reads the platform flag rather than the company role.
  it('denies a company admin without leaking the wizard', () => {
    authState.user = makeUser(false);
    renderOnboardingRoute();
    expect(screen.getByText(en.permissions.accessDenied)).toBeInTheDocument();
    expect(screen.queryByText(ONBOARDING_CONTENT)).not.toBeInTheDocument();
  });
});
