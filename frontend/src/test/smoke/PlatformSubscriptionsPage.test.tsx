import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PlatformSubscriptionsPage from '../../features/subscriptions/PlatformSubscriptionsPage';
import { ToastProvider } from '../../components/feedback/ToastProvider';
import { PageMetaContext } from '../../components/layout/pageMeta';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';
import type { CompanySubscription, SubscriptionStatus } from '../../api/types';

vi.mock('../../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}));

import apiClient from '../../api/client';

const mockGet = vi.mocked(apiClient.get);
const copy = en.platformSubscriptions;

function makeEntry(
  companyId: number,
  companyName: string,
  status: SubscriptionStatus,
): CompanySubscription {
  return {
    company_id: companyId,
    company_name: companyName,
    base_currency: 'USD',
    company_is_active: true,
    subscription: {
      id: companyId,
      company_id: companyId,
      status,
      plan_code: 'monthly',
      expires_at: '2026-09-30T23:59:59Z',
      trial_ends_at: null,
      suspended_at: null,
      cancelled_at: null,
      suspension_reason: null,
      created_at: null,
      updated_at: null,
    },
    effective_status: status,
    days_remaining: 30,
    member_count: 4,
    created_at: '2026-08-11T10:00:00Z',
    primary_admin_email: 'admin@northwind.test',
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <I18nProvider>
        <ToastProvider>
          <PageMetaContext.Provider value={{ meta: {}, setMeta: vi.fn() }}>
            <PlatformSubscriptionsPage />
          </PageMetaContext.Provider>
        </ToastProvider>
      </I18nProvider>
    </MemoryRouter>,
  );
}

describe('platform subscriptions page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // The compaction moved currency and member count under the company name and
  // folded three of the six actions into icon buttons. Nothing was dropped, and
  // this is what says so.
  it('keeps the status badge and all six actions after the density pass', async () => {
    mockGet.mockResolvedValue({
      data: { items: [makeEntry(1, 'Northwind Trading', 'suspended')], total: 1 },
    } as never);

    renderPage();

    // The page renders the desktop table and the mobile cards together and
    // hides one with a CSS breakpoint, which the test DOM does not apply — so
    // every assertion is scoped to the table row.
    await screen.findAllByText('Northwind Trading');

    const rows = screen.getAllByRole('row');
    const row = rows.find((candidate) => within(candidate).queryByText('Northwind Trading'));
    expect(row).toBeDefined();

    const scope = within(row!);
    expect(scope.getByText(en.subscriptionStatus.suspended)).toBeInTheDocument();
    expect(scope.getByText('USD · 4 ' + copy.columnMembers)).toBeInTheDocument();

    for (const label of [
      copy.actionActivate,
      copy.actionExtendMonth,
      copy.actionExtendYear,
      copy.actionEdit,
      copy.actionSuspend,
      copy.actionCancel,
    ]) {
      expect(scope.getByRole('button', { name: label })).toBeInTheDocument();
    }
  });

  // Activating an already-active subscription is a no-op the operator would
  // have to reason about, so it is the one action that is conditional.
  it('hides activate on a subscription that is already active', async () => {
    mockGet.mockResolvedValue({
      data: { items: [makeEntry(2, 'Contoso Ltd', 'active')], total: 1 },
    } as never);

    renderPage();

    await screen.findAllByText('Contoso Ltd');

    const rows = screen.getAllByRole('row');
    const row = rows.find((candidate) => within(candidate).queryByText('Contoso Ltd'));
    const scope = within(row!);

    expect(scope.queryByRole('button', { name: copy.actionActivate })).not.toBeInTheDocument();
    expect(scope.getByRole('button', { name: copy.actionEdit })).toBeInTheDocument();
  });

  it('explains an empty result instead of showing a bare table', async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0 } } as never);

    renderPage();

    await waitFor(() => expect(screen.getByText(copy.emptyTitle)).toBeInTheDocument());
  });

  it('sends status and administrator search filters to the paginated endpoint', async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0 } } as never);
    renderPage();

    const search = screen.getByRole('searchbox');
    const status = screen.getByLabelText(copy.statusFilterLabel);
    fireEvent.change(search, { target: { value: 'admin@example.com' } });
    fireEvent.change(status, { target: { value: 'suspended' } });

    await waitFor(() => {
      const lastUrl = mockGet.mock.calls[mockGet.mock.calls.length - 1]?.[0] as string;
      expect(lastUrl).toContain('search=admin%40example.com');
      expect(lastUrl).toContain('status=suspended');
      expect(lastUrl).toContain('limit=20');
    });
  });
});
