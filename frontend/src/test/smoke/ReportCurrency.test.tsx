import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, renderHook } from '@testing-library/react';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';
import NewAccountModal from '../../features/accounts/NewAccountModal';
import ReportCurrencyField from '../../features/reports/components/ReportCurrencyField';
import { useReportCurrency } from '../../features/reports/components/useReportCurrency';
import type { Account } from '../../entities/account';

/* One report per currency.
 *
 * A company that keeps riyal and dollar accounts has two trial balances, never
 * one that adds them. These pin the UI half: the picker appears only when there
 * is a choice, the report is not fetched twice while the currency list loads,
 * and a new account can be opened in a currency other than the company's. */

const get = vi.fn();
vi.mock('../../api/client', () => ({ default: { get: (...args: unknown[]) => get(...args) } }));

beforeEach(() => {
  get.mockReset();
});

describe('useReportCurrency', () => {
  it('offers no choice to a company that keeps one currency', async () => {
    get.mockResolvedValue({ data: { base_currency: 'USD', currencies: ['USD'] } });
    const { result } = renderHook(() => useReportCurrency(7));

    await waitFor(() => expect(result.current.base).toBe('USD'));
    expect(result.current.hasChoice).toBe(false);
  });

  it('offers a choice once a second currency exists, starting on the company\'s own', async () => {
    get.mockResolvedValue({ data: { base_currency: 'USD', currencies: ['USD', 'YER'] } });
    const { result } = renderHook(() => useReportCurrency(7));

    await waitFor(() => expect(result.current.hasChoice).toBe(true));
    expect(result.current.available).toEqual(['USD', 'YER']);
    expect(result.current.selected).toBe('USD');
  });

  it('does not change what a report is fetched with just because the list loaded', async () => {
    // Setting `currency` to the base on load would change a dependency of every
    // report fetch and load the same report twice -- the double fetch [D5]
    // removed from the assistant. It stays null, which the server reads as the
    // company's own, until someone actually picks.
    get.mockResolvedValue({ data: { base_currency: 'USD', currencies: ['USD', 'YER'] } });
    const { result } = renderHook(() => useReportCurrency(7));

    await waitFor(() => expect(result.current.base).toBe('USD'));
    expect(result.current.currency).toBeNull();
  });

  it('still leaves the page usable when the list cannot be loaded', async () => {
    get.mockRejectedValue(new Error('down'));
    const { result } = renderHook(() => useReportCurrency(7));

    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(result.current.hasChoice).toBe(false);
    // Null means the company's own to every report, so figures stay correct.
    expect(result.current.currency).toBeNull();
  });
});

describe('ReportCurrencyField', () => {
  it('has no "all currencies" option, because that total is the bug', () => {
    render(
      <I18nProvider>
        <ReportCurrencyField value="USD" options={['USD', 'YER']} onChange={vi.fn()} />
      </I18nProvider>,
    );
    const options = screen.getAllByRole('option').map((o) => o.textContent);
    expect(options).toEqual(['USD', 'YER']);
  });
});

describe('opening an account in another currency', () => {
  const PARENT: Account = {
    id: 10, company_id: 1, code: '1000', name: 'Assets', account_type: 'asset',
    account_subtype: null, currency: 'USD', parent_id: null, description: null,
    is_active: true, is_system: true,
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  };

  it('sends the chosen currency', async () => {
    const onCreate = vi.fn().mockResolvedValue(PARENT);
    render(
      <I18nProvider>
        <NewAccountModal isOpen onClose={vi.fn()} accounts={[PARENT]}
          onCreate={onCreate} onCreated={vi.fn()} />
      </I18nProvider>,
    );

    fireEvent.change(screen.getByLabelText(en.accountsPage.code), { target: { value: '1101' } });
    fireEvent.change(screen.getByLabelText(en.accountsPage.name), { target: { value: 'صندوق ريال' } });
    fireEvent.change(screen.getByLabelText(en.accountsPage.currency), { target: { value: 'YER' } });
    fireEvent.click(screen.getByRole('button', { name: en.accountsPage.createAccount }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    expect(onCreate.mock.calls[0][0]).toMatchObject({ currency: 'YER' });
  });

  it('warns that the currency is permanent before it is chosen', () => {
    render(
      <I18nProvider>
        <NewAccountModal isOpen onClose={vi.fn()} accounts={[PARENT]}
          onCreate={vi.fn()} onCreated={vi.fn()} />
      </I18nProvider>,
    );
    // The server ignores a currency change after creation, so the form has to
    // say so up front rather than let someone find out from their figures.
    expect(screen.getByText(en.accountsPage.currencyHelp)).toBeInTheDocument();
  });
});
