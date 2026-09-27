import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';
import DashboardPage from '../../features/dashboard/DashboardPage';

vi.mock('../../components/layout/PageLayout', () => ({
  default: ({ children }: { children: (v: unknown) => React.ReactNode }) =>
    children({ selectedCompanyId: 3, selectedCompany: { name: 'Tenant' }, companiesLoading: false }),
}));
vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  XAxis: () => null, YAxis: () => null, CartesianGrid: () => null,
  Tooltip: () => null, Cell: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock('../../api/client', () => ({ default: { get: vi.fn() } }));

import apiClient from '../../api/client';
const mockGet = vi.mocked(apiClient.get);

/** The real 400 from report_routes.py when no fiscal year covers today. */
const missingFiscalYear = () =>
  Object.assign(new Error('Request failed with status code 400'), {
    response: { status: 400, data: { detail: 'No fiscal year covers the requested date' } },
  });

function respond(failing: string[]) {
  mockGet.mockImplementation((url: string) => {
    if (failing.some((fragment) => url.includes(fragment))) return Promise.reject(missingFiscalYear());
    if (url.includes('/journal-entries') || url.includes('/accounts')) {
      return Promise.resolve({ data: { items: [], total: 0, skip: 0, limit: 5 } });
    }
    return Promise.resolve({ data: { is_balanced: true, total_assets: 0, total_liabilities: 0, total_equity: 0, net_profit: 0 } });
  });
}

const banner = () => screen.queryByText(en.common.somethingWentWrong);
const dashboardRendered = () => screen.queryByText(en.dashboard.financialOverview) !== null;

describe('dashboard reports a source that failed', () => {
  beforeEach(() => vi.clearAllMocks());

  it('says so, and keeps the sections that loaded, when one source fails', async () => {
    respond(['/reports/balance-sheet']);
    render(<I18nProvider><DashboardPage /></I18nProvider>);

    await waitFor(() => expect(dashboardRendered()).toBe(true));
    expect(banner()).not.toBeNull();
    expect(screen.getByText(en.nav.balanceSheet)).toBeInTheDocument();
    expect(dashboardRendered()).toBe(true);
  });

  it('names every source that failed', async () => {
    respond(['/reports/balance-sheet', '/reports/profit-and-loss']);
    render(<I18nProvider><DashboardPage /></I18nProvider>);
    await waitFor(() => expect(banner()).not.toBeNull());
    const names = screen.getByText(new RegExp(`${en.nav.balanceSheet}|${en.nav.profitAndLoss}`));
    expect(names.textContent).toContain(en.nav.profitAndLoss);
    expect(names.textContent).toContain(en.nav.balanceSheet);
  });

  it('shows nothing but the error when every source fails', async () => {
    respond(['/']);
    render(<I18nProvider><DashboardPage /></I18nProvider>);
    await waitFor(() =>
      expect(screen.queryByText(/Failed to load dashboard data/)).not.toBeNull(),
    );
    expect(dashboardRendered()).toBe(false);
  });

  it('shows no banner when everything loads', async () => {
    respond([]);
    render(<I18nProvider><DashboardPage /></I18nProvider>);
    await waitFor(() => expect(dashboardRendered()).toBe(true));
    expect(banner()).toBeNull();
  });
});
