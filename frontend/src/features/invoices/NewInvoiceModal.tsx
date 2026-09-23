import { useState, useEffect } from 'react';
import { Plus, Trash2, Loader2 } from 'lucide-react';
import Modal from '../../components/ui/Modal';
import { useI18n } from '../../i18n';
import apiClient from '../../api/client';
import type {
  Account,
  Invoice,
  InvoiceCreatePayload,
  InvoiceLineCreatePayload,
  InvoiceType,
  Partner,
  PaginatedResponse,
} from '../../api/types';

interface NewInvoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  companyId: number;
  invoiceType: InvoiceType;
  onCreated: (invoice: Invoice) => void;
}

interface LineItemState {
  description: string;
  quantity: string;
  unitPrice: string;
  accountId: string;
}

export default function NewInvoiceModal({
  isOpen,
  onClose,
  companyId,
  invoiceType,
  onCreated,
}: NewInvoiceModalProps) {
  const { t } = useI18n();

  const isSales = invoiceType === 'out_invoice';
  const modalTitle = isSales
    ? t.invoicesPage.newInvoice
    : t.invoicesPage.newBill;

  const [partners, setPartners] = useState<Partner[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [partnerId, setPartnerId] = useState('');
  const [invoiceNo, setInvoiceNo] = useState('');
  const [reference, setReference] = useState('');
  const [issueDate, setIssueDate] = useState(
    new Date().toISOString().slice(0, 10)
  );
  const [dueDate, setDueDate] = useState(
    new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
  );
  const [currency, setCurrency] = useState('');
  const [taxAmount, setTaxAmount] = useState('0.00');
  const [notes, setNotes] = useState('');
  const [lines, setLines] = useState<LineItemState[]>([
    { description: '', quantity: '1', unitPrice: '0.00', accountId: '' },
  ]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load partners and accounts
  useEffect(() => {
    if (!isOpen || !companyId) return;

    apiClient
      .get<PaginatedResponse<Partner>>(
        `/partners?company_id=${companyId}&${
          isSales ? 'is_customer=true' : 'is_vendor=true'
        }&is_active=true&limit=200`
      )
      .then((res) => setPartners(res.data.items))
      .catch(() => setPartners([]));

    apiClient
      .get<PaginatedResponse<Account>>(
        `/accounts?company_id=${companyId}&is_active=true&limit=300`
      )
      .then((res) => setAccounts(res.data.items))
      .catch(() => setAccounts([]));

    // Generate suggested invoice number
    const prefix = isSales ? 'INV' : 'BILL';
    const rand = Math.floor(1000 + Math.random() * 9000);
    const yr = new Date().getFullYear();
    setInvoiceNo(`${prefix}-${yr}-${rand}`);
  }, [isOpen, companyId, isSales]);

  // When partner changes, adopt their currency
  const handlePartnerChange = (id: string) => {
    setPartnerId(id);
    const selected = partners.find((p) => p.id === Number(id));
    if (selected) {
      setCurrency(selected.currency);
    }
  };

  const handleAddLine = () => {
    setLines((prev) => [
      ...prev,
      { description: '', quantity: '1', unitPrice: '0.00', accountId: '' },
    ]);
  };

  const handleRemoveLine = (index: number) => {
    if (lines.length <= 1) return;
    setLines((prev) => prev.filter((_, i) => i !== index));
  };

  const handleLineChange = (
    index: number,
    field: keyof LineItemState,
    value: string
  ) => {
    setLines((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  // Calculations
  const subtotal = lines.reduce((acc, line) => {
    const q = parseFloat(line.quantity) || 0;
    const p = parseFloat(line.unitPrice) || 0;
    return acc + q * p;
  }, 0);

  const tax = parseFloat(taxAmount) || 0;
  const total = subtotal + tax;

  // Filter accounts for lines: Revenue for sales, Expense/Asset for bills
  const filteredAccounts = accounts.filter((a) => {
    if (currency && a.currency !== currency) return false;
    if (isSales) return a.account_type === 'income';
    return a.account_type === 'expense' || a.account_type === 'asset';
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!partnerId || !invoiceNo.trim()) {
      setError('Please select a partner and enter an invoice number.');
      return;
    }

    for (const [idx, line] of lines.entries()) {
      if (!line.description.trim()) {
        setError(`Line ${idx + 1}: Description is required.`);
        return;
      }
      if (!line.accountId) {
        setError(`Line ${idx + 1}: Account is required.`);
        return;
      }
    }

    setIsSaving(true);
    setError(null);

    const payloadLines: InvoiceLineCreatePayload[] = lines.map((l) => ({
      description: l.description.trim(),
      quantity: parseFloat(l.quantity) || 1,
      unit_price: parseFloat(l.unitPrice) || 0,
      account_id: Number(l.accountId),
    }));

    const payload: InvoiceCreatePayload = {
      company_id: companyId,
      partner_id: Number(partnerId),
      invoice_type: invoiceType,
      invoice_no: invoiceNo.trim(),
      issue_date: issueDate,
      due_date: dueDate,
      currency: currency || undefined,
      reference: reference.trim() || undefined,
      tax_amount: tax,
      notes: notes.trim() || undefined,
      lines: payloadLines,
    };

    try {
      const res = await apiClient.post<Invoice>('/invoices', payload);
      onCreated(res.data);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to create invoice.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={modalTitle}
      description={
        isSales
          ? t.invoicesPage.pageSubtitle
          : t.invoicesPage.billsPageSubtitle
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-md text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Header fields */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="field-label">
              {isSales ? t.invoicesPage.customer : t.invoicesPage.vendor} *
            </label>
            <select
              required
              value={partnerId}
              onChange={(e) => handlePartnerChange(e.target.value)}
              className="select w-full"
            >
              <option value="">-- Select --</option>
              {partners.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.currency})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="field-label">{t.invoicesPage.invoiceNo} *</label>
            <input
              type="text"
              required
              value={invoiceNo}
              onChange={(e) => setInvoiceNo(e.target.value)}
              className="input w-full uppercase"
            />
          </div>

          <div>
            <label className="field-label">{t.invoicesPage.reference}</label>
            <input
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="e.g. PO-1029"
              className="input w-full"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="field-label">{t.invoicesPage.issueDate} *</label>
            <input
              type="date"
              required
              value={issueDate}
              onChange={(e) => setIssueDate(e.target.value)}
              className="input w-full"
            />
          </div>

          <div>
            <label className="field-label">{t.invoicesPage.dueDate} *</label>
            <input
              type="date"
              required
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="input w-full"
            />
          </div>

          <div>
            <label className="field-label">{t.invoicesPage.currency}</label>
            <input
              type="text"
              readOnly
              value={currency || '—'}
              className="input w-full font-mono bg-neutral-100 dark:bg-neutral-900 cursor-not-allowed"
            />
          </div>
        </div>

        {/* Line Items */}
        <div className="pt-2">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
              {t.invoicesPage.lineItems}
            </h4>
            <button
              type="button"
              onClick={handleAddLine}
              className="btn btn-secondary text-xs py-1 px-2.5 inline-flex items-center gap-1.5"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>{t.invoicesPage.addLine}</span>
            </button>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {lines.map((line, idx) => (
              <div
                key={idx}
                className="grid grid-cols-12 gap-2 items-center bg-neutral-50 dark:bg-neutral-900/60 p-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800"
              >
                <div className="col-span-5">
                  <input
                    type="text"
                    required
                    placeholder={t.invoicesPage.itemDescription}
                    value={line.description}
                    onChange={(e) =>
                      handleLineChange(idx, 'description', e.target.value)
                    }
                    className="input w-full text-xs"
                  />
                </div>

                <div className="col-span-3">
                  <select
                    required
                    value={line.accountId}
                    onChange={(e) =>
                      handleLineChange(idx, 'accountId', e.target.value)
                    }
                    className="select w-full text-xs"
                  >
                    <option value="">-- {t.invoicesPage.account} --</option>
                    {filteredAccounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.code} - {a.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="col-span-1">
                  <input
                    type="number"
                    step="any"
                    required
                    placeholder={t.invoicesPage.quantity}
                    value={line.quantity}
                    onChange={(e) =>
                      handleLineChange(idx, 'quantity', e.target.value)
                    }
                    className="input w-full text-xs text-right font-mono"
                  />
                </div>

                <div className="col-span-2">
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder={t.invoicesPage.unitPrice}
                    value={line.unitPrice}
                    onChange={(e) =>
                      handleLineChange(idx, 'unitPrice', e.target.value)
                    }
                    className="input w-full text-xs text-right font-mono"
                  />
                </div>

                <div className="col-span-1 text-center">
                  <button
                    type="button"
                    disabled={lines.length <= 1}
                    onClick={() => handleRemoveLine(idx)}
                    className="p-1.5 text-neutral-400 hover:text-red-600 disabled:opacity-30 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Totals & Notes */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-neutral-200 dark:border-neutral-800">
          <div>
            <label className="field-label">{t.invoicesPage.notes}</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Payment instructions, terms, notes..."
              className="input w-full resize-none text-xs"
            />
          </div>

          <div className="space-y-1.5 text-sm bg-neutral-50 dark:bg-neutral-900 p-3 rounded-lg border border-neutral-200 dark:border-neutral-800">
            <div className="flex justify-between text-neutral-600 dark:text-neutral-400">
              <span>{t.invoicesPage.subtotal}:</span>
              <span className="font-mono">
                {subtotal.toFixed(2)} {currency}
              </span>
            </div>
            <div className="flex justify-between items-center text-neutral-600 dark:text-neutral-400">
              <span>{t.invoicesPage.taxAmount}:</span>
              <input
                type="number"
                step="0.01"
                value={taxAmount}
                onChange={(e) => setTaxAmount(e.target.value)}
                className="input w-24 text-right text-xs font-mono py-1"
              />
            </div>
            <div className="flex justify-between font-bold text-base text-neutral-900 dark:text-white pt-1 border-t border-neutral-200 dark:border-neutral-800">
              <span>{t.invoicesPage.totalAmount}:</span>
              <span className="font-mono">
                {total.toFixed(2)} {currency}
              </span>
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200 dark:border-neutral-800">
          <button
            type="button"
            onClick={onClose}
            className="btn btn-secondary"
            disabled={isSaving}
          >
            {t.common.cancel}
          </button>
          <button
            type="submit"
            disabled={isSaving}
            className="btn btn-primary min-w-[7rem]"
          >
            {isSaving ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t.invoicesPage.creating}
              </span>
            ) : (
              t.invoicesPage.createInvoice
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
