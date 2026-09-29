import { useState, useEffect, useCallback } from 'react';
import {
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  ArrowDownLeft,
  ArrowUpRight,
} from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import { useI18n } from '../../i18n';
import apiClient from '../../api/client';
import type { Payment, PaymentType, PaginatedResponse, CompanyUserRole } from '../../api/types';
import NewPaymentModal from './NewPaymentModal';

export default function PaymentsPage() {
  const { t } = useI18n();

  return (
    <PageLayout
      pageTitle={t.paymentsPage.pageTitle}
      pageSubtitle={t.paymentsPage.pageSubtitle}
      activePath="/payments"
    >
      {({ selectedCompanyId, companiesLoading, userRole }) => (
        <PaymentsContent
          companyId={selectedCompanyId}
          companiesLoading={companiesLoading}
          userRole={userRole}
        />
      )}
    </PageLayout>
  );
}

interface PaymentsContentProps {
  companyId: number | null;
  companiesLoading: boolean;
  userRole: CompanyUserRole | null;
}

function PaymentsContent({ companyId, companiesLoading }: PaymentsContentProps) {
  const { t } = useI18n();

  const [payments, setPayments] = useState<Payment[]>([]);
  const [activeTab, setActiveTab] = useState<'all' | 'customer_receipt' | 'vendor_payment'>('all');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState<PaymentType>('customer_receipt');

  // Action states
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  const fetchPayments = useCallback(() => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    let url = `/payments?company_id=${companyId}&limit=100`;
    if (activeTab !== 'all') {
      url += `&payment_type=${activeTab}`;
    }
    if (statusFilter) {
      url += `&status=${statusFilter}`;
    }
    if (search.trim()) {
      url += `&search=${encodeURIComponent(search.trim())}`;
    }

    apiClient
      .get<PaginatedResponse<Payment>>(url)
      .then((res) => setPayments(res.data.items || []))
      .catch((err) => {
        setError(err?.response?.data?.detail || 'Failed to load payments.');
      })
      .finally(() => setIsLoading(false));
  }, [companyId, activeTab, statusFilter, search]);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  const handlePost = async (id: number) => {
    setActionLoadingId(id);
    setError(null);
    try {
      await apiClient.post(`/payments/${id}/post`);
      setSuccessToast(t.paymentsPage.paymentPosted);
      fetchPayments();
    } catch (err: any) {
      setError(
        err?.response?.data?.detail || 'Failed to post payment to ledger.'
      );
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleVoid = async (id: number) => {
    if (!window.confirm('Are you sure you want to void this payment?')) return;

    setActionLoadingId(id);
    setError(null);
    try {
      await apiClient.post(`/payments/${id}/void`);
      setSuccessToast(t.paymentsPage.paymentVoided);
      fetchPayments();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to void payment.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'posted':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            {t.paymentsPage.statusPosted}
          </span>
        );
      case 'void':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3 h-3" />
            {t.paymentsPage.statusVoid}
          </span>
        );
      case 'draft':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertCircle className="w-3 h-3" />
            {t.paymentsPage.statusDraft}
          </span>
        );
    }
  };

  if (companiesLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-muted-foreground">
        <Loader2 className="w-8 h-8 animate-spin mb-2" />
        <p className="text-sm">{t.common.loading}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex items-center justify-end gap-3">
        <button
          onClick={() => {
            setModalType('customer_receipt');
            setIsModalOpen(true);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
        >
          <ArrowDownLeft className="w-4 h-4" />
          {t.paymentsPage.newReceipt}
        </button>
        <button
          onClick={() => {
            setModalType('vendor_payment');
            setIsModalOpen(true);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium transition-colors shadow-sm"
        >
          <ArrowUpRight className="w-4 h-4" />
          {t.paymentsPage.newPayment}
        </button>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {successToast && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            {successToast}
          </div>
          <button
            onClick={() => setSuccessToast(null)}
            className="text-xs hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Toolbar & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        {/* Tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeTab === 'all'
                ? 'bg-surface-hover text-foreground font-semibold'
                : 'text-muted-foreground hover:bg-surface'
            }`}
          >
            {t.paymentsPage.tabAll}
          </button>
          <button
            onClick={() => setActiveTab('customer_receipt')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeTab === 'customer_receipt'
                ? 'bg-emerald-500/10 text-emerald-400 font-semibold'
                : 'text-muted-foreground hover:bg-surface'
            }`}
          >
            {t.paymentsPage.tabReceipts}
          </button>
          <button
            onClick={() => setActiveTab('vendor_payment')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeTab === 'vendor_payment'
                ? 'bg-primary/10 text-primary font-semibold'
                : 'text-muted-foreground hover:bg-surface'
            }`}
          >
            {t.paymentsPage.tabPayments}
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t.paymentsPage.searchPlaceholder}
              className="bg-surface border border-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary w-56"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-surface border border-border rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">All Statuses</option>
            <option value="draft">{t.paymentsPage.statusDraft}</option>
            <option value="posted">{t.paymentsPage.statusPosted}</option>
            <option value="void">{t.paymentsPage.statusVoid}</option>
          </select>
        </div>
      </div>

      {/* Content Table */}
      {isLoading ? (
        <div className="py-24 flex flex-col items-center justify-center text-muted-foreground">
          <Loader2 className="w-8 h-8 animate-spin mb-2" />
          <p className="text-sm">Loading transactions...</p>
        </div>
      ) : payments.length === 0 ? (
        <div className="border border-border rounded-2xl p-12 text-center bg-surface/30">
          <p className="text-base font-semibold text-foreground">
            {t.paymentsPage.noPaymentsTitle}
          </p>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
            {t.paymentsPage.noPaymentsDescription}
          </p>
        </div>
      ) : (
        <div className="border border-border rounded-xl overflow-hidden bg-surface/40">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-surface/80 text-muted-foreground border-b border-border">
                <tr>
                  <th className="py-3 px-4">#</th>
                  <th className="py-3 px-4">{t.paymentsPage.paymentType}</th>
                  <th className="py-3 px-4">{t.paymentsPage.partner}</th>
                  <th className="py-3 px-4">{t.paymentsPage.date}</th>
                  <th className="py-3 px-4">{t.paymentsPage.reference}</th>
                  <th className="py-3 px-4 text-right">{t.paymentsPage.amount}</th>
                  <th className="py-3 px-4">{t.paymentsPage.bankAccount}</th>
                  <th className="py-3 px-4">{t.paymentsPage.status}</th>
                  <th className="py-3 px-4 text-right">{t.paymentsPage.actions}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {payments.map((p) => {
                  const isRec = p.payment_type === 'customer_receipt';
                  const isActing = actionLoadingId === p.id;
                  return (
                    <tr key={p.id} className="hover:bg-surface/60 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-foreground">
                        #{p.id}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium ${
                            isRec
                              ? 'bg-emerald-500/10 text-emerald-400'
                              : 'bg-blue-500/10 text-blue-400'
                          }`}
                        >
                          {isRec ? (
                            <ArrowDownLeft className="w-3 h-3" />
                          ) : (
                            <ArrowUpRight className="w-3 h-3" />
                          )}
                          {isRec
                            ? t.paymentsPage.customerReceipt
                            : t.paymentsPage.vendorPayment}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-medium text-foreground">
                        {p.partner_name || `Partner #${p.partner_id}`}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {p.payment_date}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {p.reference || p.memo || '—'}
                      </td>
                      <td className="py-3 px-4 text-right font-semibold text-foreground">
                        {parseFloat(p.amount).toFixed(2)} {p.currency_code}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {p.bank_account_name || '—'}
                      </td>
                      <td className="py-3 px-4">{getStatusBadge(p.status)}</td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {p.status === 'draft' && (
                            <button
                              onClick={() => handlePost(p.id)}
                              disabled={isActing}
                              className="px-2.5 py-1 text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20 rounded transition-colors disabled:opacity-50"
                            >
                              {isActing ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                t.paymentsPage.postToLedger
                              )}
                            </button>
                          )}
                          {p.status !== 'void' && (
                            <button
                              onClick={() => handleVoid(p.id)}
                              disabled={isActing}
                              className="px-2.5 py-1 text-xs font-medium text-rose-400 hover:bg-rose-500/10 rounded transition-colors disabled:opacity-50"
                            >
                              {isActing ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                t.paymentsPage.voidPayment
                              )}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {isModalOpen && companyId && (
        <NewPaymentModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          companyId={companyId}
          initialType={modalType}
          onCreated={() => {
            setSuccessToast(t.paymentsPage.paymentCreated);
            fetchPayments();
          }}
        />
      )}
    </div>
  );
}
