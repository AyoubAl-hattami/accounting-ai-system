import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import DashboardPage from '../../features/dashboard/DashboardPage';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';

vi.mock('../../components/layout/PageLayout', () => ({
  default: ({ children }: { children: (value: unknown) => React.ReactNode }) =>
    children({
      selectedCompanyId: 7,
      selectedCompany: { name: 'Mobile Tenant' },
      companiesLoading: false,
    }),
}));

vi.mock('../../features/dashboard/useDashboardData', () => ({
  useDashboardData: () => ({
    data: {
      balanceSheet: null,
      profitLoss: null,
      trialBalance: null,
      journalEntries: { items: [], total: 0, skip: 0, limit: 5 },
      accounts: { items: [], total: 0, skip: 0, limit: 1 },
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Cell: () => null,
}));

describe('tenant dashboard mobile layout', () => {
  it('uses narrow-screen card grids and clipped chart containers', () => {
    const { container } = render(
      <I18nProvider>
        <DashboardPage />
      </I18nProvider>,
    );

    expect(screen.getByText(en.dashboard.financialOverview)).toBeInTheDocument();
    expect(
      Array.from(container.querySelectorAll('div')).some((element) =>
        element.classList.contains('min-[430px]:grid-cols-2'),
      ),
    ).toBe(true);
    expect(container.querySelectorAll('.min-w-0.overflow-hidden').length).toBeGreaterThan(1);
  });
});
