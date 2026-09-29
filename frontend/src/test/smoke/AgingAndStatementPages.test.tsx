import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AgingReportsPage from '../../features/reports/aging/AgingReportsPage';
import PartnerStatementModal from '../../features/partners/PartnerStatementModal';
import { PageMetaContext } from '../../components/layout/pageMeta';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';
import type { Partner } from '../../api/types';

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn().mockImplementation((url: string) => {
      if (url.includes('/reports/currencies')) {
        return Promise.resolve({
          data: {
            base_currency: 'USD',
            currencies: ['USD', 'EUR'],
          },
        });
      }
      if (url.includes('/reports/ar-aging')) {
        return Promise.resolve({
          data: {
            company_id: 1,
            report_type: 'ar',
            as_of_date: '2026-09-19',
            currency: 'USD',
            items: [
              {
                partner_id: 1,
                partner_code: 'CUST-001',
                partner_name: 'Customer Alpha',
                invoice_id: 101,
                invoice_no: 'INV-1001',
                invoice_date: '2026-08-01',
                due_date: '2026-08-31',
                original_amount: '1000.00',
                paid_amount: '400.00',
                outstanding_amount: '600.00',
                days_overdue: 19,
                bucket: '1-30',
                currency: 'USD',
              },
            ],
            totals: {
              total_current: '0.00',
              total_1_30: '600.00',
              total_31_60: '0.00',
              total_61_90: '0.00',
              total_91_120: '0.00',
              total_120_plus: '0.00',
              total_outstanding: '600.00',
            },
          },
        });
      }
      if (url.includes('/partners/1/statement')) {
        return Promise.resolve({
          data: {
            company_id: 1,
            partner_id: 1,
            partner_name: 'Customer Alpha',
            partner_code: 'CUST-001',
            partner_type: 'customer',
            currency: 'USD',
            date_from: '2026-08-01',
            date_to: '2026-09-19',
            opening_balance: '1000.00',
            transactions: [
              {
                date: '2026-08-15',
                type: 'payment',
                document_no: 'PAY-201',
                reference: 'Wire-Ref',
                description: 'Customer Receipt',
                debit: '0.00',
                credit: '400.00',
                running_balance: '600.00',
              },
            ],
            closing_balance: '600.00',
            total_debit: '0.00',
            total_credit: '400.00',
          },
        });
      }
      if (url.includes('/partners')) {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 1,
                company_id: 1,
                name: 'Customer Alpha',
                code: 'CUST-001',
                is_customer: true,
                is_vendor: false,
                currency: 'USD',
                is_active: true,
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
  }),
}));

describe('Phase 73: Aging Reports & Partner Statement UI', () => {
  it('renders AgingReportsPage with AR/AP tabs and summary cards', async () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <PageMetaContext.Provider value={{ meta: {}, setMeta: vi.fn() }}>
            <AgingReportsPage />
          </PageMetaContext.Provider>
        </I18nProvider>
      </MemoryRouter>
    );

    // Verify Tab headers
    expect(screen.getByText(en.agingReports.tabAr)).toBeDefined();
    expect(screen.getByText(en.agingReports.tabAp)).toBeDefined();

    // Verify invoice from mock appears after render
    expect(await screen.findByText('INV-1001')).toBeDefined();
    expect(screen.getByText('Customer Alpha')).toBeDefined();
    expect(screen.getAllByText('600.00').length).toBeGreaterThan(0);
  });

  it('renders PartnerStatementModal with opening balance, transactions, and closing balance', async () => {
    const mockPartner: Partner = {
      id: 1,
      company_id: 1,
      name: 'Customer Alpha',
      code: 'CUST-001',
      is_customer: true,
      is_vendor: false,
      currency: 'USD',
      email: 'alpha@test.com',
      phone: null,
      tax_id: null,
      address: null,
      receivable_account_id: 2,
      payable_account_id: null,
      is_active: true,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    };

    render(
      <I18nProvider>
        <PartnerStatementModal
          isOpen={true}
          onClose={vi.fn()}
          companyId={1}
          partner={mockPartner}
        />
      </I18nProvider>
    );

    // Verify modal title and partner name
    expect(screen.getByText(new RegExp(mockPartner.name))).toBeDefined();

    // Verify statement data loads
    expect(await screen.findByText('PAY-201')).toBeDefined();
    expect(screen.getAllByText(/600\.00/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(en.partnerStatement.openingBalance).length).toBeGreaterThan(0);
    expect(screen.getAllByText(en.partnerStatement.closingBalance).length).toBeGreaterThan(0);
  });
});
