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
  Cell,
} from 'recharts';
import PageLayout from '../../../components/layout/PageLayout';
import ChartCard from '../../../components/charts/ChartCard';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import { AccountTypeBadge } from '../../../entities/account';
import { useBalanceSheet } from './useBalanceSheet';
import { useI18n } from '../../../i18n';
import { formatCurrency } from '../../../lib/format';
import type { BalanceSheetLine } from '../../../api/types';
import {
  Scale,
  CheckCircle2,
  XCircle,
  Search,
  Calendar,
  X,
  Landmark,
  HandCoins,
  Gem,
  TrendingUp,
  TrendingDown,
  Equal,
  Download,
  FileDown,
} from 'lucide-react';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(Math.abs(n));
}

export default function BalanceSheetPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.reports.balanceSheet.pageTitle}
      pageSubtitle={t.reports.balanceSheet.pageSubtitle}
      activePath="/reports/balance-sheet"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <BalanceSheetContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface BalanceSheetContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function BalanceSheetContent({ selectedCompanyId, companiesLoading }: BalanceSheetContentProps) {
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
  } = useBalanceSheet({ companyId: selectedCompanyId, asOfDate });

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    setSearchQuery('');
  }, [selectedCompanyId]);

  // Client-side search — inlined into useMemo for correct deps
  const filteredAssets = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.asset_lines;
    const q = searchQuery.toLowerCase();
    return data.asset_lines.filter(
      (l) => l.account_code.toLowerCase().includes(q) || l.account_name.toLowerCase().includes(q) || l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const filteredLiabilities = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.liability_lines;
    const q = searchQuery.toLowerCase();
    return data.liability_lines.filter(
      (l) => l.account_code.toLowerCase().includes(q) || l.account_name.toLowerCase().includes(q) || l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const filteredEquity = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.equity_lines;
    const q = searchQuery.toLowerCase();
    return data.equity_lines.filter(
      (l) => l.account_code.toLowerCase().includes(q) || l.account_name.toLowerCase().includes(q) || l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const totalFiltered = filteredAssets.length + filteredLiabilities.length + filteredEquity.length;
  const totalLines = data ? data.asset_lines.length + data.liability_lines.length + data.equity_lines.length : 0;

  const isLoading = companiesLoading || reportLoading;

  const handleExportCsv = async () => {
    if (!selectedCompanyId) return;
    setExporting(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/balance-sheet/export.csv', {
        company_id: selectedCompanyId,
        as_of_date: asOfDate,
      }, 'balance-sheet.csv');
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
      await downloadFile('/reports/balance-sheet/export.pdf', {
        company_id: selectedCompanyId,
        as_of_date: asOfDate,
      }, 'balance-sheet.pdf');
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
              {/* Title + Status */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-violet-700 flex items-center justify-center shadow-lg shadow-violet-500/20">
                    <Scale className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-white">{t.reports.balanceSheet.pageTitle}</h1>
                    <p className="text-sm text-gray-400">
                      {data.as_of_date
                        ? `${t.common.through} ${new Date(data.as_of_date).toLocaleDateString()}`
                        : t.common.allTime}
                    </p>
                  </div>
                </div>
                <div>
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
              <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Landmark className="w-3.5 h-3.5 text-blue-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.balanceSheet.totalAssets}</p>
                  </div>
                  <p className="text-xl font-bold text-blue-400 tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_assets))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <HandCoins className="w-3.5 h-3.5 text-amber-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.balanceSheet.liabilities}</p>
                  </div>
                  <p className="text-xl font-bold text-amber-400 tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_liabilities))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Gem className="w-3.5 h-3.5 text-violet-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.balanceSheet.equityAccountsTotal}</p>
                  </div>
                  <p className="text-xl font-bold text-violet-400 tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.equity_accounts_total))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    {parseAmount(data.retained_earnings) >= 0
                      ? <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
                      : <TrendingDown className="w-3.5 h-3.5 text-red-400" />
                    }
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.balanceSheet.retainedEarnings}</p>
                  </div>
                  <p className={`text-xl font-bold tracking-tight font-mono ${parseAmount(data.retained_earnings) >= 0 ? 'text-cyan-400' : 'text-red-400'}`}>
                    {parseAmount(data.retained_earnings) < 0 ? '−' : ''}{formatCurrency(Math.abs(parseAmount(data.retained_earnings)))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    {parseAmount(data.current_year_earnings) >= 0
                      ? <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                      : <TrendingDown className="w-3.5 h-3.5 text-red-400" />
                    }
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.balanceSheet.currentYearEarnings}</p>
                  </div>
                  <p className={`text-xl font-bold tracking-tight font-mono ${parseAmount(data.current_year_earnings) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {parseAmount(data.current_year_earnings) < 0 ? '−' : ''}{formatCurrency(Math.abs(parseAmount(data.current_year_earnings)))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Equal className="w-3.5 h-3.5 text-gray-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.reports.balanceSheet.totalEquity}</p>
                  </div>
                  <p className="text-xl font-bold text-white tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_equity))}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Accounting equation */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.08 }}
            className="glass-panel p-4 mb-6"
          >
            <div className="flex flex-wrap items-center justify-center gap-3 text-sm">
              <div className="flex items-center gap-2">
                <Landmark className="w-4 h-4 text-blue-400" />
                <span className="text-gray-400">{t.reports.balanceSheet.assets}</span>
                <span className="font-mono font-bold text-blue-400">{formatCurrency(parseAmount(data.total_assets))}</span>
              </div>
              <span className="text-gray-600 font-bold">=</span>
              <div className="flex items-center gap-2">
                <HandCoins className="w-4 h-4 text-amber-400" />
                <span className="text-gray-400">{t.reports.balanceSheet.liabilities}</span>
                <span className="font-mono font-bold text-amber-400">{formatCurrency(parseAmount(data.total_liabilities))}</span>
              </div>
              <span className="text-gray-600 font-bold">+</span>
              <div className="flex items-center gap-2">
                <Gem className="w-4 h-4 text-violet-400" />
                <span className="text-gray-400">{t.reports.balanceSheet.equityAccountsTotal}</span>
                <span className="font-mono font-bold text-violet-400">{formatCurrency(parseAmount(data.equity_accounts_total))}</span>
              </div>
              <span className="text-gray-600 font-bold">+</span>
              <div className="flex items-center gap-2">
                {parseAmount(data.retained_earnings) >= 0
                  ? <TrendingUp className="w-4 h-4 text-cyan-400" />
                  : <TrendingDown className="w-4 h-4 text-red-400" />
                }
                <span className="text-gray-400">{t.reports.balanceSheet.retainedEarnings}</span>
                <span className={`font-mono font-bold ${parseAmount(data.retained_earnings) >= 0 ? 'text-cyan-400' : 'text-red-400'}`}>
                  {parseAmount(data.retained_earnings) < 0 ? '−' : ''}{formatCurrency(Math.abs(parseAmount(data.retained_earnings)))}
                </span>
              </div>
              <span className="text-gray-600 font-bold">+</span>
              <div className="flex items-center gap-2">
                {parseAmount(data.current_year_earnings) >= 0
                  ? <TrendingUp className="w-4 h-4 text-emerald-400" />
                  : <TrendingDown className="w-4 h-4 text-red-400" />
                }
                <span className="text-gray-400">{t.reports.balanceSheet.currentYearEarnings}</span>
                <span className={`font-mono font-bold ${parseAmount(data.current_year_earnings) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {parseAmount(data.current_year_earnings) < 0 ? '−' : ''}{formatCurrency(Math.abs(parseAmount(data.current_year_earnings)))}
                </span>
              </div>
            </div>
          </motion.div>

          {/* Balance Sheet composition chart */}
          <BSChart data={data} t={t} />

          {/* Toolbar: date + search */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.12 }}
            className="flex flex-col sm:flex-row gap-3 mb-6"
          >
            {/* As of date */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1.5">{t.common.asOfDate}</label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="date"
                  value={asOfDate || ''}
                  onChange={(e) => setAsOfDate(e.target.value || null)}
                  className="input-field pl-10 pr-10 text-sm min-w-[200px]"
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
            </div>

            {/* Search */}
            <div className="flex-1">
              <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1.5 sm:invisible">{t.common.search}</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t.common.searchByAccountPlaceholder}
                  className="input-field pl-10 text-sm"
                />
              </div>
            </div>

            <div className="flex items-end gap-3 px-3 pb-1">
              <span className="text-xs text-gray-500 font-medium whitespace-nowrap">
                {totalFiltered} of {totalLines} account{totalLines !== 1 ? 's' : ''}
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
          {totalLines === 0 && (
            <EmptyState
              icon={<Scale className="w-7 h-7 text-brand-400" />}
              title="No Balance Sheet Data"
              description="There are no account balances to display. Create journal entries to see the balance sheet."
            />
          )}

          {/* Search-empty state */}
          {totalLines > 0 && totalFiltered === 0 && (
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

          {/* Sectioned breakdown */}
          {totalFiltered > 0 && (
            <div className="space-y-6">
              {/* Assets */}
              <SectionTable
                title={t.reports.balanceSheet.assets}
                icon={<Landmark className="w-4 h-4 text-blue-400" />}
                dotColor="bg-blue-400"
                amountColor="text-blue-400"
                lines={filteredAssets}
                totalLabel={t.reports.balanceSheet.totalAssets}
                totalAmount={data.total_assets}
                delay={0.15}
                searchQuery={searchQuery}
              />

              {/* Liabilities */}
              <SectionTable
                title={t.reports.balanceSheet.liabilities}
                icon={<HandCoins className="w-4 h-4 text-amber-400" />}
                dotColor="bg-amber-400"
                amountColor="text-amber-400"
                lines={filteredLiabilities}
                totalLabel={t.reports.balanceSheet.totalLiabilities}
                totalAmount={data.total_liabilities}
                delay={0.25}
                searchQuery={searchQuery}
              />

              {/* Equity */}
              <SectionTable
                title={t.reports.balanceSheet.equity}
                icon={<Gem className="w-4 h-4 text-violet-400" />}
                dotColor="bg-violet-400"
                amountColor="text-violet-400"
                lines={filteredEquity}
                totalLabel={t.reports.balanceSheet.equityAccountsTotal}
                totalAmount={data.equity_accounts_total}
                delay={0.35}
                searchQuery={searchQuery}
              />
            </div>
          )}
        </>
      )}
    </>
  );
}

// ── Section table component ──
interface SectionTableProps {
  title: string;
  icon: React.ReactNode;
  dotColor: string;
  amountColor: string;
  lines: BalanceSheetLine[];
  totalLabel: string;
  totalAmount: string;
  delay: number;
  searchQuery: string;
}

function SectionTable({ title, icon, dotColor, amountColor, lines, totalLabel, totalAmount, delay, searchQuery }: SectionTableProps) {
  const { t } = useI18n();
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-2 h-2 rounded-full ${dotColor}`} />
        {icon}
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        <span className="text-[10px] text-gray-500 font-medium ml-auto">
          {lines.length} account{lines.length !== 1 ? 's' : ''}
        </span>
      </div>

      {lines.length === 0 ? (
        <div className="glass-panel p-6 text-center">
          <p className="text-sm text-gray-500">No {title.toLowerCase()} accounts{searchQuery ? ' match your search' : ''}</p>
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block glass-panel overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.common.code}</th>
                  <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.common.account}</th>
                  <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.common.type}</th>
                  <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">{t.common.amount}</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line, i) => (
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
                      <span className={`text-sm font-mono ${amountColor}`}>{fmtAmt(line.amount)}</span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-white/[0.08] bg-white/[0.02]">
                  <td className="px-4 py-3" colSpan={3}>
                    <span className="text-sm font-semibold text-white">{totalLabel}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className={`text-sm font-mono font-semibold ${amountColor}`}>
                      {formatCurrency(parseAmount(totalAmount))}
                    </span>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-2">
            {lines.map((line, i) => (
              <motion.div
                key={line.account_id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="glass-panel p-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs font-mono font-semibold text-brand-400">{line.account_code}</span>
                    <h4 className="text-sm font-medium text-white mt-0.5">{line.account_name}</h4>
                  </div>
                  <AccountTypeBadge type={line.account_type} />
                </div>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.04]">
                  <span className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{t.common.amount}</span>
                  <span className={`text-sm font-mono font-semibold ${amountColor}`}>{fmtAmt(line.amount)}</span>
                </div>
              </motion.div>
            ))}
            <div className="glass-panel p-3 flex items-center justify-between">
              <span className="text-xs font-semibold text-white">{totalLabel}</span>
              <span className={`text-sm font-mono font-semibold ${amountColor}`}>
                {formatCurrency(parseAmount(totalAmount))}
              </span>
            </div>
          </div>
        </>
      )}
    </motion.div>
  );
}

// ── Balance Sheet composition chart ──
import type { Translations } from '../../../i18n/types';

function BSChart({ data, t }: { data: { total_assets: string; total_liabilities: string; equity_accounts_total: string; retained_earnings: string; current_year_earnings: string }; t: Translations }) {
  const parseAmt = (v: string) => parseFloat(v) || 0;

  const chartData = useMemo(() => {
    const assets = parseAmt(data.total_assets);
    const liab = parseAmt(data.total_liabilities);
    const equityAccounts = parseAmt(data.equity_accounts_total);
    const retained = parseAmt(data.retained_earnings);
    const cye = parseAmt(data.current_year_earnings);
    if (assets === 0 && liab === 0 && equityAccounts === 0 && retained === 0 && cye === 0) return [];
    const items = [
      { name: t.charts.assets, value: assets, fill: '#60a5fa' },
      { name: t.charts.liabilities, value: liab, fill: '#fbbf24' },
      { name: t.reports.balanceSheet.equityAccountsTotal, value: equityAccounts, fill: '#a78bfa' },
      { name: t.reports.balanceSheet.retainedEarnings, value: retained, fill: retained >= 0 ? '#22d3ee' : '#f87171' },
      { name: t.reports.balanceSheet.currentYearEarnings, value: cye, fill: cye >= 0 ? '#34d399' : '#f87171' },
    ];
    // Filter out zero values for a cleaner chart
    return items.filter((item) => item.value !== 0);
  }, [data, t]);

  if (chartData.length === 0) return null;

  return (
    <ChartCard title={t.charts.financialComposition} delay={0.15} height={220}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }} barSize={44}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            contentStyle={{ background: 'rgba(17,24,39,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
            itemStyle={{ color: '#e5e7eb' }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any) => Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
