import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ChangeTemporaryPasswordPage from '../../features/auth/ChangeTemporaryPasswordPage';
import { I18nProvider } from '../../i18n';
import { ThemeProvider } from '../../theme';
import { ar, en } from '../../i18n/translations';

vi.mock('../../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

const navigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigate };
});

const refreshUser = vi.fn();
const login = vi.fn();
const authState = {
  user: {
    id: 4,
    email: 'admin@northwind.test',
    full_name: 'Admin',
    is_active: true,
    is_superuser: false,
    must_change_password: true,
  },
  isLoading: false,
  login,
  logout: vi.fn(),
  refreshUser,
};

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => authState,
}));

import apiClient from '../../api/client';

const mockPost = vi.mocked(apiClient.post);
const copy = en.changePassword;

function renderPage(language: 'en' | 'ar' = 'en') {
  localStorage.setItem('app-language', language);
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <I18nProvider>
          <ChangeTemporaryPasswordPage />
        </I18nProvider>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

function fillForm(current: string, next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText(copy.currentPasswordLabel), {
    target: { value: current },
  });
  fireEvent.change(screen.getByLabelText(copy.newPasswordLabel), { target: { value: next } });
  fireEvent.change(screen.getByLabelText(copy.confirmPasswordLabel), {
    target: { value: confirm },
  });
}

describe('forced temporary password change', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders the agreed English copy', () => {
    renderPage();
    expect(screen.getByText(copy.title)).toBeInTheDocument();
    expect(screen.getByText(copy.description)).toBeInTheDocument();
    expect(screen.getByLabelText(copy.currentPasswordLabel)).toBeInTheDocument();
    expect(screen.getByLabelText(copy.newPasswordLabel)).toBeInTheDocument();
    expect(screen.getByLabelText(copy.confirmPasswordLabel)).toBeInTheDocument();
  });

  it('renders the agreed Arabic copy', () => {
    renderPage('ar');
    expect(screen.getByText(ar.changePassword.title)).toBeInTheDocument();
    expect(screen.getByText(ar.changePassword.description)).toBeInTheDocument();
  });

  it('submits the change, obtains a new session and leaves for the dashboard', async () => {
    mockPost.mockResolvedValueOnce({ data: {} } as never);
    login.mockResolvedValueOnce({ ...authState.user, must_change_password: false });
    renderPage();
    fillForm('Temp0rary1', 'N3wStrongPass', 'N3wStrongPass');
    fireEvent.click(screen.getByRole('button', { name: copy.submit }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith('/auth/change-temporary-password', {
      current_password: 'Temp0rary1',
      new_password: 'N3wStrongPass',
      confirm_password: 'N3wStrongPass',
    });

    await waitFor(() =>
      expect(login).toHaveBeenCalledWith('admin@northwind.test', 'N3wStrongPass'),
    );
    expect(navigate).toHaveBeenCalledWith('/dashboard', { replace: true });
  });

  // Caught before the request, so a typo costs a message rather than a round
  // trip that would come back as a raw validation error.
  it('refuses a mismatched confirmation without calling the API', async () => {
    renderPage();
    fillForm('Temp0rary1', 'N3wStrongPass', 'N3wStrongPas');
    fireEvent.click(screen.getByRole('button', { name: copy.submit }));

    expect(await screen.findByText(copy.mismatch)).toBeInTheDocument();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('refuses a new password the backend policy would reject', async () => {
    renderPage();
    fillForm('Temp0rary1', 'weakpass', 'weakpass');
    fireEvent.click(screen.getByRole('button', { name: copy.submit }));

    expect(await screen.findByText(copy.tooWeak)).toBeInTheDocument();
    expect(mockPost).not.toHaveBeenCalled();
  });

  // The refusal must reach the operator as a sentence, never as response JSON.
  it('explains a wrong current password and stays on the page', async () => {
    mockPost.mockRejectedValueOnce({ response: { status: 400, data: { detail: 'nope' } } });
    renderPage();
    fillForm('WrongOne1', 'N3wStrongPass', 'N3wStrongPass');
    fireEvent.click(screen.getByRole('button', { name: copy.submit }));

    expect(await screen.findByText(copy.currentIncorrect)).toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();
    expect(screen.queryByText(/nope/)).not.toBeInTheDocument();
  });
});
