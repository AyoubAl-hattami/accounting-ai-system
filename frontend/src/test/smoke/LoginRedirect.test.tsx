import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LoginPage from '../../features/auth/LoginPage';
import { I18nProvider } from '../../i18n';
import { ThemeProvider } from '../../theme';
import { en } from '../../i18n/translations';
import { safeRedirectTarget } from '../../auth/safeRedirect';

const signedIn = { id: 1, is_superuser: false, must_change_password: false };
const login = vi.fn();

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ login }),
}));

function renderAt(path: string) {
  return render(
    <I18nProvider>
      <ThemeProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/accept-invite" element={<div>ACCEPT INVITE PAGE</div>} />
          <Route path="/dashboard" element={<div>DASHBOARD</div>} />
          <Route
            path="/auth/change-temporary-password"
            element={<div>CHANGE PASSWORD</div>}
          />
        </Routes>
      </MemoryRouter>
      </ThemeProvider>
    </I18nProvider>,
  );
}

async function signIn(user: ReturnType<typeof userEvent.setup>) {
  // Exact labels, not regexes: /Password/i also matches the show-password button.
  await user.type(screen.getByLabelText(en.login.emailLabel), 'a@b.test');
  await user.type(screen.getByLabelText(en.login.passwordLabel), 'Password123');
  await user.click(screen.getByRole('button', { name: en.login.signIn }));
}

describe('safeRedirectTarget', () => {
  it('accepts a same-origin path', () => {
    expect(safeRedirectTarget('/accept-invite?token=abc')).toBe('/accept-invite?token=abc');
  });

  it.each([
    ['null', null],
    ['empty', ''],
    ['absolute http', 'http://evil.tld/'],
    ['absolute https', 'https://evil.tld/'],
    ['protocol-relative', '//evil.tld/'],
    ['backslash form', '/\\evil.tld/'],
    ['scheme-ish', 'javascript:alert(1)'],
    ['bare host', 'evil.tld'],
  ])('rejects %s', (_label, value) => {
    expect(safeRedirectTarget(value as string | null)).toBeNull();
  });
});

describe('login honours ?redirect=', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    login.mockResolvedValue(signedIn);
  });

  // [A5] The invitation flow sends the visitor to /login?redirect=<accept page>.
  // LoginPage used to ignore it, landing them on the dashboard with the
  // invitation lost.
  it('returns to the invitation after signing in', async () => {
    const user = userEvent.setup();
    renderAt(`/login?redirect=${encodeURIComponent('/accept-invite?token=abc')}`);
    await signIn(user);
    await waitFor(() => expect(screen.getByText('ACCEPT INVITE PAGE')).toBeInTheDocument());
  });

  it('ignores an off-origin redirect and uses the default route', async () => {
    const user = userEvent.setup();
    renderAt(`/login?redirect=${encodeURIComponent('//evil.tld/')}`);
    await signIn(user);
    await waitFor(() => expect(screen.getByText('DASHBOARD')).toBeInTheDocument());
  });

  it('uses the default route when there is no redirect', async () => {
    const user = userEvent.setup();
    renderAt('/login');
    await signIn(user);
    await waitFor(() => expect(screen.getByText('DASHBOARD')).toBeInTheDocument());
  });

  // The temporary-password gate is not a destination the user chose, and
  // skipping it would leave the account on a credential it must replace.
  it('sends a temporary-password account to the change form, redirect or not', async () => {
    const user = userEvent.setup();
    login.mockResolvedValue({ ...signedIn, must_change_password: true });
    renderAt(`/login?redirect=${encodeURIComponent('/accept-invite?token=abc')}`);
    await signIn(user);
    await waitFor(() => expect(screen.getByText('CHANGE PASSWORD')).toBeInTheDocument());
  });
});
