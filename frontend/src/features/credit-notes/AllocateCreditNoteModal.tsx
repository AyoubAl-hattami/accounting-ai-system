import { useState, useEffect, useMemo } from 'react';
import { X, Loader2, AlertCircle, Check, DollarSign } from 'lucide-react';
import apiClient from '../../api/client';
import { CreditNote, Invoice, CreditNoteAllocationPayload, PaginatedResponse } from '../../api/types';
import { useI18n } from '../../i18n';

interface AllocateCreditNoteModalProps {
  companyId?: number;
  creditNote: CreditNote;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function AllocateCreditNoteModal({
  creditNote,
  isOpen,
  onClose,
  onSuccess,
}: AllocateCreditNoteModalProps) {
  const { t } = useI18n();

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [allocations, setAllocations] = useState<Record<number, number>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isCustomer = creditNote.note_type === 'customer_credit_note';
  const expectedInvoiceType = isCustomer ? 'customer_invoice' : 'vendor_bill';

  // Fetch open invoices for this partner with the same currency
  useEffect(() => {
    if (!isOpen) return;

    setIsLoading(true);
    setError(null);
    setAllocations({});

    apiClient
      .get<PaginatedResponse<Invoice>>(
        `/invoices?company_id=${creditNote.company_id}&partner_id=${creditNote.partner_id}&currency=${creditNote.currency}&invoice_type=${expectedInvoiceType}&limit=100`
      )
      .then((res: any) => {
        const items = res.data.items || [];
        // Only keep posted invoices with positive residual amount
        const openInvoices = items.filter((inv: Invoice) => {
          const resAmt = inv.residual_amount !== undefined
            ? Number(inv.residual_amount)
            : Number(inv.total_amount) - Number(inv.paid_amount || 0) - Number(inv.credited_amount || 0);
          return inv.status === 'posted' && resAmt > 0;
        });
        setInvoices(openInvoices);
      })
      .catch((err: any) => {
        setError(err?.response?.data?.detail || 'Failed to load open invoices.');
      })
      .finally(() => setIsLoading(false));
  }, [isOpen, creditNote, expectedInvoiceType]);

  const totalAllocatedInModal = useMemo(() => {
    return Object.values(allocations).reduce((sum, val) => sum + (Number(val) || 0), 0);
  }, [allocations]);

  const availableUnallocated = Number(creditNote.unallocated_amount || 0);
  const remainingUnallocated = Math.max(0, availableUnallocated - totalAllocatedInModal);

  const handleAmountChange = (invoiceId: number, maxResidual: number, valueStr: string) => {
    const val = parseFloat(valueStr);
    if (isNaN(val) || val <= 0) {
      const next = { ...allocations };
      delete next[invoiceId];
      setAllocations(next);
      return;
    }

    // Cap at invoice residual amount
    const capped = Math.min(val, maxResidual);
    setAllocations((prev) => ({
      ...prev,
      [invoiceId]: Math.round(capped * 100) / 100,
    }));
  };

  const handleQuickMax = (invoiceId: number, residual: number) => {
    // Current allocation for this invoice
    const currentForInvoice = allocations[invoiceId] || 0;
    // Available unallocated pool plus what was already allocated to this invoice
    const pool = availableUnallocated - (totalAllocatedInModal - currentForInvoice);
    const maxPossible = Math.min(residual, pool);

    if (maxPossible > 0) {
      setAllocations((prev) => ({
        ...prev,
        [invoiceId]: Math.round(maxPossible * 100) / 100,
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (totalAllocatedInModal <= 0) {
      setError('Please allocate an amount to at least one invoice.');
      return;
    }

    if (totalAllocatedInModal > availableUnallocated) {
      setError(
        `Total allocated (${totalAllocatedInModal.toFixed(2)}) exceeds available unallocated credit (${availableUnallocated.toFixed(2)}).`
      );
      return;
    }

    const payload: { allocations: CreditNoteAllocationPayload[] } = {
      allocations: Object.entries(allocations)
        .filter(([_, amt]) => amt > 0)
        .map(([invId, amt]) => ({
          invoice_id: Number(invId),
          amount: amt,
        })),
    };

    setIsSubmitting(true);
    setError(null);

    try {
      await apiClient.post(
        `/credit-notes/${creditNote.id}/allocate`,
        payload
      );
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to allocate credit note.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-3xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-indigo-500" />
              {t.creditNotesPage.allocateModalTitle}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {creditNote.credit_note_no} • {creditNote.partner_name} ({creditNote.currency})
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
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2 text-red-700 dark:text-red-300 text-sm">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Allocation summary cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                {t.creditNotesPage.totalAmount}
              </p>
              <p className="text-base font-bold text-slate-900 dark:text-white mt-1">
                {Number(creditNote.total_amount).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                })}{' '}
                {creditNote.currency}
              </p>
            </div>
            <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/40">
              <p className="text-xs text-amber-700 dark:text-amber-300 font-medium">
                {t.creditNotesPage.allocatedAmount}
              </p>
              <p className="text-base font-bold text-amber-900 dark:text-amber-100 mt-1">
                {Number(creditNote.allocated_amount || 0).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                })}{' '}
                {creditNote.currency}
              </p>
            </div>
            <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700/40">
              <p className="text-xs text-emerald-700 dark:text-emerald-300 font-medium">
                {t.creditNotesPage.allocateRemaining}
              </p>
              <p className="text-base font-bold text-emerald-900 dark:text-emerald-100 mt-1">
                {remainingUnallocated.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                })}{' '}
                {creditNote.currency}
              </p>
            </div>
          </div>

          {/* Invoice selection list */}
          <div>
            <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
              {t.creditNotesPage.selectInvoice}
            </h4>

            {isLoading ? (
              <div className="py-12 flex flex-col items-center justify-center text-slate-500">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mb-2" />
                <p className="text-sm">Loading open invoices...</p>
              </div>
            ) : invoices.length === 0 ? (
              <div className="py-8 text-center border border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {t.creditNotesPage.noOpenInvoices}
                </p>
              </div>
            ) : (
              <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-600 dark:text-slate-300">
                      <th className="px-4 py-3">{t.creditNotesPage.invoiceNo}</th>
                      <th className="px-4 py-3">{t.creditNotesPage.invoiceDate}</th>
                      <th className="px-4 py-3 text-right">{t.creditNotesPage.invoiceTotal}</th>
                      <th className="px-4 py-3 text-right">{t.creditNotesPage.invoiceResidual}</th>
                      <th className="px-4 py-3 text-right w-44">{t.creditNotesPage.amountToAllocate}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                    {invoices.map((inv) => {
                      const residual: number =
                        inv.residual_amount !== undefined
                          ? Number(inv.residual_amount)
                          : Math.max(
                              0,
                              Number(inv.total_amount) -
                                Number(inv.paid_amount || 0) -
                                Number(inv.credited_amount || 0)
                            );
                      const currentAlloc = allocations[inv.id] || '';

                      return (
                        <tr
                          key={inv.id}
                          className="hover:bg-slate-50/50 dark:hover:bg-slate-700/30 transition-colors"
                        >
                          <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                            {inv.invoice_no}
                          </td>
                          <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs">
                            {inv.issue_date}
                          </td>
                          <td className="px-4 py-3 text-right text-slate-600 dark:text-slate-300">
                            {Number(inv.total_amount).toFixed(2)} {inv.currency}
                          </td>
                          <td className="px-4 py-3 text-right font-semibold text-indigo-600 dark:text-indigo-400">
                            {Number(residual).toFixed(2)} {inv.currency}
                          </td>
                          <td className="px-4 py-2 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                max={residual}
                                value={currentAlloc}
                                onChange={(e) =>
                                  handleAmountChange(inv.id, residual, e.target.value)
                                }
                                placeholder="0.00"
                                className="w-24 px-2.5 py-1 text-right text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                              />
                              <button
                                type="button"
                                onClick={() => handleQuickMax(inv.id, residual)}
                                className="px-2 py-1 text-xs font-semibold rounded-md bg-slate-100 hover:bg-indigo-50 dark:bg-slate-700 dark:hover:bg-indigo-900/40 text-slate-700 hover:text-indigo-600 dark:text-slate-300 dark:hover:text-indigo-400 transition-colors"
                              >
                                {t.creditNotesPage.maxButton}
                              </button>
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

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
            <div className="text-sm text-slate-600 dark:text-slate-400">
              Allocating:{' '}
              <span className="font-bold text-slate-900 dark:text-white">
                {totalAllocatedInModal.toFixed(2)} {creditNote.currency}
              </span>
            </div>
            <div className="flex gap-3">
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
                disabled={isSubmitting || totalAllocatedInModal <= 0}
                className="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    <span>{t.creditNotesPage.submitAllocation}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
