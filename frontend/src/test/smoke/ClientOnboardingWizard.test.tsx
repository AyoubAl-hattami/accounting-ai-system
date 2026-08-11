import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ClientOnboardingPage from '../../features/onboarding/ClientOnboardingPage';
import { ToastProvider } from '../../components/feedback/ToastProvider';
import { PageMetaContext } from '../../components/layout/pageMeta';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';
import type { ClientOnboardingResult } from '../../api/types';

vi.mock('../../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

import apiClient from '../../api/client';

const mockGet = vi.mocked(apiClient.get);
const mockPost = vi.mocked(apiClient.post);

const copy = en.clientOnboarding;

const RESULT: ClientOnboardingResult = {
  company_id: 42,
  company_name: 'Northwind Trading',
  base_currency: 'USD',
  admin_user_id: 7,
  admin_email: 'admin@northwind.test',
  admin_was_existing: false,
  subscription_status: 'active',
  effective_status: 'active',
  plan_code: 'monthly',
  expires_at: '2026-09-30T23:59:59Z',
  trial_ends_at: null,
  days_remaining: 30,
  seeded_accounts_count: 13,
  fiscal_year_created: true,
  fiscal_periods_created: 12,
  generated_password: 'Sw1ftPelican42',
  must_change_password: true,
  public_login_url: 'https://accounting.example.com',
  handover_message: 'server copy, unused by the wizard',
};

function renderWizard() {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <ToastProvider>
          <PageMetaContext.Provider value={{ meta: {}, setMeta: vi.fn() }}>
            <ClientOnboardingPage />
          </PageMetaContext.Provider>
        </ToastProvider>
      </I18nProvider>
    </MemoryRouter>,
  );
}

const clickNext = () => fireEvent.click(screen.getByRole('button', { name: en.common.next }));

/** Fills the two required fields and walks to the review step. */
function advanceToReview() {
  fireEvent.change(screen.getByLabelText(copy.companyNameLabel), {
    target: { value: 'Northwind Trading' },
  });
  clickNext();
  fireEvent.change(screen.getByLabelText(copy.adminEmailLabel), {
    target: { value: 'admin@northwind.test' },
  });
  clickNext(); // → subscription
  clickNext(); // → accounting
  clickNext(); // → review
}

describe('client onboarding wizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: null } as never);
  });

  it('refuses to leave the first step without a company name', async () => {
    renderWizard();
    clickNext();
    expect(await screen.findByText(copy.validationCompanyNameRequired)).toBeInTheDocument();
    expect(screen.getByLabelText(copy.companyNameLabel)).toBeInTheDocument();
  });

  it('refuses a manual password that the backend policy would reject', async () => {
    renderWizard();
    fireEvent.change(screen.getByLabelText(copy.companyNameLabel), {
      target: { value: 'Northwind Trading' },
    });
    clickNext();
    fireEvent.change(screen.getByLabelText(copy.adminEmailLabel), {
      target: { value: 'admin@northwind.test' },
    });
    fireEvent.click(screen.getByLabelText(copy.passwordModeManual));
    fireEvent.change(screen.getByLabelText(copy.temporaryPasswordLabel), {
      target: { value: 'weakpass' },
    });
    clickNext();
    expect(await screen.findByText(copy.validationPasswordTooWeak)).toBeInTheDocument();
  });

  // The one-time password only reaches the operator if the server is asked to
  // generate it and the subscription window is sent on the field the backend
  // reads for an active tenant.
  it('asks the server to generate the password and dates an active subscription', async () => {
    mockPost.mockResolvedValueOnce({ data: RESULT } as never);
    renderWizard();
    advanceToReview();

    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    const [url, payload] = mockPost.mock.calls[0] as [string, Record<string, unknown>];

    expect(url).toBe('/platform/onboarding/clients');
    expect(payload.company_name).toBe('Northwind Trading');
    expect(payload.admin_email).toBe('admin@northwind.test');
    expect(payload.generate_password).toBe(true);
    expect(payload.temporary_password).toBeUndefined();
    expect(payload.reuse_existing_user).toBe(false);
    expect(payload.subscription_status).toBe('active');
    expect(payload.subscription_expires_at).toEqual(expect.any(String));
    expect(payload.trial_ends_at).toBeNull();
    expect(payload.seed_default_accounts).toBe(true);
    expect(payload.create_fiscal_year).toBe(true);
    expect(payload.open_monthly_periods).toBe(true);
  });

  // A trial carries its end date on trial_ends_at, which is the field the
  // backend copies into the expiry so the trial actually lapses.
  it('sends a trial window on trial_ends_at', async () => {
    mockPost.mockResolvedValueOnce({ data: RESULT } as never);
    renderWizard();

    fireEvent.change(screen.getByLabelText(copy.companyNameLabel), {
      target: { value: 'Northwind Trading' },
    });
    clickNext();
    fireEvent.change(screen.getByLabelText(copy.adminEmailLabel), {
      target: { value: 'admin@northwind.test' },
    });
    clickNext();
    fireEvent.change(screen.getByLabelText(copy.statusLabel), { target: { value: 'trial' } });
    clickNext();
    clickNext();
    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    const [, payload] = mockPost.mock.calls[0] as [string, Record<string, unknown>];
    expect(payload.subscription_status).toBe('trial');
    expect(payload.trial_ends_at).toEqual(expect.any(String));
    expect(payload.subscription_expires_at).toBeNull();
  });

  it('shows the handover message and the one-time password warning after success', async () => {
    mockPost.mockResolvedValueOnce({ data: RESULT } as never);
    renderWizard();
    advanceToReview();
    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    expect(await screen.findByText(copy.successTitle)).toBeInTheDocument();

    const message = await screen.findByTestId('handover-message');
    expect(message.textContent).toContain('Company: Northwind Trading');
    expect(message.textContent).toContain('Admin email: admin@northwind.test');
    expect(message.textContent).toContain('Temporary password: Sw1ftPelican42');
    expect(message.textContent).toContain('Login URL: https://accounting.example.com');

    expect(screen.getAllByText(copy.passwordShownOnceWarning).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: copy.copyMessage })).toBeInTheDocument();
  });

  // The operator must be told the client cannot use the credential as-is, and
  // must be given the address to send them.
  it('shows the public login URL and the forced first-login change', async () => {
    mockPost.mockResolvedValueOnce({ data: RESULT } as never);
    renderWizard();
    advanceToReview();
    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    await screen.findByTestId('handover-message');

    expect(screen.getAllByText('https://accounting.example.com').length).toBeGreaterThan(0);
    expect(screen.getByText(copy.changePasswordWarning)).toBeInTheDocument();
    expect(screen.queryByText(copy.handoverUrlNotConfigured)).not.toBeInTheDocument();
  });

  it('warns when the server has no public URL configured', async () => {
    mockPost.mockResolvedValueOnce({
      data: { ...RESULT, public_login_url: '[add your domain here]' },
    } as never);
    renderWizard();
    advanceToReview();
    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    expect(await screen.findByText(copy.handoverUrlNotConfigured)).toBeInTheDocument();
  });

  // Leaving the success screen must drop the plaintext password with it.
  it('clears the temporary password when onboarding another client', async () => {
    mockPost.mockResolvedValueOnce({ data: RESULT } as never);
    renderWizard();
    advanceToReview();
    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    await screen.findByTestId('handover-message');
    fireEvent.click(screen.getByRole('button', { name: copy.onboardAnother }));

    expect(await screen.findByLabelText(copy.companyNameLabel)).toHaveValue('');
    expect(screen.queryByTestId('handover-message')).not.toBeInTheDocument();
    expect(screen.queryByText(/Sw1ftPelican42/)).not.toBeInTheDocument();
  });

  it('explains a duplicate company name instead of failing silently', async () => {
    mockPost.mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 409, data: { detail: "A company named 'Northwind Trading' already exists" } },
    });
    renderWizard();
    advanceToReview();
    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    expect(await screen.findByText(copy.errorCompanyExists)).toBeInTheDocument();
    expect(screen.queryByTestId('handover-message')).not.toBeInTheDocument();
  });

  it('explains a duplicate admin email and points at the reuse option', async () => {
    mockPost.mockRejectedValueOnce({
      isAxiosError: true,
      response: {
        status: 409,
        data: {
          detail:
            'An account already exists for admin@northwind.test. '
            + 'Set reuse_existing_user to attach it to this company.',
        },
      },
    });
    renderWizard();
    advanceToReview();
    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    expect(await screen.findByText(copy.errorAdminEmailExists)).toBeInTheDocument();
  });

  // The chart is a starting point, not a policy: the operator picks it, and no
  // country is ever the one the wizard picks on its own.
  it('defaults to the generic chart, never a regional one', async () => {
    mockPost.mockResolvedValueOnce({ data: RESULT } as never);
    renderWizard();
    advanceToReview();

    expect(screen.getByText(copy.chartSetupDefault)).toBeInTheDocument();
    expect(screen.queryByText(copy.chartSetupYemen)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    const [, payload] = mockPost.mock.calls[0] as [string, Record<string, unknown>];
    expect(payload.seed_default_accounts).toBe(true);
    expect(payload.chart_template).toBe('default');
  });

  it('can hand the client a completely blank chart', async () => {
    mockPost.mockResolvedValueOnce({ data: { ...RESULT, seeded_accounts_count: 0 } } as never);
    renderWizard();

    fireEvent.change(screen.getByLabelText(copy.companyNameLabel), {
      target: { value: 'Northwind Trading' },
    });
    clickNext();
    fireEvent.change(screen.getByLabelText(copy.adminEmailLabel), {
      target: { value: 'admin@northwind.test' },
    });
    clickNext();
    clickNext(); // → accounting
    fireEvent.click(screen.getByLabelText(copy.chartSetupBlank));
    clickNext(); // → review
    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    const [, payload] = mockPost.mock.calls[0] as [string, Record<string, unknown>];
    expect(payload.seed_default_accounts).toBe(false);
  });

  it('sends the regional starter only when it is explicitly chosen', async () => {
    mockPost.mockResolvedValueOnce({ data: RESULT } as never);
    renderWizard();

    fireEvent.change(screen.getByLabelText(copy.companyNameLabel), {
      target: { value: 'Northwind Trading' },
    });
    clickNext();
    fireEvent.change(screen.getByLabelText(copy.adminEmailLabel), {
      target: { value: 'admin@northwind.test' },
    });
    clickNext();
    clickNext(); // → accounting
    fireEvent.click(screen.getByLabelText(copy.chartSetupYemen));
    clickNext(); // → review

    expect(screen.getByText(copy.chartSetupYemen)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    const [, payload] = mockPost.mock.calls[0] as [string, Record<string, unknown>];
    expect(payload.seed_default_accounts).toBe(true);
    expect(payload.chart_template).toBe('yemen_cash_wallet');
  });

  it('offers the three chart choices side by side', () => {
    renderWizard();

    fireEvent.change(screen.getByLabelText(copy.companyNameLabel), {
      target: { value: 'Northwind Trading' },
    });
    clickNext();
    fireEvent.change(screen.getByLabelText(copy.adminEmailLabel), {
      target: { value: 'admin@northwind.test' },
    });
    clickNext();
    clickNext(); // → accounting

    expect(screen.getByLabelText(copy.chartSetupDefault)).toBeChecked();
    expect(screen.getByLabelText(copy.chartSetupBlank)).not.toBeChecked();
    expect(screen.getByLabelText(copy.chartSetupYemen)).not.toBeChecked();
    expect(screen.getByText(copy.chartSetupBlankHelp)).toBeInTheDocument();
  });

  it('explains an access refusal inside the page', async () => {
    mockPost.mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 403, data: { detail: 'Not enough permissions' } },
    });
    renderWizard();
    advanceToReview();
    fireEvent.click(screen.getByRole('button', { name: copy.createClient }));

    expect(await screen.findByText(copy.errorAccessDenied)).toBeInTheDocument();
  });
});
