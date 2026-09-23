import { useState, useEffect, useMemo } from 'react';
import { X, Plus, Trash2, Loader2, AlertCircle } from 'lucide-react';
import apiClient from '../../api/client';
import {
  CreditNoteType,
  CreditNoteCreatePayload,
  CreditNoteLinePayload,
  Partner,
  Account,
} from '../../api/types';
import { useI18n } from '../../i18n';

interface NewCreditNoteModalProps {
  companyId: number;
  noteType: CreditNoteType;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function NewCreditNoteModal({
  companyId,
  noteType,
  isOpen,
  onClose,
  onSuccess,
}: NewCreditNoteModalProps) {
  const { t } = useI18n();

  const [partners, setPartners] = useState<Partner[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isCustomer = noteType === 'customer_credit_note';

  // Form State
  const [partnerId, setPartnerId] = useState<number | ''>('');
  const [creditNoteNo, setCreditNoteNo] = useState<string>('');
  const [issueDate, setIssueDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [currency, setCurrency] = useState<string>('USD');
  const [reference, setReference] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [taxAmount, setTaxAmount] = useState<number>(0);

  const [lines, setLines] = useState<CreditNoteLinePayload[]>([
    { description: '', quantity: 1, unit_price: 0, account_id: 0 },
  ]);

  // Fetch partners and accounts
  useEffect(() => {
    if (!isOpen) return;

    setIsLoadingMetadata(true);
    setError(null);

    const partnerFilter = isCustomer ? 'is_customer=true' : 'is_vendor=true';
    Promise.all([
      apiClient.get<{ items: Partner[] }>(
        `/partners?company_id=${companyId}&${partnerFilter}&limit=100`
      ),
      apiClient.get<Account[]>(`/accounts?company_id=${companyId}&is_active=true`),
    ])
      .then(([partnersRes, accountsRes]) => {
        setPartners(partnersRes.data.items || []);
        setAccounts(accountsRes.data || []);
      })
      .catch((err) => {
        setError(err?.response?.data?.detail || 'Failed to load partners or accounts.');
      })
      .finally(() => setIsLoadingMetadata(false));
  }, [isOpen, companyId, isCustomer]);

  // Update currency when partner changes
  const handlePartnerChange = (id: number) => {
    setPartnerId(id);
    const selected = partners.find((p) => p.id === id);
    if (selected && selected.currency) {
      setCurrency(selected.currency);
    }
  };

  // Line item helpers
  const handleLineChange = (
    index: number,
    field: keyof CreditNoteLinePayload,
    value: any
  ) => {
    const updated = [...lines];
    updated[index] = { ...updated[index], [field]: value };
    setLines(updated);
  };

  const addLine = () => {
    const defaultAccountId = accounts.length > 0 ? accounts[0].id : 0;
    setLines([
      ...lines,
      { description: '', quantity: 1, unit_price: 0, account_id: defaultAccountId },
    ]);
  };

  const removeLine = (index: number) => {
    if (lines.length <= 1) return;
    setLines(lines.filter((_, i) => i !== index));
  };

  // Calculated totals
  const subtotal = useMemo(() => {
    return lines.reduce((acc, l) => acc + (Number(l.quantity) || 0) * (Number(l.unit_price) || 0), 0);
  }, [lines]);

  const totalAmount = useMemo(() => {
    return subtotal + (Number(taxAmount) || 0);
  }, [subtotal, taxAmount]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!partnerId) {
      setError('Please select a partner.');
      return;
    }
    if (!creditNoteNo.trim()) {
      setError('Please enter a note number.');
      return;
    }
    if (lines.some((l) => !l.description.trim() || l.quantity <= 0 || l.account_id <= 0)) {
      setError('Please fill in all line item details with valid accounts and quantities.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const payload: CreditNoteCreatePayload = {
      company_id: companyId,
      partner_id: Number(partnerId),
      note_type: noteType,
      credit_note_no: creditNoteNo.trim(),
      issue_date: issueDate,
      currency,
      reference: reference.trim() || null,
      reason: reason.trim() || null,
      tax_amount: Number(taxAmount) || 0,
      lines: lines.map((l) => ({
        description: l.description.trim(),
        quantity: Number(l.quantity),
        unit_price: Number(l.unit_price),
        account_id: Number(l.account_id),
      })),
    };

    try {
      await apiClient.post('/credit-notes', payload);
      onSuccess();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create credit note.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl max-w-3xl w-full overflow-hidden border border-slate-200 dark:border-slate-700">
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            {isCustomer
              ? t.creditNotesPage.newCreditNote
              : t.creditNotesPage.newDebitNote}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-500 dark:hover:text-slate-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="m-6 mb-0 p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl text-rose-700 dark:text-rose-300 flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {isLoadingMetadata ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
          ) : (
            <>
              {/* Header Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.creditNotesPage.partner} *
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

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Document Number *
                  </label>
                  <input
                    type="text"
                    value={creditNoteNo}
                    onChange={(e) => setCreditNoteNo(e.target.value)}
                    placeholder={isCustomer ? 'CN-001' : 'DN-001'}
                    required
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.creditNotesPage.date} *
                  </label>
                  <input
                    type="date"
                    value={issueDate}
                    onChange={(e) => setIssueDate(e.target.value)}
                    required
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.creditNotesPage.currency}
                  </label>
                  <input
                    type="text"
                    value={currency}
                    readOnly
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-slate-700 px-3 py-2 text-sm text-slate-500 dark:text-slate-400 cursor-not-allowed"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.creditNotesPage.reference}
                  </label>
                  <input
                    type="text"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                    placeholder="PO / Return #"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    {t.creditNotesPage.reason}
                  </label>
                  <input
                    type="text"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="e.g. Return of goods"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Line Items */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                    {t.creditNotesPage.lineItems}
                  </h3>
                  <button
                    type="button"
                    onClick={addLine}
                    className="inline-flex items-center text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    <Plus className="w-3.5 h-3.5 mr-1" />
                    {t.creditNotesPage.addLine}
                  </button>
                </div>

                <div className="space-y-2">
                  {lines.map((line, idx) => (
                    <div
                      key={idx}
                      className="grid grid-cols-12 gap-2 items-center bg-slate-50 dark:bg-slate-900/30 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700"
                    >
                      <div className="col-span-5">
                        <input
                          type="text"
                          placeholder={t.creditNotesPage.description}
                          value={line.description}
                          onChange={(e) =>
                            handleLineChange(idx, 'description', e.target.value)
                          }
                          required
                          className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-2.5 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        />
                      </div>
                      <div className="col-span-3">
                        <select
                          value={line.account_id}
                          onChange={(e) =>
                            handleLineChange(idx, 'account_id', Number(e.target.value))
                          }
                          required
                          className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-2 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        >
                          <option value="0">Select Account</option>
                          {accounts.map((acc) => (
                            <option key={acc.id} value={acc.id}>
                              {acc.code} - {acc.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="col-span-1">
                        <input
                          type="number"
                          step="0.01"
                          min="0.01"
                          placeholder={t.creditNotesPage.quantity}
                          value={line.quantity}
                          onChange={(e) =>
                            handleLineChange(idx, 'quantity', parseFloat(e.target.value) || 0)
                          }
                          required
                          className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-2 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 text-right"
                        />
                      </div>
                      <div className="col-span-2">
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          placeholder={t.creditNotesPage.unitPrice}
                          value={line.unit_price}
                          onChange={(e) =>
                            handleLineChange(idx, 'unit_price', parseFloat(e.target.value) || 0)
                          }
                          required
                          className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-2 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 text-right"
                        />
                      </div>
                      <div className="col-span-1 flex justify-center">
                        <button
                          type="button"
                          onClick={() => removeLine(idx)}
                          disabled={lines.length <= 1}
                          className="text-slate-400 hover:text-rose-500 disabled:opacity-30"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Totals Section */}
              <div className="flex justify-end pt-2">
                <div className="w-64 space-y-2 bg-slate-50 dark:bg-slate-900/40 p-4 rounded-xl border border-slate-200 dark:border-slate-700 text-sm">
                  <div className="flex justify-between text-slate-600 dark:text-slate-400">
                    <span>{t.creditNotesPage.subtotal}:</span>
                    <span className="font-medium text-slate-900 dark:text-white">
                      {currency} {subtotal.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-slate-600 dark:text-slate-400">
                    <span>{t.creditNotesPage.taxAmount}:</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={taxAmount}
                      onChange={(e) => setTaxAmount(parseFloat(e.target.value) || 0)}
                      className="w-24 rounded border border-slate-300 dark:border-slate-600 bg-transparent px-2 py-0.5 text-right text-sm text-slate-900 dark:text-white"
                    />
                  </div>
                  <div className="flex justify-between font-semibold text-slate-900 dark:text-white border-t border-slate-200 dark:border-slate-700 pt-2">
                    <span>{t.creditNotesPage.totalAmount}:</span>
                    <span>
                      {currency} {totalAmount.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || isLoadingMetadata}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              {t.creditNotesPage.createNote}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
