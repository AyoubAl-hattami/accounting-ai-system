import { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Search,
  CheckCircle,
  XCircle,
  DollarSign,
  AlertCircle,
  Loader2,
  ArrowUpRight,
  ArrowDownLeft,
} from 'lucide-react';
import apiClient from '../../api/client';
import type {
  Refund,
  RefundType,
  RefundStatus,
  PaginatedResponse,
  CompanyUserRole,
} from '../../api/types';
import { useI18n } from '../../i18n';
import PageLayout from '../../components/layout/PageLayout';
import NewRefundModal from './NewRefundModal';

export default function RefundsPage() {
  const { t } = useI18n();

  return (
    <PageLayout
      pageTitle={t.refundsPage.pageTitle}
      pageSubtitle={t.refundsPage.pageSubtitle}
      activePath="/refunds"
    >
      {({ selectedCompanyId, companiesLoading, userRole }) => (
        <RefundsContent
          companyId={selectedCompanyId}
          companiesLoading={companiesLoading}
          userRole={userRole}
        />
      )}
    </PageLayout>
  );
}

interface RefundsContentProps {
  companyId: number | null;
  companiesLoading: boolean;
  userRole?: CompanyUserRole | null;
}

function RefundsContent({ companyId, companiesLoading }: RefundsContentProps) {
  const { t } = useI18n();

  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [activeTab, setActiveTab] = useState<'all' | RefundType>('all');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const [isNewModalOpen, setIsNewModalOpen] = useState<boolean>(false);
  const [newModalType, setNewModalType] = useState<RefundType>('customer_refund');
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  const fetchRefunds = useCallback(() => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    let url = `/refunds?company_id=${companyId}&limit=100`;
    if (activeTab !== 'all') {
      url += `&refund_type=${activeTab}`;
    }
    if (statusFilter) {
      url += `&status=${statusFilter}`;
    }
    if (search.trim()) {
      url += `&search=${encodeURIComponent(search.trim())}`;
    }

    apiClient
      .get<PaginatedResponse<Refund>>(url)
      .then((res: any) => setRefunds(res.data.items || []))
      .catch((err: any) => {
        setError(err?.response?.data?.detail || 'Failed to load refunds.');
      })
      .finally(() => setIsLoading(false));
  }, [companyId, activeTab, statusFilter, search]);

  useEffect(() => {
    fetchRefunds();
  }, [fetchRefunds]);

  const handlePost = async (id: number) => {
    setActionLoadingId(id);
    setError(null);
    try {
      await apiClient.post(`/refunds/${id}/post`);
      setSuccessToast(t.refundsPage.refundPosted);
      fetchRefunds();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to post refund to ledger.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleVoid = async (id: number) => {
    if (!window.confirm('Are you sure you want to void this refund?')) return;

    setActionLoadingId(id);
    setError(null);
    try {
      await apiClient.post(`/refunds/${id}/void`);
      setSuccessToast(t.refundsPage.refundVoided);
      fetchRefunds();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to void refund.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const getStatusBadge = (status: RefundStatus) => {
    switch (status) {
      case 'posted':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
            <CheckCircle className="w-3 h-3" />
            {t.refundsPage.statusPosted}
          </span>
        );
      case 'draft':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
            {t.refundsPage.statusDraft}
          </span>
        );
      case 'void':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400">
            <XCircle className="w-3 h-3" />
            {t.refundsPage.statusVoid}
          </span>
        );
      default:
        return null;
    }
  };

  if (companiesLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mb-2" />
        <p className="text-sm">{t.common.loading}</p>
      </div>
    );
  }

  if (!companyId) {
    return (
      <div className="p-8 text-center border border-dashed border-slate-300 dark:border-slate-700 rounded-2xl">
        <p className="text-slate-500">{t.common.noCompanySelected}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {successToast && (
        <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-xl flex items-center justify-between text-emerald-800 dark:text-emerald-200 text-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>{successToast}</span>
          </div>
          <button
            onClick={() => setSuccessToast(null)}
            className="text-xs font-semibold hover:underline"
          >
            {t.common.close}
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl flex items-center justify-between text-red-800 dark:text-red-200 text-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-xs font-semibold hover:underline"
          >
            {t.common.close}
          </button>
        </div>
      )}

      {/* Top Controls: Tabs, Search, Create Buttons */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Tabs */}
        <div className="flex items-center p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === 'all'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {t.refundsPage.tabAll}
          </button>
          <button
            onClick={() => setActiveTab('customer_refund')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === 'customer_refund'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {t.refundsPage.tabCustomerRefunds}
          </button>
          <button
            onClick={() => setActiveTab('vendor_refund')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === 'vendor_refund'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {t.refundsPage.tabVendorRefunds}
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setNewModalType('customer_refund');
              setIsNewModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            {t.refundsPage.newCustomerRefund}
          </button>
          <button
            onClick={() => {
              setNewModalType('vendor_refund');
              setIsNewModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            {t.refundsPage.newVendorRefund}
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t.refundsPage.searchPlaceholder}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="posted">Posted</option>
          <option value="void">Voided</option>
        </select>
      </div>

      {/* Refunds Table */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="py-24 flex flex-col items-center justify-center text-slate-500">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mb-2" />
            <p className="text-sm">{t.common.loading}</p>
          </div>
        ) : refunds.length === 0 ? (
          <div className="py-16 text-center">
            <DollarSign className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
            <h4 className="text-base font-semibold text-slate-800 dark:text-slate-200">
              {t.refundsPage.noRefundsTitle}
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto mt-1">
              {t.refundsPage.noRefundsDescription}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-600 dark:text-slate-300">
                  <th className="px-6 py-3.5">{t.refundsPage.date}</th>
                  <th className="px-6 py-3.5">{t.refundsPage.refundType}</th>
                  <th className="px-6 py-3.5">{t.refundsPage.partner}</th>
                  <th className="px-6 py-3.5">{t.refundsPage.bankCashAccount}</th>
                  <th className="px-6 py-3.5 text-right">{t.refundsPage.amount}</th>
                  <th className="px-6 py-3.5">{t.refundsPage.status}</th>
                  <th className="px-6 py-3.5 text-right">{t.refundsPage.actions}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {refunds.map((ref) => {
                  const isCust = ref.refund_type === 'customer_refund';
                  const isActionLoading = actionLoadingId === ref.id;

                  return (
                    <tr
                      key={ref.id}
                      className="hover:bg-slate-50/50 dark:hover:bg-slate-700/20 transition-colors"
                    >
                      <td className="px-6 py-4 font-medium text-slate-900 dark:text-white whitespace-nowrap">
                        {ref.refund_date}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            isCust
                              ? 'bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                              : 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                          }`}
                        >
                          {isCust ? (
                            <ArrowUpRight className="w-3 h-3 text-rose-500" />
                          ) : (
                            <ArrowDownLeft className="w-3 h-3 text-emerald-500" />
                          )}
                          {isCust
                            ? t.refundsPage.customerRefund
                            : t.refundsPage.vendorRefund}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-800 dark:text-slate-200 font-medium">
                        {ref.partner_name || `Partner #${ref.partner_id}`}
                        {ref.reference && (
                          <span className="block text-xs text-slate-400 font-normal">
                            Ref: {ref.reference}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-slate-600 dark:text-slate-400 text-xs">
                        {ref.bank_account_name || `Account #${ref.bank_or_cash_account_id}`}
                      </td>
                      <td className="px-6 py-4 text-right font-bold text-slate-900 dark:text-white whitespace-nowrap">
                        {Number(ref.amount).toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                        })}{' '}
                        {ref.currency_code}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(ref.status)}
                      </td>
                      <td className="px-6 py-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          {ref.status === 'draft' && (
                            <button
                              onClick={() => handlePost(ref.id)}
                              disabled={isActionLoading}
                              className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-300 transition-colors"
                            >
                              {isActionLoading ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                t.refundsPage.postToLedger
                              )}
                            </button>
                          )}
                          {ref.status !== 'void' && (
                            <button
                              onClick={() => handleVoid(ref.id)}
                              disabled={isActionLoading}
                              className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-rose-50 text-rose-700 hover:bg-rose-100 dark:bg-rose-900/30 dark:text-rose-300 transition-colors"
                            >
                              {t.refundsPage.voidRefund}
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
        )}
      </div>

      {/* New Refund Modal */}
      {isNewModalOpen && (
        <NewRefundModal
          companyId={companyId}
          refundType={newModalType}
          isOpen={isNewModalOpen}
          onClose={() => setIsNewModalOpen(false)}
          onSuccess={() => {
            setSuccessToast(t.refundsPage.refundCreated);
            fetchRefunds();
          }}
        />
      )}
    </div>
  );
}
