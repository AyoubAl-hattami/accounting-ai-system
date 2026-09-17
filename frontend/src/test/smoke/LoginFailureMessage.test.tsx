import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LoginPage from '../../features/auth/LoginPage';
import { I18nProvider } from '../../i18n';
import { ThemeProvider } from '../../theme';
import { en } from '../../i18n/translations';
import { isExpiredSession } from '../../api/client';
import { errorMessage } from '../../api/errorMessage';

/* A wrong password showed nothing at all.
 *
 * The login form does set an error and does render it. What removed it was the
 * shared response interceptor: it treated every 401 as an expired session, so a
 * failed sign-in assigned window.location.href = '/login'. That is a full page
 * load -- the form unmounted and the message went with it, leaving a blank
 * login page that looked like the button had done nothing.
 *
 * These cover the two halves: the interceptor must leave a sign-in 401 alone,
 * and the form must show the reason. */

const login = vi.fn();

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ login }),
}));

function unauthorized(url: string, detail?: string) {
  return {
    config: { url },
    response: { status: 401, data: detail ? { detail } : undefined },
  };
}

function renderLogin() {
  return render(
    <I18nProvider>
      <ThemeProvider>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<div>DASHBOARD</div>} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>
    </I18nProvider>,
  );
}

async function submit(user: ReturnType<typeof userEvent.setup>) {
  // Exact labels, not regexes: /Password/i also matches the show-password button.
  await user.type(screen.getByLabelText(en.login.emailLabel), 'someone@acme-demo.com');
  await user.type(screen.getByLabelText(en.login.passwordLabel), 'wrong-password');
  await user.click(screen.getByRole('button', { name: en.login.signIn }));
}

describe('isExpiredSession', () => {
  it('leaves a failed sign-in alone', () => {
    expect(isExpiredSession(unauthorized('/auth/login'))).toBe(false);
  });

  it('still treats a 401 on any other call as an ended session', () => {
    expect(isExpiredSession(unauthorized('/accounts'))).toBe(true);
    expect(isExpiredSession(unauthorized('/auth/me'))).toBe(true);
  });

  it.each([
    ['an absolute sign-in URL', 'http://127.0.0.1:8010/auth/login'],
    ['a trailing slash', '/auth/login/'],
    ['a query string', '/auth/login?next=%2Fdashboard'],
  ])('recognises the sign-in request with %s', (_label, url) => {
    expect(isExpiredSession(unauthorized(url))).toBe(false);
  });

  it('ignores failures that are not 401', () => {
    expect(isExpiredSession({ config: { url: '/accounts' }, response: { status: 403 } })).toBe(false);
    expect(isExpiredSession({ config: { url: '/accounts' } })).toBe(false);
    expect(isExpiredSession(null)).toBe(false);
  });

  it('does not mistake a path that merely contains the sign-in path', () => {
    expect(isExpiredSession(unauthorized('/auth/login-history'))).toBe(true);
  });
});

describe('the login form says why a sign-in failed', () => {
  beforeEach(() => {
    login.mockReset();
  });

  it('says the credentials are wrong, in the language of the page', async () => {
    const user = userEvent.setup();
    // The server answers in English; the page has its own translated wording
    // and uses that instead, so an Arabic UI does not show a foreign string.
    login.mockRejectedValue(unauthorized('/auth/login', 'Invalid email or password'));
    renderLogin();
    await submit(user);

    expect(await screen.findByRole('alert')).toHaveTextContent(en.login.invalidCredentials);
  });

  it('says so even when the server sends no reason at all', async () => {
    const user = userEvent.setup();
    login.mockRejectedValue(unauthorized('/auth/login'));
    renderLogin();
    await submit(user);

    expect(await screen.findByRole('alert')).toHaveTextContent(en.login.invalidCredentials);
  });

  it('keeps the server wording for anything that is not a bad password', async () => {
    const user = userEvent.setup();
    // A lockout carries information the client does not have, so it is shown
    // as the server phrased it.
    login.mockRejectedValue({
      config: { url: '/auth/login' },
      response: { status: 429, data: { detail: 'Too many attempts. Try again later.' } },
    });
    renderLogin();
    await submit(user);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Too many attempts. Try again later.',
    );
  });

  it('says so when the request never reached the server', async () => {
    const user = userEvent.setup();
    login.mockRejectedValue(new Error('Network Error'));
    renderLogin();
    await submit(user);

    expect(await screen.findByRole('alert')).toHaveTextContent(en.login.networkError);
  });

  it('marks both fields invalid so the message is announced', async () => {
    const user = userEvent.setup();
    login.mockRejectedValue(unauthorized('/auth/login', 'Invalid email or password'));
    renderLogin();
    await submit(user);
    await screen.findByRole('alert');

    expect(screen.getByLabelText(en.login.emailLabel)).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText(en.login.passwordLabel)).toHaveAttribute(
      'aria-describedby',
      'login-error',
    );
  });
});

describe('errorMessage normalises what FastAPI sends', () => {
  it('keeps a plain string detail', () => {
    expect(errorMessage(unauthorized('/auth/login', 'Invalid email or password'), 'fallback'))
      .toBe('Invalid email or password');
  });

  it('reads a 422 validation array instead of handing React an object', () => {
    // This is the shape that turned the login page white.
    const validation = {
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ['body', 'email'], msg: 'value is not a valid email address' },
            { loc: ['body', 'password'], msg: 'String should have at least 8 characters' },
          ],
        },
      },
    };
    expect(errorMessage(validation, 'fallback')).toBe(
      'value is not a valid email address. String should have at least 8 characters',
    );
  });

  it('reads the object form the forced-password-change gate uses', () => {
    const gated = {
      response: {
        status: 403,
        data: {
          detail: {
            code: 'PASSWORD_CHANGE_REQUIRED',
            message: 'You must change your temporary password before using the system.',
          },
        },
      },
    };
    expect(errorMessage(gated, 'fallback')).toBe(
      'You must change your temporary password before using the system.',
    );
  });

  it.each([
    ['no response at all', new Error('Network Error')],
    ['no detail', { response: { status: 500, data: {} } }],
    ['a blank detail', { response: { status: 400, data: { detail: '   ' } } }],
    ['an array with nothing readable', { response: { status: 422, data: { detail: [{}] } } }],
    ['null', null],
  ])('falls back on %s', (_label, error) => {
    expect(errorMessage(error, 'fallback')).toBe('fallback');
  });

  it('always returns a string, so React can never be handed an object', () => {
    const shapes: unknown[] = [
      unauthorized('/auth/login', 'text'),
      { response: { data: { detail: [{ msg: 'a' }] } } },
      { response: { data: { detail: { message: 'b' } } } },
      { response: { data: { detail: 42 } } },
      undefined,
    ];
    for (const shape of shapes) {
      expect(typeof errorMessage(shape, 'fallback')).toBe('string');
    }
  });
});
