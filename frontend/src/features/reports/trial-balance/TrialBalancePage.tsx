import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import PageLayout from '../../../components/layout/PageLayout';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import AccountTypeBadge from '../../accounts/AccountTypeBadge';
import { useTrialBalance } from './useTrialBalance';
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
} from 'lucide-react';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(n);
}

export default function TrialBalancePage() {
  return (
    <PageLayout
      pageTitle="Trial Balance"
      pageSubtitle="Verify that total debit and credit balances remain aligned"
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
  const [asOfDate, setAsOfDate] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

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
                    <h1 className="text-2xl font-bold text-white">Trial Balance</h1>
                    <p className="text-sm text-gray-400">
                      {data.as_of_date
                        ? `As of ${new Date(data.as_of_date).toLocaleDateString()}`
                        : 'All-time balances'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {data.is_balanced ? (
                    <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-semibold">
                      <CheckCircle2 className="w-4 h-4" />
                      Balanced
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-semibold">
                      <XCircle className="w-4 h-4" />
                      Unbalanced
                    </span>
                  )}
                </div>
              </div>

              {/* Totals grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowDownRight className="w-3.5 h-3.5 text-emerald-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Total Debit</p>
                  </div>
                  <p className="text-xl font-bold text-emerald-400 tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_debit))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowUpRight className="w-3.5 h-3.5 text-red-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Total Credit</p>
                  </div>
                  <p className="text-xl font-bold text-red-400 tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_credit))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowDownRight className="w-3.5 h-3.5 text-blue-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Debit Balance</p>
                  </div>
                  <p className="text-xl font-bold text-white tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_debit_balance))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowUpRight className="w-3.5 h-3.5 text-violet-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Credit Balance</p>
                  </div>
                  <p className="text-xl font-bold text-white tracking-tight font-mono">
                    {formatCurrency(parseAmount(data.total_credit_balance))}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

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
                placeholder="Search by account code, name, or type..."
                className="input-field pl-10 text-sm"
              />
            </div>

            {/* Line count */}
            <div className="flex items-center px-3">
              <span className="text-xs text-gray-500 font-medium whitespace-nowrap">
                {filteredLines.length} of {data.lines.length} account{data.lines.length !== 1 ? 's' : ''}
              </span>
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
              <p className="text-gray-400 text-sm">No accounts match your search.</p>
              <button
                onClick={() => setSearchQuery('')}
                className="mt-3 text-brand-400 text-xs font-medium hover:text-brand-300 transition-colors"
              >
                Clear search
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
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Code</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Account Name</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Type</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Debit Total</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Credit Total</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Debit Balance</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Credit Balance</th>
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
                          <span className="text-sm font-semibold text-white">Totals</span>
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
                  <p className="text-xs font-semibold text-white mb-2">Totals</p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Debit</p>
                      <p className="text-sm font-mono font-semibold text-emerald-400">{formatCurrency(parseAmount(data.total_debit))}</p>
                    </div>
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Credit</p>
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
