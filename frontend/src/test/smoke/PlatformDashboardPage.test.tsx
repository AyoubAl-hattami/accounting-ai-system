import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PlatformDashboardPage from '../../features/platform-dashboard/PlatformDashboardPage';
import { PageMetaContext } from '../../components/layout/pageMeta';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn().mockResolvedValue({
      data: {
        total_clients: 12,
        trial_subscriptions: 3,
        active_subscriptions: 7,
        past_due_subscriptions: 1,
        suspended_subscriptions: 1,
        cancelled_subscriptions: 0,
        recent_clients: [
          {
            company_id: 8,
            company_name: 'Northwind Trading',
            base_currency: 'USD',
            company_is_active: true,
            subscription: {
              id: 8,
              company_id: 8,
              status: 'trial',
              plan_code: 'standard',
              expires_at: null,
              trial_ends_at: null,
              suspended_at: null,
              cancelled_at: null,
              suspension_reason: null,
              created_at: null,
              updated_at: null,
            },
            effective_status: 'trial',
            days_remaining: null,
            member_count: 1,
            created_at: '2026-08-11T10:00:00Z',
            primary_admin_email: 'admin@northwind.test',
          },
        ],
      },
    }),
  },
}));

describe('platform dashboard page', () => {
  it('shows client totals, recent onboarding, and status distribution', async () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <PageMetaContext.Provider value={{ meta: {}, setMeta: vi.fn() }}>
            <PlatformDashboardPage />
          </PageMetaContext.Provider>
        </I18nProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Northwind Trading')).toBeInTheDocument();
    expect(screen.getByText('admin@northwind.test')).toBeInTheDocument();
    expect(screen.getByText(en.platformDashboard.totalClients)).toBeInTheDocument();
    expect(screen.getByText(en.platformDashboard.statusDistribution)).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: en.platformDashboard.manageSubscriptions }),
    ).toHaveAttribute('href', '/platform/subscriptions');
  });
});
