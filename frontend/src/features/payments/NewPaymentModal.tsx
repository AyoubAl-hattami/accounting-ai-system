import { useState, useEffect, useMemo } from 'react';
import { Loader2, Wand2 } from 'lucide-react';
import Modal from '../../components/ui/Modal';
import { useI18n } from '../../i18n';
import apiClient from '../../api/client';
import type {
  Account,
  Invoice,
  Partner,
  Payment,
  PaymentCreatePayload,
  PaymentType,
  PaginatedResponse,
} from '../../api/types';

interface NewPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  companyId: number;
  initialType?: PaymentType;
  onCreated: (payment: Payment) => void;
}

export default function NewPaymentModal({
  isOpen,
  onClose,
  companyId,
  initialType = 'customer_receipt',
  onCreated,
}: NewPaymentModalProps) {
  const { t } = useI18n();

  const [paymentType, setPaymentType] = useState<PaymentType>(initialType);
  const [partners, setPartners] = useState<Partner[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [partnerId, setPartnerId] = useState('');
  const [currencyCode, setCurrencyCode] = useState('USD');
  const [amount, setAmount] = useState('0.00');
  const [paymentDate, setPaymentDate] = useState(
    new Date().toISOString().slice(0, 10)
  );
  const [bankAccountId, setBankAccountId] = useState('');
  const [arApAccountId, setArApAccountId] = useState('');
  const [reference, setReference] = useState('');
  const [memo, setMemo] = useState('');

  // Open invoices for partner & currency
  const [openInvoices, setOpenInvoices] = useState<Invoice[]>([]);
  const [allocations, setAllocations] = useState<Record<number, string>>({});

  const [isLoadingInvoices, setIsLoadingInvoices] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isReceipt = paymentType === 'customer_receipt';

  // Load partners and accounts
  useEffect(() => {
    if (!isOpen || !companyId) return;

    setPaymentType(initialType);
    setAmount('0.00');
    setPartnerId('');
    setReference('');
    setMemo('');
    setAllocations({});
    setOpenInvoices([]);
    setError(null);

    // Fetch partners
    apiClient
      .get<PaginatedResponse<Partner>>(
        `/partners?company_id=${companyId}&is_active=true&limit=300`
      )
      .then((res) => setPartners(res.data.items))
      .catch(() => setPartners([]));

    // Fetch accounts
    apiClient
      .get<PaginatedResponse<Account>>(
        `/accounts?company_id=${companyId}&is_active=true&limit=300`
      )
      .then((res) => setAccounts(res.data.items))
      .catch(() => setAccounts([]));
  }, [isOpen, companyId, initialType]);

  // Filtered partners by type
  const availablePartners = useMemo(() => {
    return partners.filter((p) => (isReceipt ? p.is_customer : p.is_vendor));
  }, [partners, isReceipt]);

  // When partner changes: update currency, default AR/AP account, and fetch open invoices
  const handlePartnerChange = (id: string) => {
    setPartnerId(id);
    setAllocations({});
    const selected = partners.find((p) => p.id === Number(id));
    if (selected) {
      const pCurr = selected.currency || 'USD';
      setCurrencyCode(pCurr);

      if (isReceipt && selected.receivable_account_id) {
        setArApAccountId(String(selected.receivable_account_id));
      } else if (!isReceipt && selected.payable_account_id) {
        setArApAccountId(String(selected.payable_account_id));
      } else {
        setArApAccountId('');
      }
    }
  };

  // Fetch open invoices when partner or currency changes
  useEffect(() => {
    if (!isOpen || !companyId || !partnerId || !currencyCode) {
      setOpenInvoices([]);
      setAllocations({});
      return;
    }

    setIsLoadingInvoices(true);
    apiClient
      .get<Invoice[]>(
        `/invoices/open-items?company_id=${companyId}&partner_id=${partnerId}&currency=${currencyCode}`
      )
      .then((res) => {
        // Filter invoices matching payment direction:
        // Customer Receipt settles out_invoice (sales)
        // Vendor Payment settles in_invoice (bills)
        const expectedType = isReceipt ? 'out_invoice' : 'in_invoice';
        const filtered = (res.data || []).filter((inv) => inv.invoice_type === expectedType);
        setOpenInvoices(filtered);
      })
      .catch(() => setOpenInvoices([]))
      .finally(() => setIsLoadingInvoices(false));
  }, [isOpen, companyId, partnerId, currencyCode, isReceipt]);

  // Bank accounts filtered by selected currency
  const bankAccounts = useMemo(() => {
    return accounts.filter(
      (a) =>
        a.currency === currencyCode &&
        (a.account_subtype === 'bank' ||
          a.account_subtype === 'cash' ||
          a.account_subtype === 'e_wallet' ||
          a.account_type === 'asset')
    );
  }, [accounts, currencyCode]);

  // AR/AP accounts filtered by selected currency
  const arApAccounts = useMemo(() => {
    const targetSubtype = isReceipt ? 'receivable' : 'payable';
    const targetType = isReceipt ? 'asset' : 'liability';
    return accounts.filter(
      (a) =>
        a.currency === currencyCode &&
        (a.account_subtype === targetSubtype || a.account_type === targetType)
    );
  }, [accounts, currencyCode, isReceipt]);

  // Calculate allocation totals
  const totalAllocated = useMemo(() => {
    return Object.values(allocations).reduce((sum, val) => {
      const num = parseFloat(val) || 0;
      return sum + num;
    }, 0);
  }, [allocations]);

  const numAmount = parseFloat(amount) || 0;
  const unallocatedAmount = Math.max(0, numAmount - totalAllocated);

  const handleAllocationChange = (invoiceId: number, val: string) => {
    setAllocations((prev) => ({
      ...prev,
      [invoiceId]: val,
    }));
  };

  // Auto-allocate payment across open invoices sequentially
  const handleAutoAllocate = () => {
    let remainingToAllocate = numAmount;
    const newAllocations: Record<number, string> = {};

    for (const inv of openInvoices) {
      if (remainingToAllocate <= 0) break;
      const due = parseFloat(String(inv.residual_amount ?? inv.total_amount)) || 0;
      if (due <= 0) continue;

      const alloc = Math.min(remainingToAllocate, due);
      newAllocations[inv.id] = alloc.toFixed(2);
      remainingToAllocate -= alloc;
    }

    setAllocations(newAllocations);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!partnerId) {
      setError(t.paymentsPage.partner + ' is required');
      return;
    }

    if (numAmount <= 0) {
      setError('Amount must be greater than zero.');
      return;
    }

    if (!bankAccountId) {
      setError(t.paymentsPage.bankAccount + ' is required');
      return;
    }

    if (!arApAccountId) {
      setError(t.paymentsPage.arApAccount + ' is required');
      return;
    }

    if (totalAllocated > numAmount) {
      setError(
        `Total allocated (${totalAllocated.toFixed(2)}) cannot exceed payment amount (${numAmount.toFixed(2)}).`
      );
      return;
    }

    // Prepare allocation payloads
    const allocationPayloads = Object.entries(allocations)
      .map(([invId, allocVal]) => ({
        invoice_id: Number(invId),
        amount: parseFloat(allocVal) || 0,
      }))
      .filter((a) => a.amount > 0);

    const payload: PaymentCreatePayload = {
      company_id: companyId,
      partner_id: Number(partnerId),
      payment_type: paymentType,
      currency_code: currencyCode,
      amount: numAmount,
      payment_date: paymentDate,
      bank_or_cash_account_id: Number(bankAccountId),
      receivable_or_payable_account_id: Number(arApAccountId),
      reference: reference.trim() || undefined,
      memo: memo.trim() || undefined,
      allocations: allocationPayloads.length > 0 ? allocationPayloads : undefined,
    };

    setIsSaving(true);
    try {
      const res = await apiClient.post<Payment>('/payments', payload);
      onCreated(res.data);
      onClose();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to record payment.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isReceipt ? t.paymentsPage.newReceipt : t.paymentsPage.newPayment}
      size="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Type toggle */}
        <div className="flex gap-3 border-b border-border pb-4">
          <button
            type="button"
            onClick={() => {
              setPaymentType('customer_receipt');
              setPartnerId('');
              setAllocations({});
            }}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              paymentType === 'customer_receipt'
                ? 'bg-primary text-primary-foreground'
                : 'bg-surface hover:bg-surface-hover text-muted-foreground'
            }`}
          >
            {t.paymentsPage.customerReceipt}
          </button>
          <button
            type="button"
            onClick={() => {
              setPaymentType('vendor_payment');
              setPartnerId('');
              setAllocations({});
            }}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              paymentType === 'vendor_payment'
                ? 'bg-primary text-primary-foreground'
                : 'bg-surface hover:bg-surface-hover text-muted-foreground'
            }`}
          >
            {t.paymentsPage.vendorPayment}
          </button>
        </div>

        {/* Header fields */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              {isReceipt ? t.paymentsPage.customer : t.paymentsPage.vendor} *
            </label>
            <select
              value={partnerId}
              onChange={(e) => handlePartnerChange(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              required
            >
              <option value="">-- {t.paymentsPage.partner} --</option>
              {availablePartners.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code}) [{p.currency}]
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              {t.paymentsPage.currency} *
            </label>
            <input
              type="text"
              value={currencyCode}
              onChange={(e) => setCurrencyCode(e.target.value.toUpperCase())}
              maxLength={3}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              {t.paymentsPage.amount} *
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              {t.paymentsPage.date} *
            </label>
            <input
              type="date"
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              {t.paymentsPage.bankAccount} *
            </label>
            <select
              value={bankAccountId}
              onChange={(e) => setBankAccountId(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              required
            >
              <option value="">-- {t.paymentsPage.bankAccount} --</option>
              {bankAccounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.code} - {a.name} ({a.currency})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              {t.paymentsPage.arApAccount} *
            </label>
            <select
              value={arApAccountId}
              onChange={(e) => setArApAccountId(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              required
            >
              <option value="">-- {t.paymentsPage.arApAccount} --</option>
              {arApAccounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.code} - {a.name} ({a.currency})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              {t.paymentsPage.reference}
            </label>
            <input
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="e.g. Wire-12345 / Check #44"
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              {t.paymentsPage.memo}
            </label>
            <input
              type="text"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="e.g. Payment for January services"
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {/* Open Invoices Settlement Table */}
        <div className="border border-border rounded-xl p-4 bg-surface/50 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-foreground">
              {t.paymentsPage.openInvoices}
            </h4>
            {openInvoices.length > 0 && numAmount > 0 && (
              <button
                type="button"
                onClick={handleAutoAllocate}
                className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
              >
                <Wand2 className="w-3.5 h-3.5" />
                {t.paymentsPage.autoAllocate}
              </button>
            )}
          </div>

          {isLoadingInvoices ? (
            <div className="py-6 flex justify-center text-muted-foreground">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
          ) : openInvoices.length === 0 ? (
            <p className="text-xs text-muted-foreground py-2">
              {partnerId
                ? t.paymentsPage.noOpenInvoices
                : 'Select a partner to load open invoices.'}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-muted-foreground border-b border-border">
                  <tr>
                    <th className="py-2 px-2">{t.paymentsPage.invoiceNo}</th>
                    <th className="py-2 px-2">{t.invoicesPage.issueDate}</th>
                    <th className="py-2 px-2 text-right">
                      {t.paymentsPage.invoiceTotal}
                    </th>
                    <th className="py-2 px-2 text-right">
                      {t.paymentsPage.alreadyPaid}
                    </th>
                    <th className="py-2 px-2 text-right font-medium">
                      {t.paymentsPage.amountDue}
                    </th>
                    <th className="py-2 px-2 text-right w-36">
                      {t.paymentsPage.allocatedAmount}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {openInvoices.map((inv) => {
                    const due =
                      parseFloat(String(inv.residual_amount ?? inv.total_amount)) || 0;
                    const paid = parseFloat(String(inv.paid_amount ?? '0.00')) || 0;
                    return (
                      <tr key={inv.id} className="hover:bg-surface/80">
                        <td className="py-2 px-2 font-mono font-medium text-foreground">
                          {inv.invoice_no}
                        </td>
                        <td className="py-2 px-2 text-muted-foreground">
                          {inv.issue_date}
                        </td>
                        <td className="py-2 px-2 text-right text-muted-foreground">
                          {parseFloat(inv.total_amount).toFixed(2)} {inv.currency}
                        </td>
                        <td className="py-2 px-2 text-right text-muted-foreground">
                          {paid.toFixed(2)}
                        </td>
                        <td className="py-2 px-2 text-right font-medium text-foreground">
                          {due.toFixed(2)} {inv.currency}
                        </td>
                        <td className="py-2 px-2 text-right">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max={due}
                            value={allocations[inv.id] || ''}
                            onChange={(e) =>
                              handleAllocationChange(inv.id, e.target.value)
                            }
                            placeholder="0.00"
                            className="w-full bg-surface border border-border rounded px-2 py-1 text-right text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Allocation summary footer */}
          <div className="flex flex-wrap items-center justify-between pt-3 border-t border-border text-xs">
            <div className="flex gap-4">
              <span>
                {t.paymentsPage.totalAllocated}:{' '}
                <strong className="text-foreground">
                  {totalAllocated.toFixed(2)} {currencyCode}
                </strong>
              </span>
              <span>
                {t.paymentsPage.unallocatedAmount}:{' '}
                <strong
                  className={
                    unallocatedAmount > 0
                      ? 'text-amber-400 font-semibold'
                      : 'text-foreground'
                  }
                >
                  {unallocatedAmount.toFixed(2)} {currencyCode}
                </strong>
              </span>
            </div>
          </div>
        </div>

        {/* Modal actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-surface rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50"
          >
            {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
            {isSaving ? t.paymentsPage.creating : t.paymentsPage.createPayment}
          </button>
        </div>
      </form>
    </Modal>
  );
}
