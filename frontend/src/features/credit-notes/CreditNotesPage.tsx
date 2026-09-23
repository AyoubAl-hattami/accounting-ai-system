import { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Plus,
  Search,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Layers,
} from 'lucide-react';
import apiClient from '../../api/client';
import type {
  CreditNote,
  CreditNoteType,
  CreditNoteStatus,
  PaginatedResponse,
  CompanyUserRole,
} from '../../api/types';
import { useI18n } from '../../i18n';
import PageLayout from '../../components/layout/PageLayout';
import NewCreditNoteModal from './NewCreditNoteModal';
import AllocateCreditNoteModal from './AllocateCreditNoteModal';

export default function CreditNotesPage() {
  const { t } = useI18n();

  return (
    <PageLayout
      pageTitle={t.creditNotesPage.pageTitle}
      pageSubtitle={t.creditNotesPage.pageSubtitle}
      activePath="/credit-notes"
    >
      {({ selectedCompanyId, companiesLoading, userRole }) => (
        <CreditNotesContent
          companyId={selectedCompanyId}
          companiesLoading={companiesLoading}
          userRole={userRole}
        />
      )}
    </PageLayout>
  );
}

interface CreditNotesContentProps {
  companyId: number | null;
  companiesLoading: boolean;
  userRole?: CompanyUserRole | null;
}

function CreditNotesContent({ companyId, companiesLoading }: CreditNotesContentProps) {
  const { t } = useI18n();

  const [notes, setNotes] = useState<CreditNote[]>([]);
  const [activeTab, setActiveTab] = useState<'all' | CreditNoteType>('all');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const [isNewModalOpen, setIsNewModalOpen] = useState<boolean>(false);
  const [newModalType, setNewModalType] = useState<CreditNoteType>('customer_credit_note');
  const [allocatingNote, setAllocatingNote] = useState<CreditNote | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  const fetchNotes = useCallback(() => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    let url = `/credit-notes?company_id=${companyId}&limit=100`;
    if (activeTab !== 'all') {
      url += `&note_type=${activeTab}`;
    }
    if (statusFilter) {
      url += `&status=${statusFilter}`;
    }
    if (search.trim()) {
      url += `&search=${encodeURIComponent(search.trim())}`;
    }

    apiClient
      .get<PaginatedResponse<CreditNote>>(url)
      .then((res: any) => setNotes(res.data.items || []))
      .catch((err: any) => {
        setError(err?.response?.data?.detail || 'Failed to load credit notes.');
      })
      .finally(() => setIsLoading(false));
  }, [companyId, activeTab, statusFilter, search]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const handlePost = async (id: number) => {
    setActionLoadingId(id);
    setError(null);
    try {
      await apiClient.post(`/credit-notes/${id}/post`);
      setSuccessToast(t.creditNotesPage.notePosted);
      fetchNotes();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to post note to ledger.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleVoid = async (id: number) => {
    if (!window.confirm('Are you sure you want to void this note?')) return;

    setActionLoadingId(id);
    setError(null);
    try {
      await apiClient.post(`/credit-notes/${id}/void`);
      setSuccessToast(t.creditNotesPage.noteVoided);
      fetchNotes();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to void note.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const openCreateModal = (type: CreditNoteType) => {
    setNewModalType(type);
    setIsNewModalOpen(true);
  };

  const renderStatusBadge = (status: CreditNoteStatus) => {
    switch (status) {
      case 'posted':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
            <CheckCircle className="w-3 h-3 mr-1" />
            {t.creditNotesPage.statusPosted}
          </span>
        );
      case 'draft':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
            {t.creditNotesPage.statusDraft}
          </span>
        );
      case 'void':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400">
            <XCircle className="w-3 h-3 mr-1" />
            {t.creditNotesPage.statusVoid}
          </span>
        );
      default:
        return null;
    }
  };

  if (companiesLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {successToast && (
        <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-xl text-emerald-700 dark:text-emerald-300 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle className="w-5 h-5 text-emerald-600" />
            <span>{successToast}</span>
          </div>
          <button
            onClick={() => setSuccessToast(null)}
            className="text-emerald-600 hover:text-emerald-800 text-sm font-semibold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl text-rose-700 dark:text-rose-300 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-rose-600" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-rose-600 hover:text-rose-800 text-sm font-semibold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Action Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Tabs */}
        <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              activeTab === 'all'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {t.creditNotesPage.tabAll}
          </button>
          <button
            onClick={() => setActiveTab('customer_credit_note')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              activeTab === 'customer_credit_note'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {t.creditNotesPage.tabCustomerCreditNotes}
          </button>
          <button
            onClick={() => setActiveTab('vendor_debit_note')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              activeTab === 'vendor_debit_note'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {t.creditNotesPage.tabVendorDebitNotes}
          </button>
        </div>

        {/* Buttons */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => openCreateModal('customer_credit_note')}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            <Plus className="w-4 h-4 mr-2" />
            {t.creditNotesPage.newCreditNote}
          </button>
          <button
            onClick={() => openCreateModal('vendor_debit_note')}
            className="inline-flex items-center px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-xl shadow-sm text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 focus:outline-none"
          >
            <Plus className="w-4 h-4 mr-2" />
            {t.creditNotesPage.newDebitNote}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-center gap-4 bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder={t.creditNotesPage.searchPlaceholder}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-full sm:w-48 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="posted">Posted</option>
          <option value="void">Void</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
          </div>
        ) : notes.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="mx-auto h-12 w-12 text-slate-400" />
            <h3 className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">
              {t.creditNotesPage.noNotesTitle}
            </h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {t.creditNotesPage.noNotesDescription}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
              <thead className="bg-slate-50 dark:bg-slate-900/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {t.creditNotesPage.date}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {t.creditNotesPage.noteType}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    #
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {t.creditNotesPage.partner}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {t.creditNotesPage.totalAmount}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {t.creditNotesPage.allocatedAmount}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {t.creditNotesPage.unallocatedAmount}
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {t.creditNotesPage.status}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {t.creditNotesPage.actions}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {notes.map((cn) => {
                  const isActionLoading = actionLoadingId === cn.id;
                  const isCustomer = cn.note_type === 'customer_credit_note';
                  return (
                    <tr
                      key={cn.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300">
                        {cn.issue_date}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            isCustomer
                              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
                              : 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
                          }`}
                        >
                          {isCustomer
                            ? t.creditNotesPage.customerCreditNote
                            : t.creditNotesPage.vendorDebitNote}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-900 dark:text-white">
                        {cn.credit_note_no}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 dark:text-white">
                        {cn.partner_name || `Partner #${cn.partner_id}`}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-slate-900 dark:text-white">
                        {cn.currency} {Number(cn.total_amount).toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-emerald-600 dark:text-emerald-400 font-medium">
                        {cn.currency} {Number(cn.allocated_amount).toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-slate-500 dark:text-slate-400 font-medium">
                        {cn.currency} {Number(cn.unallocated_amount).toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {renderStatusBadge(cn.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
                        {cn.status === 'draft' && (
                          <button
                            onClick={() => handlePost(cn.id)}
                            disabled={isActionLoading}
                            className="inline-flex items-center px-2.5 py-1.5 rounded-lg text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                          >
                            {isActionLoading && (
                              <Loader2 className="w-3 h-3 animate-spin mr-1" />
                            )}
                            {t.creditNotesPage.postToLedger}
                          </button>
                        )}
                        {cn.status !== 'void' && (
                          <button
                            onClick={() => setAllocatingNote(cn)}
                            className="inline-flex items-center px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600"
                          >
                            <Layers className="w-3 h-3 mr-1" />
                            {t.creditNotesPage.allocateNote}
                          </button>
                        )}
                        {cn.status !== 'void' && (
                          <button
                            onClick={() => handleVoid(cn.id)}
                            disabled={isActionLoading}
                            className="inline-flex items-center px-2.5 py-1.5 rounded-lg text-xs font-medium text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/60 disabled:opacity-50"
                          >
                            {t.creditNotesPage.voidNote}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* New Credit Note Modal */}
      {isNewModalOpen && companyId && (
        <NewCreditNoteModal
          companyId={companyId}
          noteType={newModalType}
          isOpen={isNewModalOpen}
          onClose={() => setIsNewModalOpen(false)}
          onSuccess={() => {
            setIsNewModalOpen(false);
            setSuccessToast(t.creditNotesPage.noteCreated);
            fetchNotes();
          }}
        />
      )}

      {/* Allocate Credit Note Modal */}
      {allocatingNote && companyId && (
        <AllocateCreditNoteModal
          companyId={companyId}
          creditNote={allocatingNote}
          isOpen={!!allocatingNote}
          onClose={() => setAllocatingNote(null)}
          onSuccess={() => {
            setAllocatingNote(null);
            setSuccessToast(t.creditNotesPage.noteAllocated);
            fetchNotes();
          }}
        />
      )}
    </div>
  );
}
