import { useState, useEffect } from 'react';
import {
  Calendar,
  Coins,
  Download,
  FileText,
  Printer,
  RefreshCw,
  X,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import apiClient from '../../api/client';
import type { Partner, PartnerStatementResponse } from '../../api/types';

interface PartnerStatementModalProps {
  isOpen: boolean;
  onClose: () => void;
  companyId: number;
  partner: Partner | null;
}

export default function PartnerStatementModal({
  isOpen,
  onClose,
  companyId,
  partner,
}: PartnerStatementModalProps) {
  const { t, language } = useI18n();

  const [dateFrom, setDateFrom] = useState<string>(() => {
    const d = new Date();
    d.setMonth(d.getMonth() - 1);
    return d.toISOString().split('T')[0];
  });
  const [dateTo, setDateTo] = useState<string>(() => new Date().toISOString().split('T')[0]);
  const [currency, setCurrency] = useState<string>(partner?.currency || 'USD');
  const [statement, setStatement] = useState<PartnerStatementResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (partner) {
      setCurrency(partner.currency);
    }
  }, [partner]);

  const fetchStatement = async () => {
    if (!companyId || !partner || !currency) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<PartnerStatementResponse>(
        `/partners/${partner.id}/statement?company_id=${companyId}&date_from=${dateFrom}&date_to=${dateTo}&currency=${currency}`
      );
      setStatement(res.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.common.somethingWentWrong);
      setStatement(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && partner) {
      fetchStatement();
    }
  }, [isOpen, partner, dateFrom, dateTo, currency]);

  if (!isOpen || !partner) return null;

  const formatAmount = (val: string | number) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat(language === 'ar' ? 'ar-SA' : 'en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num || 0);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleExportCsv = () => {
    if (!statement) return;
    const headers = [
      t.partnerStatement.dateCol,
      t.partnerStatement.typeCol,
      t.partnerStatement.docNoCol,
      t.partnerStatement.descriptionCol,
      t.partnerStatement.debitCol,
      t.partnerStatement.creditCol,
      t.partnerStatement.runningBalanceCol,
    ];

    const rows = statement.transactions.map((tx) => [
      tx.date,
      tx.type,
      `"${tx.document_no}"`,
      `"${tx.description || ''}"`,
      tx.debit,
      tx.credit,
      tx.running_balance,
    ]);

    const csvContent = [
      `Partner: ${statement.partner_name} (${statement.partner_code})`,
      `Currency: ${statement.currency}`,
      `Date Range: ${statement.date_from} to ${statement.date_to}`,
      `Opening Balance: ${statement.opening_balance}`,
      `Closing Balance: ${statement.closing_balance}`,
      '',
      headers.join(','),
      ...rows.map((r) => r.join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute(
      'download',
      `statement_${statement.partner_code}_${statement.date_from}_${statement.date_to}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-neutral-950 rounded-2xl border border-neutral-200 dark:border-neutral-800 shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-primary/10 text-primary rounded-xl">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-neutral-900 dark:text-white">
                {t.partnerStatement.modalTitle}: {partner.name}
              </h2>
              <div className="flex items-center gap-2 text-xs text-neutral-500 font-mono mt-0.5">
                <span>{partner.code}</span>
                <span>•</span>
                <span className="font-semibold text-primary">{currency}</span>
                <span>•</span>
                <span>
                  {partner.is_customer && partner.is_vendor
                    ? `${t.partnerStatement.customerLabel} & ${t.partnerStatement.vendorLabel}`
                    : partner.is_customer
                    ? t.partnerStatement.customerLabel
                    : t.partnerStatement.vendorLabel}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="btn btn-secondary inline-flex items-center gap-1.5 text-xs py-1.5 px-3"
              title={t.partnerStatement.print}
            >
              <Printer className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{t.partnerStatement.print}</span>
            </button>
            <button
              onClick={handleExportCsv}
              className="btn btn-secondary inline-flex items-center gap-1.5 text-xs py-1.5 px-3"
              title={t.partnerStatement.exportCsv}
            >
              <Download className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{t.partnerStatement.exportCsv}</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Filter Controls Bar */}
        <div className="p-4 bg-neutral-50 dark:bg-neutral-900/30 border-b border-neutral-200 dark:border-neutral-800 grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1">
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {t.partnerStatement.dateFrom}
              </span>
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="input w-full text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1">
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {t.partnerStatement.dateTo}
              </span>
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="input w-full text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1">
              <span className="inline-flex items-center gap-1">
                <Coins className="h-3 w-3" />
                {t.partnerStatement.currency}
              </span>
            </label>
            <input
              type="text"
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              maxLength={3}
              className="input w-full text-xs font-mono uppercase"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={() => fetchStatement()}
              disabled={loading}
              className="btn btn-secondary w-full inline-flex items-center justify-center gap-1.5 text-xs py-2"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>{t.common.refresh}</span>
            </button>
          </div>
        </div>

        {/* Summary Metric Cards */}
        {statement && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950">
            <div className="bg-neutral-50 dark:bg-neutral-900 p-3 rounded-xl border border-neutral-200 dark:border-neutral-800">
              <span className="text-xs text-neutral-500 font-medium">
                {t.partnerStatement.openingBalance}
              </span>
              <div className="text-base font-bold font-mono text-neutral-900 dark:text-white mt-1">
                {formatAmount(statement.opening_balance)} {statement.currency}
              </div>
            </div>

            <div className="bg-neutral-50 dark:bg-neutral-900 p-3 rounded-xl border border-neutral-200 dark:border-neutral-800">
              <span className="text-xs text-neutral-500 font-medium">
                {t.partnerStatement.totalDebit}
              </span>
              <div className="text-base font-bold font-mono text-neutral-900 dark:text-white mt-1">
                {formatAmount(statement.total_debit)} {statement.currency}
              </div>
            </div>

            <div className="bg-neutral-50 dark:bg-neutral-900 p-3 rounded-xl border border-neutral-200 dark:border-neutral-800">
              <span className="text-xs text-neutral-500 font-medium">
                {t.partnerStatement.totalCredit}
              </span>
              <div className="text-base font-bold font-mono text-neutral-900 dark:text-white mt-1">
                {formatAmount(statement.total_credit)} {statement.currency}
              </div>
            </div>

            <div className="bg-primary/10 p-3 rounded-xl border border-primary/30">
              <span className="text-xs text-primary font-semibold">
                {t.partnerStatement.closingBalance}
              </span>
              <div className="text-base font-extrabold font-mono text-primary mt-1">
                {formatAmount(statement.closing_balance)} {statement.currency}
              </div>
            </div>
          </div>
        )}

        {/* Statement Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="p-12 text-center text-sm text-neutral-500">
              {t.common.loading}
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-300 text-sm">
              {error}
            </div>
          ) : !statement || statement.transactions.length === 0 ? (
            <div className="p-12 text-center text-sm text-neutral-500">
              {t.partnerStatement.noTransactions}
            </div>
          ) : (
            <div className="border border-neutral-200 dark:border-neutral-800 rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50 text-neutral-500 font-medium">
                    <th className="py-2.5 px-3">{t.partnerStatement.dateCol}</th>
                    <th className="py-2.5 px-3">{t.partnerStatement.typeCol}</th>
                    <th className="py-2.5 px-3">{t.partnerStatement.docNoCol}</th>
                    <th className="py-2.5 px-3">{t.partnerStatement.descriptionCol}</th>
                    <th className="py-2.5 px-3 text-right">{t.partnerStatement.debitCol}</th>
                    <th className="py-2.5 px-3 text-right">{t.partnerStatement.creditCol}</th>
                    <th className="py-2.5 px-3 text-right font-bold">{t.partnerStatement.runningBalanceCol}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                  {/* Opening Balance Row */}
                  <tr className="bg-neutral-50/30 dark:bg-neutral-900/30 font-semibold italic text-neutral-500">
                    <td className="py-2 px-3">{statement.date_from}</td>
                    <td className="py-2 px-3" colSpan={3}>
                      {t.partnerStatement.openingBalance}
                    </td>
                    <td className="py-2 px-3 text-right font-mono">—</td>
                    <td className="py-2 px-3 text-right font-mono">—</td>
                    <td className="py-2 px-3 text-right font-mono text-neutral-900 dark:text-white">
                      {formatAmount(statement.opening_balance)}
                    </td>
                  </tr>

                  {/* Transaction Rows */}
                  {statement.transactions.map((tx, idx) => (
                    <tr
                      key={idx}
                      className="hover:bg-neutral-50/50 dark:hover:bg-neutral-900/50 transition-colors"
                    >
                      <td className="py-2.5 px-3 font-mono text-neutral-600 dark:text-neutral-400">
                        {tx.date}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            tx.type === 'invoice'
                              ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                              : 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                          }`}
                        >
                          {tx.type === 'invoice'
                            ? partner.is_customer
                              ? t.partnerStatement.invoiceType
                              : t.partnerStatement.billType
                            : partner.is_customer
                            ? t.partnerStatement.receiptType
                            : t.partnerStatement.paymentType}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono font-semibold text-neutral-800 dark:text-neutral-200">
                        {tx.document_no}
                      </td>
                      <td className="py-2.5 px-3 text-neutral-600 dark:text-neutral-400 max-w-xs truncate">
                        {tx.description || tx.reference || '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-neutral-800 dark:text-neutral-200">
                        {parseFloat(String(tx.debit)) > 0 ? formatAmount(tx.debit) : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-neutral-800 dark:text-neutral-200">
                        {parseFloat(String(tx.credit)) > 0 ? formatAmount(tx.credit) : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-neutral-900 dark:text-white">
                        {formatAmount(tx.running_balance)}
                      </td>
                    </tr>
                  ))}

                  {/* Closing Balance Row */}
                  <tr className="bg-primary/5 dark:bg-primary/10 font-bold text-primary">
                    <td className="py-2.5 px-3">{statement.date_to}</td>
                    <td className="py-2.5 px-3" colSpan={3}>
                      {t.partnerStatement.closingBalance}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono">
                      {formatAmount(statement.total_debit)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono">
                      {formatAmount(statement.total_credit)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-extrabold text-primary">
                      {formatAmount(statement.closing_balance)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
