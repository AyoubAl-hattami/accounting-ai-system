import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import PageLayout from '../../../components/layout/PageLayout';
import ChartCard from '../../../components/charts/ChartCard';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import { AccountTypeBadge } from '../../../entities/account';
import { useTrialBalance } from './useTrialBalance';
import { useI18n } from '../../../i18n';
import { formatCurrency } from '../../../lib/format';
import {
  BarChart3,
  CheckCircle2,
  XCircle,
  Search,
  Calendar,
  X,
  ArrowDownRight,
  ArrowUpRight,
  Download,
  FileDown,
} from 'lucide-react';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(n);
}

export default function TrialBalancePage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.reports.trialBalance.pageTitle}
      pageSubtitle={t.reports.trialBalance.pageSubtitle}
      activePath="/reports/trial-balance"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <TrialBalanceContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface TrialBalanceContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function TrialBalanceContent({ selectedCompanyId, companiesLoading }: TrialBalanceContentProps) {
  const { t } = useI18n();
  const [asOfDate, setAsOfDate] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  const {
    data,
    isLoading: reportLoading,
    error,
    fetchReport,
  } = useTrialBalance({ companyId: selectedCompanyId, asOfDate });

  // Fetch on mount and when company/date changes
  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Reset filters on company change
  useEffect(() => {
    setSearchQuery('');
  }, [selectedCompanyId]);

  // Client-side search
  const filteredLines = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.lines;
    const q = searchQuery.toLowerCase();
    return data.lines.filter(
      (l) =>
        l.account_code.toLowerCase().includes(q) ||
        l.account_name.toLowerCase().includes(q) ||
        l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const isLoading = companiesLoading || reportLoading;

  const handleExportCsv = async () => {
    if (!selectedCompanyId) return;
    setExporting(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/trial-balance/export.csv', {
        company_id: selectedCompanyId,
        as_of_date: asOfDate,
      }, 'trial-balance.csv');
    } catch {
      alert(t.common.exportFailed);
    } finally {
      setExporting(false);
    }
  };

  const handleExportPdf = async () => {
    if (!selectedCompanyId) return;
    setExportingPdf(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/trial-balance/export.pdf', {
        company_id: selectedCompanyId,
        as_of_date: asOfDate,
      }, 'trial-balance.pdf');
    } catch {
      alert(t.common.pdfExportFailed);
    } finally {
      setExportingPdf(false);
    }
  };

  return (
    <>
      {isLoading && <LoadingState />}

      {!isLoading && error && <ErrorState message={error} onRetry={fetchReport} />}

      {!isLoading && !error && data && (
        <>
          {/* Hero panel */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="glass-panel relative overflow-hidden mb-6"
          >
            <div className="absolute top-0 right-0 w-72 h-72 bg-brand-500/[0.04] rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
            <div className="relative p-6 lg:p-8">
              {/* Title + Status row */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-500/20">
                    <BarChart3 className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-white">{t.reports.trialBalance.pageTitle}</h1>
                    <p className="text-sm text-gray-400">
                      {data.as_of_date
                        ? `${t.common.through} ${new Date(data.as_of_date).toLocaleDateString()}`
                        : t.common.allTime}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {data.is_balanced ? (
                    <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-semibold">
                      <CheckCircle2 className="w-4 h-4" />
                      {t.reports.trialBalance.balanced}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-semibold">
                      <XCircle className="w-4 h-4" />
                      {t.reports.trialBalance.unbalanced}
                    </span>
                  )}
                </div>
              </div>

              {/* Totals grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowDownRight className="w-3.5 h-3.5 text-emerald-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.common.debitTotal}</p>
                  </div>
                  <p className="text-xl font-bold text-emerald-400 tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_debit))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowUpRight className="w-3.5 h-3.5 text-red-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.common.creditTotal}</p>
                  </div>
                  <p className="text-xl font-bold text-red-400 tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_credit))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowDownRight className="w-3.5 h-3.5 text-blue-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.trialBalance.debitBalance}</p>
                  </div>
                  <p className="text-xl font-bold text-white tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_debit_balance))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowUpRight className="w-3.5 h-3.5 text-violet-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.trialBalance.creditBalance}</p>
                  </div>
                  <p className="text-xl font-bold text-white tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_credit_balance))}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Top Account Balances chart */}
          {data.lines.length > 0 && (
            <TopAccountsChart lines={data.lines} t={t} />
          )}

          {/* Toolbar: date + search */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="flex flex-col sm:flex-row gap-3 mb-6"
          >
            {/* Date picker */}
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="date"
                value={asOfDate || ''}
                onChange={(e) => setAsOfDate(e.target.value || null)}
                className="input-field pl-10 pr-10 text-sm min-w-[200px]"
                placeholder="As of date"
              />
              {asOfDate && (
                <button
                  onClick={() => setAsOfDate(null)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t.common.searchByAccountPlaceholder}
                className="input-field pl-10 text-sm"
              />
            </div>

            {/* Line count + Export */}
            <div className="flex items-center gap-3 px-3">
              <span className="text-xs text-gray-500 font-medium whitespace-nowrap">
                {filteredLines.length} of {data.lines.length} account{data.lines.length !== 1 ? 's' : ''}
              </span>
              <button
                onClick={handleExportCsv}
                disabled={exporting}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-semibold hover:bg-brand-500/20 transition-colors disabled:opacity-50"
              >
                <Download className="w-3.5 h-3.5" />
                {exporting ? t.common.exporting : t.common.exportCsv}
              </button>
              <button
                onClick={handleExportPdf}
                disabled={exportingPdf}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-semibold hover:bg-red-500/20 transition-colors disabled:opacity-50"
              >
                <FileDown className="w-3.5 h-3.5" />
                {exportingPdf ? t.common.exportingPdf : t.common.exportPdf}
              </button>
            </div>
          </motion.div>

          {/* Empty state */}
          {data.lines.length === 0 && (
            <EmptyState
              icon={<BarChart3 className="w-7 h-7 text-brand-400" />}
              title="No Trial Balance Data"
              description="There are no account balances to display. Create journal entries to see the trial balance."
            />
          )}

          {/* Search-empty state */}
          {data.lines.length > 0 && filteredLines.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-16">
              <Search className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">{t.common.noAccountsMatch}</p>
              <button
                onClick={() => setSearchQuery('')}
                className="mt-3 text-brand-400 text-xs font-medium hover:text-brand-300 transition-colors"
              >
                {t.common.clearSearch}
              </button>
            </motion.div>
          )}

          {/* Lines table */}
          {filteredLines.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.15 }}
            >
              {/* Desktop table */}
              <div className="hidden md:block glass-panel overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/[0.06]">
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.common.code}</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.reports.trialBalance.accountName}</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.common.type}</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.common.debitTotal}</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.common.creditTotal}</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.reports.trialBalance.debitBalance}</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.reports.trialBalance.creditBalance}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredLines.map((line, i) => (
                        <motion.tr
                          key={line.account_id}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: i * 0.02 }}
                          className="border-b border-white/[0.03] last:border-0 hover:bg-white/[0.02] transition-colors"
                        >
                          <td className="px-4 py-3">
                            <span className="text-sm font-mono font-semibold text-brand-400">{line.account_code}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm text-gray-200">{line.account_name}</span>
                          </td>
                          <td className="px-4 py-3">
                            <AccountTypeBadge type={line.account_type} />
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-sm font-mono text-emerald-400">{fmtAmt(line.debit_total)}</span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-sm font-mono text-red-400">{fmtAmt(line.credit_total)}</span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className={`text-sm font-mono ${parseAmount(line.debit_balance) > 0 ? 'text-white' : 'text-gray-600'}`}>
                              {fmtAmt(line.debit_balance)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className={`text-sm font-mono ${parseAmount(line.credit_balance) > 0 ? 'text-white' : 'text-gray-600'}`}>
                              {fmtAmt(line.credit_balance)}
                            </span>
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                    {/* Footer totals */}
                    <tfoot>
                      <tr className="border-t border-white/[0.08] bg-white/[0.02]">
                        <td className="px-4 py-3" colSpan={3}>
                          <span className="text-sm font-semibold text-white">{t.reports.trialBalance.totals}</span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-sm font-mono font-semibold text-emerald-400">
                            {formatCurrency(parseAmount(data.total_debit))}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-sm font-mono font-semibold text-red-400">
                            {formatCurrency(parseAmount(data.total_credit))}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-sm font-mono font-semibold text-white">
                            {formatCurrency(parseAmount(data.total_debit_balance))}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-sm font-mono font-semibold text-white">
                            {formatCurrency(parseAmount(data.total_credit_balance))}
                          </span>
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Mobile cards */}
              <div className="md:hidden space-y-3">
                {filteredLines.map((line, i) => (
                  <motion.div
                    key={line.account_id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="glass-panel p-4"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <span className="text-xs font-mono font-semibold text-brand-400">{line.account_code}</span>
                        <h4 className="text-sm font-medium text-white mt-0.5">{line.account_name}</h4>
                      </div>
                      <AccountTypeBadge type={line.account_type} />
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-3">
                      <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Dr Total</p>
                        <p className="text-xs font-mono text-emerald-400">{fmtAmt(line.debit_total)}</p>
                      </div>
                      <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Cr Total</p>
                        <p className="text-xs font-mono text-red-400">{fmtAmt(line.credit_total)}</p>
                      </div>
                      <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Dr Balance</p>
                        <p className={`text-xs font-mono ${parseAmount(line.debit_balance) > 0 ? 'text-white' : 'text-gray-600'}`}>
                          {fmtAmt(line.debit_balance)}
                        </p>
                      </div>
                      <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Cr Balance</p>
                        <p className={`text-xs font-mono ${parseAmount(line.credit_balance) > 0 ? 'text-white' : 'text-gray-600'}`}>
                          {fmtAmt(line.credit_balance)}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                ))}

                {/* Mobile totals footer */}
                <div className="glass-panel p-4 border-brand-500/20">
                  <p className="text-xs font-semibold text-white mb-2">{t.reports.trialBalance.totals}</p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.trialBalance.debit}</p>
                      <p className="text-sm font-mono font-semibold text-emerald-400">{formatCurrency(parseAmount(data.total_debit))}</p>
                    </div>
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.trialBalance.credit}</p>
                      <p className="text-sm font-mono font-semibold text-red-400">{formatCurrency(parseAmount(data.total_credit))}</p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </>
      )}
    </>
  );
}

// ── Top Accounts horizontal bar chart ──
import type { TrialBalanceLine } from '../../../api/types';
import type { Translations } from '../../../i18n/types';

function TopAccountsChart({ lines, t }: { lines: TrialBalanceLine[]; t: Translations }) {
  const chartData = useMemo(() => {
    return [...lines]
      .map((l) => ({
        name: `${l.account_code} ${l.account_name}`.slice(0, 28),
        debit: parseAmount(l.debit_balance),
        credit: parseAmount(l.credit_balance),
      }))
      .filter((a) => a.debit !== 0 || a.credit !== 0)
      .sort((a, b) => Math.max(b.debit, b.credit) - Math.max(a.debit, a.credit))
      .slice(0, 10);
  }, [lines]);

  if (chartData.length === 0) return null;

  return (
    <ChartCard
      title={t.charts.topAccountBalances}
      delay={0.15}
      height={Math.max(200, chartData.length * 36)}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 20, left: 8, bottom: 4 }} barSize={14}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
          <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
          <YAxis dataKey="name" type="category" tick={{ fill: '#d1d5db', fontSize: 10 }} axisLine={false} tickLine={false} width={150} />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            contentStyle={{ background: 'rgba(17,24,39,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
            itemStyle={{ color: '#e5e7eb' }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any) => Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          />
          <Bar dataKey="debit" name={t.charts.debit} fill="#34d399" radius={[0, 4, 4, 0]} />
          <Bar dataKey="credit" name={t.charts.credit} fill="#818cf8" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
