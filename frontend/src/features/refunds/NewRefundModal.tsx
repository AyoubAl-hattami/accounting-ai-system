import { useState, useEffect } from 'react';
import { X, Loader2, AlertCircle, Check } from 'lucide-react';
import apiClient from '../../api/client';
import type {
  RefundType,
  RefundCreatePayload,
  Partner,
  Account,
  CreditNote,
  PaginatedResponse,
} from '../../api/types';
import { useI18n } from '../../i18n';

interface NewRefundModalProps {
  companyId: number;
  refundType: RefundType;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function NewRefundModal({
  companyId,
  refundType,
  isOpen,
  onClose,
  onSuccess,
}: NewRefundModalProps) {
  const { t } = useI18n();

  const [partners, setPartners] = useState<Partner[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [creditNotes, setCreditNotes] = useState<CreditNote[]>([]);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isCustomer = refundType === 'customer_refund';

  // Form State
  const [partnerId, setPartnerId] = useState<number | ''>('');
  const [refundDate, setRefundDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [currencyCode, setCurrencyCode] = useState<string>('USD');
  const [amount, setAmount] = useState<number | ''>('');
  const [bankAccountId, setBankAccountId] = useState<number | ''>('');
  const [arApAccountId, setArApAccountId] = useState<number | ''>('');
  const [creditNoteId, setCreditNoteId] = useState<number | ''>('');
  const [reference, setReference] = useState<string>('');
  const [memo, setMemo] = useState<string>('');

  // Fetch partners and accounts
  useEffect(() => {
    if (!isOpen) return;

    setIsLoadingMetadata(true);
    setError(null);

    const partnerFilter = isCustomer ? 'is_customer=true' : 'is_vendor=true';

    Promise.all([
      apiClient.get<Partner[]>(`/partners?company_id=${companyId}&${partnerFilter}&limit=200`),
      apiClient.get<Account[]>(`/accounts?company_id=${companyId}&is_active=true&limit=300`),
    ])
      .then(([partnersRes, accountsRes]) => {
        const pList = partnersRes.data || [];
        setPartners(pList);
        const aList = accountsRes.data || [];
        setAccounts(aList);

        // Pre-select default accounts if available
        const bankAcct = aList.find(
          (a: Account) =>
            a.account_type === 'asset' &&
            (a.code.startsWith('10') ||
              a.code.startsWith('11') ||
              a.name.toLowerCase().includes('bank') ||
              a.name.toLowerCase().includes('cash'))
        );
        if (bankAcct) {
          setBankAccountId(bankAcct.id);
        }

        if (isCustomer) {
          const arAcct = aList.find(
            (a: Account) =>
              a.account_type === 'asset' &&
              (a.code.startsWith('12') ||
                a.name.toLowerCase().includes('receivable') ||
                a.name.toLowerCase().includes('ar'))
          );
          if (arAcct) setArApAccountId(arAcct.id);
        } else {
          const apAcct = aList.find(
            (a: Account) =>
              a.account_type === 'liability' &&
              (a.code.startsWith('20') ||
                a.name.toLowerCase().includes('payable') ||
                a.name.toLowerCase().includes('ap'))
          );
          if (apAcct) setArApAccountId(apAcct.id);
        }
      })
      .catch((err: any) => {
        setError(err?.response?.data?.detail || 'Failed to load partners or accounts.');
      })
      .finally(() => setIsLoadingMetadata(false));
  }, [isOpen, companyId, isCustomer]);

  // When partner changes, update currency and fetch available credit notes
  const handlePartnerChange = (id: number) => {
    setPartnerId(id);
    setCreditNoteId('');
    const partner = partners.find((p: Partner) => p.id === id);
    if (partner) {
      setCurrencyCode(partner.currency || 'USD');
      // Fetch credit notes for this partner
      const noteType = isCustomer ? 'customer_credit_note' : 'vendor_debit_note';
      apiClient
        .get<PaginatedResponse<CreditNote>>(
          `/credit-notes?company_id=${companyId}&partner_id=${id}&note_type=${noteType}&status=posted&limit=50`
        )
        .then((res: any) => {
          setCreditNotes(res.data.items || []);
        })
        .catch(() => {
          setCreditNotes([]);
        });
    } else {
      setCreditNotes([]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!partnerId) {
      setError('Please select a partner.');
      return;
    }
    if (!amount || Number(amount) <= 0) {
      setError('Amount must be greater than zero.');
      return;
    }
    if (!bankAccountId) {
      setError('Please select a bank or cash account.');
      return;
    }
    if (!arApAccountId) {
      setError('Please select an AR / AP account.');
      return;
    }

    const payload: RefundCreatePayload = {
      company_id: companyId,
      partner_id: Number(partnerId),
      refund_type: refundType,
      currency_code: currencyCode,
      amount: Number(amount),
      refund_date: refundDate,
      bank_or_cash_account_id: Number(bankAccountId),
      receivable_or_payable_account_id: Number(arApAccountId),
      credit_note_id: creditNoteId ? Number(creditNoteId) : null,
      reference: reference.trim() || null,
      memo: memo.trim() || null,
    };

    setIsSubmitting(true);
    setError(null);

    try {
      await apiClient.post('/refunds', payload);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create refund.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-2xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              {isCustomer ? t.refundsPage.newCustomerRefund : t.refundsPage.newVendorRefund}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {isCustomer ? 'Disburse funds to a customer' : 'Record received refund from a vendor'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2 text-red-700 dark:text-red-300 text-sm">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {isLoadingMetadata ? (
            <div className="py-12 flex flex-col items-center justify-center text-slate-500">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mb-2" />
              <p className="text-sm">Loading accounts and partners...</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Partner */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.refundsPage.partner} *
                  </label>
                  <select
                    value={partnerId}
                    onChange={(e) => handlePartnerChange(Number(e.target.value))}
                    required
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select Partner</option>
                    {partners.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.currency})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Date */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.refundsPage.date} *
                  </label>
                  <input
                    type="date"
                    value={refundDate}
                    onChange={(e) => setRefundDate(e.target.value)}
                    required
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Amount */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.refundsPage.amount} *
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value === '' ? '' : Number(e.target.value))}
                      placeholder="0.00"
                      required
                      className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <span className="absolute right-3 top-2 text-xs font-bold text-slate-400">
                      {currencyCode}
                    </span>
                  </div>
                </div>

                {/* Currency */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.refundsPage.currency}
                  </label>
                  <input
                    type="text"
                    value={currencyCode}
                    readOnly
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-slate-700 px-3 py-2 text-sm text-slate-500 dark:text-slate-400 cursor-not-allowed"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Bank or Cash Account */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.refundsPage.bankCashAccount} *
                  </label>
                  <select
                    value={bankAccountId}
                    onChange={(e) => setBankAccountId(Number(e.target.value))}
                    required
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select Account</option>
                    {accounts
                      .filter((a) => a.account_type === 'asset')
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.code} - {a.name}
                        </option>
                      ))}
                  </select>
                </div>

                {/* AR / AP Account */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.refundsPage.arApAccount} ({isCustomer ? 'AR Asset' : 'AP Liability'}) *
                  </label>
                  <select
                    value={arApAccountId}
                    onChange={(e) => setArApAccountId(Number(e.target.value))}
                    required
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select Account</option>
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.code} - {a.name} ({a.account_type})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Linked Credit Note (Optional) */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  {t.refundsPage.creditNote}
                </label>
                <select
                  value={creditNoteId}
                  onChange={(e) => setCreditNoteId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">None (General Partner Refund)</option>
                  {creditNotes.map((cn) => (
                    <option key={cn.id} value={cn.id}>
                      {cn.credit_note_no} - {cn.total_amount} {cn.currency} (Unallocated: {cn.unallocated_amount})
                    </option>
                  ))}
                </select>
              </div>

              {/* Reference */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  {t.refundsPage.reference}
                </label>
                <input
                  type="text"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  placeholder="Check #, Wire transfer ref, etc."
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* Memo */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  {t.refundsPage.reason}
                </label>
                <input
                  type="text"
                  value={memo}
                  onChange={(e) => setMemo(e.target.value)}
                  placeholder="Reason or notes for this refund"
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-semibold rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              {t.common.cancel}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || isLoadingMetadata}
              className="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating...</span>
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  <span>{t.refundsPage.createRefund}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
