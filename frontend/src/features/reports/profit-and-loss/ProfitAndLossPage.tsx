import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import PageLayout from '../../../components/layout/PageLayout';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import AccountTypeBadge from '../../accounts/AccountTypeBadge';
import { useProfitAndLoss } from './useProfitAndLoss';
import { formatCurrency } from '../../../lib/format';
import type { ProfitAndLossLine } from '../../../api/types';
import {
  FileText,
  TrendingUp,
  TrendingDown,
  Search,
  Calendar,
  X,
  ArrowUpRight,
  ArrowDownRight,
  DollarSign,
} from 'lucide-react';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(n);
}

export default function ProfitAndLossPage() {
  return (
    <PageLayout
      pageTitle="Profit & Loss"
      pageSubtitle="Track income, expenses, and net performance for the selected period"
      activePath="/reports/profit-and-loss"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <ProfitAndLossContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface ProfitAndLossContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function ProfitAndLossContent({ selectedCompanyId, companiesLoading }: ProfitAndLossContentProps) {
  const [startDate, setStartDate] = useState<string | null>(null);
  const [endDate, setEndDate] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const {
    data,
    isLoading: reportLoading,
    error,
    fetchReport,
  } = useProfitAndLoss({ companyId: selectedCompanyId, startDate, endDate });

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    setSearchQuery('');
  }, [selectedCompanyId]);

  // Client-side search across both income and expense lines
  const filteredIncome = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.income_lines;
    const q = searchQuery.toLowerCase();
    return data.income_lines.filter(
      (l) =>
        l.account_code.toLowerCase().includes(q) ||
        l.account_name.toLowerCase().includes(q) ||
        l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const filteredExpenses = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.expense_lines;
    const q = searchQuery.toLowerCase();
    return data.expense_lines.filter(
      (l) =>
        l.account_code.toLowerCase().includes(q) ||
        l.account_name.toLowerCase().includes(q) ||
        l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);
  const totalFiltered = filteredIncome.length + filteredExpenses.length;
  const totalLines = data ? data.income_lines.length + data.expense_lines.length : 0;

  const isLoading = companiesLoading || reportLoading;

  const clearDates = () => {
    setStartDate(null);
    setEndDate(null);
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
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                    <FileText className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-white">Profit & Loss</h1>
                    <p className="text-sm text-gray-400">
                      {data.start_date && data.end_date
                        ? `${new Date(data.start_date).toLocaleDateString()} — ${new Date(data.end_date).toLocaleDateString()}`
                        : data.start_date
                          ? `From ${new Date(data.start_date).toLocaleDateString()}`
                          : data.end_date
                            ? `Through ${new Date(data.end_date).toLocaleDateString()}`
                            : 'All-time performance'}
                    </p>
                  </div>
                </div>
                <div>
                  {parseAmount(data.net_profit) >= 0 ? (
                    <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-semibold">
                      <TrendingUp className="w-4 h-4" />
                      Net Profit
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-semibold">
                      <TrendingDown className="w-4 h-4" />
                      Net Loss
                    </span>
                  )}
                </div>
              </div>

              {/* Totals grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowDownRight className="w-3.5 h-3.5 text-emerald-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Total Income</p>
                  </div>
                  <p className="text-xl font-bold text-emerald-400 tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_income))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowUpRight className="w-3.5 h-3.5 text-red-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Total Expenses</p>
                  </div>
                  <p className="text-xl font-bold text-red-400 tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_expenses))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <DollarSign className={`w-3.5 h-3.5 ${parseAmount(data.net_profit) >= 0 ? 'text-emerald-400' : 'text-red-400'}`} />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Net Result</p>
                  </div>
                  <p className={`text-xl font-bold tracking-tight font-mono ${parseAmount(data.net_profit) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {parseAmount(data.net_profit) < 0 ? '−' : ''}{formatCurrency(Math.abs(parseAmount(data.net_profit)))}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Toolbar: dates + search */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="flex flex-col sm:flex-row gap-3 mb-6"
          >
            {/* Start date */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1.5">Start Date</label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="date"
                  value={startDate || ''}
                  onChange={(e) => setStartDate(e.target.value || null)}
                  className="input-field pl-10 text-sm min-w-[170px]"
                />
              </div>
            </div>

            {/* End date */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1.5">End Date</label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="date"
                  value={endDate || ''}
                  onChange={(e) => setEndDate(e.target.value || null)}
                  className="input-field pl-10 text-sm min-w-[170px]"
                />
              </div>
            </div>

            {/* Clear dates */}
            {(startDate || endDate) && (
              <button
                onClick={clearDates}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium text-gray-400 hover:text-gray-200 border border-white/[0.06] hover:border-white/[0.12] bg-white/[0.02] transition-all"
              >
                <X className="w-3.5 h-3.5" />
                Clear dates
              </button>
            )}

            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by account code, name, or type..."
                className="input-field pl-10 text-sm"
              />
            </div>

            <div className="flex items-center px-3">
              <span className="text-xs text-gray-500 font-medium whitespace-nowrap">
                {totalFiltered} of {totalLines} account{totalLines !== 1 ? 's' : ''}
              </span>
            </div>
          </motion.div>

          {/* Empty state */}
          {totalLines === 0 && (
            <EmptyState
              icon={<FileText className="w-7 h-7 text-brand-400" />}
              title="No Profit & Loss Data"
              description="There are no income or expense entries to display. Create journal entries to see the P&L report."
            />
          )}

          {/* Search-empty state */}
          {totalLines > 0 && totalFiltered === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-16">
              <Search className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No accounts match your search.</p>
              <button
                onClick={() => setSearchQuery('')}
                className="mt-3 text-brand-400 text-xs font-medium hover:text-brand-300 transition-colors"
              >
                Clear search
              </button>
            </motion.div>
          )}

          {/* Breakdown sections */}
          {totalFiltered > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Income section */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.15 }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                  <h2 className="text-sm font-semibold text-white">Income</h2>
                  <span className="text-[10px] text-gray-500 font-medium ml-auto">
                    {filteredIncome.length} account{filteredIncome.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {filteredIncome.length === 0 ? (
                  <div className="glass-panel p-6 text-center">
                    <p className="text-sm text-gray-500">No income accounts{searchQuery ? ' match your search' : ''}</p>
                  </div>
                ) : (
                  <>
                    {/* Desktop table */}
                    <div className="hidden md:block glass-panel overflow-hidden">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-white/[0.06]">
                            <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Code</th>
                            <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Account</th>
                            <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Type</th>
                            <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Amount</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredIncome.map((line, i) => (
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
                                <span className="text-sm font-mono text-emerald-400">{fmtAmt(line.amount)}</span>
                              </td>
                            </motion.tr>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="border-t border-white/[0.08] bg-white/[0.02]">
                            <td className="px-4 py-3" colSpan={3}>
                              <span className="text-sm font-semibold text-white">Total Income</span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className="text-sm font-mono font-semibold text-emerald-400">
                                {formatCurrency(parseAmount(data.total_income))}
                              </span>
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>

                    {/* Mobile cards */}
                    <div className="md:hidden space-y-2">
                      {filteredIncome.map((line, i) => (
                        <MobileLineCard key={line.account_id} line={line} color="emerald" index={i} />
                      ))}
                      <div className="glass-panel p-3 flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">Total Income</span>
                        <span className="text-sm font-mono font-semibold text-emerald-400">
                          {formatCurrency(parseAmount(data.total_income))}
                        </span>
                      </div>
                    </div>
                  </>
                )}
              </motion.div>

              {/* Expense section */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.25 }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full bg-red-400" />
                  <h2 className="text-sm font-semibold text-white">Expenses</h2>
                  <span className="text-[10px] text-gray-500 font-medium ml-auto">
                    {filteredExpenses.length} account{filteredExpenses.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {filteredExpenses.length === 0 ? (
                  <div className="glass-panel p-6 text-center">
                    <p className="text-sm text-gray-500">No expense accounts{searchQuery ? ' match your search' : ''}</p>
                  </div>
                ) : (
                  <>
                    {/* Desktop table */}
                    <div className="hidden md:block glass-panel overflow-hidden">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-white/[0.06]">
                            <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Code</th>
                            <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Account</th>
                            <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Type</th>
                            <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Amount</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredExpenses.map((line, i) => (
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
                                <span className="text-sm font-mono text-red-400">{fmtAmt(line.amount)}</span>
                              </td>
                            </motion.tr>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="border-t border-white/[0.08] bg-white/[0.02]">
                            <td className="px-4 py-3" colSpan={3}>
                              <span className="text-sm font-semibold text-white">Total Expenses</span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className="text-sm font-mono font-semibold text-red-400">
                                {formatCurrency(parseAmount(data.total_expenses))}
                              </span>
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>

                    {/* Mobile cards */}
                    <div className="md:hidden space-y-2">
                      {filteredExpenses.map((line, i) => (
                        <MobileLineCard key={line.account_id} line={line} color="red" index={i} />
                      ))}
                      <div className="glass-panel p-3 flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">Total Expenses</span>
                        <span className="text-sm font-mono font-semibold text-red-400">
                          {formatCurrency(parseAmount(data.total_expenses))}
                        </span>
                      </div>
                    </div>
                  </>
                )}
              </motion.div>
            </div>
          )}

          {/* Net result footer */}
          {totalFiltered > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.35 }}
              className="glass-panel p-6 mt-6"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    parseAmount(data.net_profit) >= 0
                      ? 'bg-emerald-500/10 border border-emerald-500/20'
                      : 'bg-red-500/10 border border-red-500/20'
                  }`}>
                    {parseAmount(data.net_profit) >= 0 ? (
                      <TrendingUp className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <TrendingDown className="w-5 h-5 text-red-400" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {parseAmount(data.net_profit) >= 0 ? 'Net Profit' : 'Net Loss'}
                    </p>
                    <p className="text-xs text-gray-500">Income minus expenses</p>
                  </div>
                </div>
                <p className={`text-2xl font-bold font-mono tracking-tight ${
                  parseAmount(data.net_profit) >= 0 ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {parseAmount(data.net_profit) < 0 ? '−' : ''}{formatCurrency(Math.abs(parseAmount(data.net_profit)))}
                </p>
              </div>
            </motion.div>
          )}
        </>
      )}
    </>
  );
}

// ── Mobile line card ──
interface MobileLineCardProps {
  line: ProfitAndLossLine;
  color: 'emerald' | 'red';
  index: number;
}

function MobileLineCard({ line, color, index }: MobileLineCardProps) {
  const amountColor = color === 'emerald' ? 'text-emerald-400' : 'text-red-400';

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
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
        <span className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Amount</span>
        <span className={`text-sm font-mono font-semibold ${amountColor}`}>{fmtAmt(line.amount)}</span>
      </div>
    </motion.div>
  );
}
