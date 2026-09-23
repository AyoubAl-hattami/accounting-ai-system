import { useState, useEffect, useMemo } from 'react';
import {
  Plus,
  Search,
  FileText,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  ArrowUpRight,
} from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import { useI18n } from '../../i18n';
import apiClient from '../../api/client';
import type {
  Invoice,
  InvoiceStatus,
  InvoiceType,
  PaginatedResponse,
  CompanyUserRole,
} from '../../api/types';
import NewInvoiceModal from './NewInvoiceModal';

interface InvoicesPageProps {
  invoiceType?: InvoiceType;
}

export default function InvoicesPage({ invoiceType = 'out_invoice' }: InvoicesPageProps) {
  const { t } = useI18n();

  const isSales = invoiceType === 'out_invoice';
  const pageTitle = isSales
    ? t.invoicesPage.pageTitle
    : t.invoicesPage.billsPageTitle;
  const pageSubtitle = isSales
    ? t.invoicesPage.pageSubtitle
    : t.invoicesPage.billsPageSubtitle;
  const activePath = isSales ? '/invoices' : '/bills';

  return (
    <PageLayout
      pageTitle={pageTitle}
      pageSubtitle={pageSubtitle}
      activePath={activePath}
    >
      {({ selectedCompanyId, companiesLoading, userRole }) => (
        <InvoicesContent
          companyId={selectedCompanyId}
          companiesLoading={companiesLoading}
          userRole={userRole}
          invoiceType={invoiceType}
          isSales={isSales}
        />
      )}
    </PageLayout>
  );
}

interface InvoicesContentProps {
  companyId: number | null;
  companiesLoading: boolean;
  userRole: CompanyUserRole | null;
  invoiceType: InvoiceType;
  isSales: boolean;
}

function InvoicesContent({
  companyId,
  companiesLoading,
  invoiceType,
  isSales,
}: InvoicesContentProps) {
  const { t } = useI18n();

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [postingId, setPostingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchInvoices = async () => {
    if (!companyId) return;
    setLoading(true);
    setActionError(null);
    try {
      const res = await apiClient.get<PaginatedResponse<Invoice>>(
        `/invoices?company_id=${companyId}&invoice_type=${invoiceType}&limit=500`
      );
      setInvoices(res.data.items);
    } catch {
      setInvoices([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, [companyId, invoiceType]);

  const filteredInvoices = useMemo(() => {
    return invoices.filter((inv) => {
      if (statusFilter !== 'all' && inv.status !== statusFilter) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchNo = inv.invoice_no.toLowerCase().includes(q);
        const matchRef = inv.reference?.toLowerCase().includes(q) ?? false;
        const matchPartner = inv.partner_name?.toLowerCase().includes(q) ?? false;
        return matchNo || matchRef || matchPartner;
      }
      return true;
    });
  }, [invoices, statusFilter, search]);

  const handlePost = async (invoiceId: number) => {
    setPostingId(invoiceId);
    setActionError(null);
    try {
      await apiClient.post(`/invoices/${invoiceId}/post`, {});
      await fetchInvoices();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to post invoice to ledger.';
      setActionError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setPostingId(null);
    }
  };

  const handleVoid = async (invoiceId: number) => {
    if (!window.confirm('Are you sure you want to void this document?')) return;
    setActionError(null);
    try {
      await apiClient.post(`/invoices/${invoiceId}/void`, {});
      await fetchInvoices();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to void invoice.';
      setActionError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  };

  const getStatusBadge = (status: InvoiceStatus) => {
    switch (status) {
      case 'posted':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {t.invoicesPage.statusPosted}
          </span>
        );
      case 'draft':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
            <Clock className="h-3.5 w-3.5" />
            {t.invoicesPage.statusDraft}
          </span>
        );
      case 'void':
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
            <XCircle className="h-3.5 w-3.5" />
            {t.invoicesPage.statusVoid}
          </span>
        );
      default:
        return <span className="text-xs">{status}</span>;
    }
  };

  const getPaymentStatusBadge = (inv: Invoice) => {
    if (inv.status === 'draft' || inv.status === 'void' || inv.status === 'cancelled') {
      return <span className="text-xs text-neutral-400">—</span>;
    }
    const pStatus =
      inv.payment_status ||
      (parseFloat(String(inv.paid_amount || 0)) >= parseFloat(inv.total_amount)
        ? 'paid'
        : parseFloat(String(inv.paid_amount || 0)) > 0
        ? 'partially_paid'
        : 'unpaid');
    switch (pStatus) {
      case 'paid':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {t.invoicesPage.statusPaid}
          </span>
        );
      case 'partially_paid':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
            <Clock className="h-3.5 w-3.5" />
            {t.invoicesPage.statusPartiallyPaid}
          </span>
        );
      case 'unpaid':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-400">
            {t.invoicesPage.statusUnpaid}
          </span>
        );
    }
  };

  if (companiesLoading) {
    return <div className="p-8 text-center text-sm text-neutral-500">{t.common.loading}</div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header Actions */}
      <div className="flex justify-end">
        <button
          onClick={() => setIsNewModalOpen(true)}
          className="btn btn-primary inline-flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          <span>{isSales ? t.invoicesPage.newInvoice : t.invoicesPage.newBill}</span>
        </button>
      </div>

      {actionError && (
        <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-md text-sm text-red-600 dark:text-red-400 flex items-center justify-between">
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} className="text-xs underline">
            {t.common.close}
          </button>
        </div>
      )}

      {/* Toolbar: Filters & Search */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white dark:bg-neutral-950 p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm">
        {/* Status filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
          {(['all', 'draft', 'posted', 'void'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg capitalize transition-colors ${
                statusFilter === st
                  ? 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900'
                  : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-800'
              }`}
            >
              {st === 'all'
                ? t.journals.allStatuses
                : st === 'draft'
                ? t.invoicesPage.statusDraft
                : st === 'posted'
                ? t.invoicesPage.statusPosted
                : t.invoicesPage.statusVoid}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t.invoicesPage.searchPlaceholder}
            className="input pl-9 w-full text-sm"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-neutral-950 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-neutral-500">
            {t.common.loading}
          </div>
        ) : filteredInvoices.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="h-10 w-10 mx-auto text-neutral-300 dark:text-neutral-700 mb-3" />
            <h3 className="text-base font-semibold text-neutral-900 dark:text-white">
              {isSales
                ? t.invoicesPage.noInvoicesTitle
                : t.invoicesPage.noBillsTitle}
            </h3>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1 max-w-sm mx-auto">
              {isSales
                ? t.invoicesPage.noInvoicesDescription
                : t.invoicesPage.noBillsDescription}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50 text-neutral-500 font-medium text-xs uppercase tracking-wider">
                  <th className="py-3 px-4">{t.invoicesPage.invoiceNo}</th>
                  <th className="py-3 px-4">
                    {isSales ? t.invoicesPage.customer : t.invoicesPage.vendor}
                  </th>
                  <th className="py-3 px-4">{t.invoicesPage.issueDate}</th>
                  <th className="py-3 px-4">{t.invoicesPage.dueDate}</th>
                  <th className="py-3 px-4 text-right">{t.invoicesPage.totalAmount}</th>
                  <th className="py-3 px-4 text-right">{t.invoicesPage.paidAmount}</th>
                  <th className="py-3 px-4 text-right">{t.invoicesPage.residualAmount}</th>
                  <th className="py-3 px-4 text-center">{t.invoicesPage.status}</th>
                  <th className="py-3 px-4 text-center">{t.invoicesPage.paymentStatus}</th>
                  <th className="py-3 px-4 text-right">{t.invoicesPage.actions}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                {filteredInvoices.map((inv) => {
                  const paid = parseFloat(String(inv.paid_amount || 0));
                  const due = parseFloat(String(inv.residual_amount ?? inv.total_amount));
                  return (
                    <tr
                      key={inv.id}
                      className="hover:bg-neutral-50/50 dark:hover:bg-neutral-900/50 transition-colors"
                    >
                      <td className="py-3.5 px-4 font-mono text-xs font-semibold text-neutral-900 dark:text-white">
                        <div>{inv.invoice_no}</div>
                        {inv.reference && (
                          <div className="text-neutral-400 text-[11px] font-normal">
                            Ref: {inv.reference}
                          </div>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-neutral-800 dark:text-neutral-200">
                        {inv.partner_name || `Partner #${inv.partner_id}`}
                      </td>
                      <td className="py-3.5 px-4 text-neutral-600 dark:text-neutral-400 font-mono text-xs">
                        {inv.issue_date}
                      </td>
                      <td className="py-3.5 px-4 text-neutral-600 dark:text-neutral-400 font-mono text-xs">
                        {inv.due_date}
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-bold text-neutral-900 dark:text-white">
                        {parseFloat(inv.total_amount).toFixed(2)}{' '}
                        <span className="text-xs font-normal text-neutral-500">
                          {inv.currency}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono text-xs text-neutral-600 dark:text-neutral-400">
                        {paid.toFixed(2)}
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-semibold text-neutral-900 dark:text-white">
                        {due.toFixed(2)}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {getStatusBadge(inv.status)}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {getPaymentStatusBadge(inv)}
                      </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {inv.status === 'draft' && (
                          <button
                            onClick={() => handlePost(inv.id)}
                            disabled={postingId === inv.id}
                            className="btn btn-primary text-xs py-1 px-2.5 inline-flex items-center gap-1.5"
                          >
                            {postingId === inv.id ? (
                              <>
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                <span>{t.invoicesPage.posting}</span>
                              </>
                            ) : (
                              <>
                                <ArrowUpRight className="h-3.5 w-3.5" />
                                <span>{t.invoicesPage.postToLedger}</span>
                              </>
                            )}
                          </button>
                        )}

                        {inv.status === 'draft' && (
                          <button
                            onClick={() => handleVoid(inv.id)}
                            className="btn btn-secondary text-xs py-1 px-2 text-red-600 hover:text-red-700 dark:text-red-400"
                          >
                            {t.invoicesPage.voidInvoice}
                          </button>
                        )}

                        {inv.journal_entry_id && (
                          <span className="text-[11px] font-mono text-neutral-400">
                            GL #{inv.journal_entry_id}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {companyId && (
        <NewInvoiceModal
          isOpen={isNewModalOpen}
          onClose={() => setIsNewModalOpen(false)}
          companyId={companyId}
          invoiceType={invoiceType}
          onCreated={() => fetchInvoices()}
        />
      )}
    </div>
  );
}
