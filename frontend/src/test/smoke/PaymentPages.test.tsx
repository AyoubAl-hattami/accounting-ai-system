import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PaymentsPage from '../../features/payments/PaymentsPage';
import InvoicesPage from '../../features/invoices/InvoicesPage';
import { PageMetaContext } from '../../components/layout/pageMeta';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn().mockImplementation((url: string) => {
      if (url.includes('/payments')) {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                company_id: 1,
                partner_id: 1,
                partner_name: 'Customer Alpha',
                payment_type: 'customer_receipt',
                currency_code: 'USD',
                amount: '400.00',
                payment_date: '2026-09-19',
                bank_or_cash_account_id: 10,
                bank_account_name: 'Main Bank',
                receivable_or_payable_account_id: 11,
                receivable_or_payable_account_name: 'Accounts Receivable',
                status: 'draft',
                reference: 'Wire-001',
                memo: 'Advance',
                journal_entry_id: null,
                allocations: [],
                allocated_amount: '0.00',
                unallocated_amount: '400.00',
              },
            ],
            total: 1,
            skip: 0,
            limit: 100,
          },
        });
      }
      if (url.includes('/invoices')) {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                company_id: 1,
                partner_id: 1,
                partner_name: 'Customer Alpha',
                invoice_type: 'out_invoice',
                invoice_no: 'INV-1001',
                reference: 'PO-100',
                issue_date: '2026-09-19',
                due_date: '2026-10-19',
                currency: 'USD',
                status: 'posted',
                subtotal: '1000.00',
                tax_amount: '0.00',
                total_amount: '1000.00',
                paid_amount: '400.00',
                residual_amount: '600.00',
                payment_status: 'partially_paid',
                journal_entry_id: 1,
                notes: 'Services',
                created_at: '2026-09-19T10:00:00Z',
                updated_at: '2026-09-19T10:00:00Z',
                lines: [],
              },
            ],
            total: 1,
            skip: 0,
            limit: 500,
          },
        });
      }
      return Promise.resolve({ data: { items: [], total: 0 } });
    }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

vi.mock('../../features/companies/useCompanies', () => ({
  useCompanies: () => ({
    companies: [{ id: 1, name: 'Acme Inc', base_currency: 'USD', is_active: true }],
    selectedCompanyId: 1,
    selectedCompany: { id: 1, name: 'Acme Inc', base_currency: 'USD', is_active: true },
    isLoading: false,
    error: null,
    selectCompany: vi.fn(),
  }),
}));

vi.mock('../../auth/useCompanyRole', () => ({
  useCompanyRole: () => ({
    role: 'admin',
    isLoading: false,
    error: null,
  }),
}));

describe('Payment & Settlement pages smoke tests', () => {
  it('renders PaymentsPage with customer receipt and action buttons', async () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <PageMetaContext.Provider value={{ meta: {}, setMeta: vi.fn() }}>
            <PaymentsPage />
          </PageMetaContext.Provider>
        </I18nProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('Customer Alpha')).toBeInTheDocument();
    expect(screen.getByText('Wire-001')).toBeInTheDocument();
    expect(screen.getByText(en.paymentsPage.newReceipt)).toBeInTheDocument();
    expect(screen.getByText(en.paymentsPage.newPayment)).toBeInTheDocument();
    expect(screen.getByText(en.paymentsPage.postToLedger)).toBeInTheDocument();
  });

  it('renders InvoicesPage with payment status badges and residual amounts', async () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <PageMetaContext.Provider value={{ meta: {}, setMeta: vi.fn() }}>
            <InvoicesPage invoiceType="out_invoice" />
          </PageMetaContext.Provider>
        </I18nProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('INV-1001')).toBeInTheDocument();
    expect(screen.getByText('400.00')).toBeInTheDocument(); // Paid amount
    expect(screen.getByText('600.00')).toBeInTheDocument(); // Due amount
    expect(screen.getByText(en.invoicesPage.statusPartiallyPaid)).toBeInTheDocument();
  });
});
