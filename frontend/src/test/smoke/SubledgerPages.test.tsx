import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PartnersPage from '../../features/partners/PartnersPage';
import InvoicesPage from '../../features/invoices/InvoicesPage';
import { PageMetaContext } from '../../components/layout/pageMeta';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn().mockImplementation((url: string) => {
      if (url.includes('/partners')) {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                company_id: 1,
                name: 'Al-Amal Trading',
                code: 'CUST-001',
                is_customer: true,
                is_vendor: false,
                currency: 'USD',
                email: 'info@alamal.com',
                phone: '+967 770 123 456',
                tax_id: '123456789',
                address: 'Sanaa, Yemen',
                receivable_account_id: null,
                payable_account_id: null,
                is_active: true,
                created_at: '2026-09-19T10:00:00Z',
                updated_at: '2026-09-19T10:00:00Z',
              },
            ],
            total: 1,
            skip: 0,
            limit: 500,
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
                partner_name: 'Al-Amal Trading',
                invoice_type: 'out_invoice',
                invoice_no: 'INV-2026-001',
                reference: 'PO-100',
                issue_date: '2026-09-19',
                due_date: '2026-10-19',
                currency: 'USD',
                status: 'draft',
                subtotal: '1000.00',
                tax_amount: '0.00',
                total_amount: '1000.00',
                journal_entry_id: null,
                notes: 'Consulting',
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

describe('Subledger pages smoke tests', () => {
  it('renders PartnersPage with customers and toolbar', async () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <PageMetaContext.Provider value={{ meta: {}, setMeta: vi.fn() }}>
            <PartnersPage />
          </PageMetaContext.Provider>
        </I18nProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('Al-Amal Trading')).toBeInTheDocument();
    expect(screen.getByText('CUST-001')).toBeInTheDocument();
    expect(screen.getByText(en.partnersPage.addPartner)).toBeInTheDocument();
  });

  it('renders InvoicesPage with sales invoices', async () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <PageMetaContext.Provider value={{ meta: {}, setMeta: vi.fn() }}>
            <InvoicesPage invoiceType="out_invoice" />
          </PageMetaContext.Provider>
        </I18nProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('INV-2026-001')).toBeInTheDocument();
    expect(screen.getByText(en.invoicesPage.newInvoice)).toBeInTheDocument();
    expect(screen.getAllByText(en.invoicesPage.statusDraft).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(en.invoicesPage.postToLedger)).toBeInTheDocument();
  });
});
