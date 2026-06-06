import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import PageLayout from '../../../components/layout/PageLayout';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import AccountTypeBadge from '../../accounts/AccountTypeBadge';
import { useAccountLedger } from './useAccountLedger';
import { formatCurrency } from '../../../lib/format';
import apiClient from '../../../api/client';
import type { Account, PaginatedResponse } from '../../../api/types';
import {
  BookMarked,
  Search,
  Calendar,
  X,
  ChevronsUpDown,
  ArrowDownRight,
  ArrowUpRight,
  Hash,
} from 'lucide-react';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(Math.abs(n));
}

const STORAGE_KEY = 'accounting-ai-selected-account';

export default function AccountLedgerPage() {
  return (
    <PageLayout
      pageTitle="Account Ledger"
      pageSubtitle="Review opening balance, activity, and running balance for an account"
      activePath="/reports/account-ledger"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <AccountLedgerContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface AccountLedgerContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function AccountLedgerContent({ selectedCompanyId, companiesLoading }: AccountLedgerContentProps) {
  // ── Account selector state ──
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? parseInt(saved, 10) : null;
  });
  const [selectorOpen, setSelectorOpen] = useState(false);

  // ── Date filters ──
  const [startDate, setStartDate] = useState<string | null>(null);
  const [endDate, setEndDate] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // ── Fetch accounts for selector ──
  useEffect(() => {
    if (!selectedCompanyId) return;
    let cancelled = false;
    setAccountsLoading(true);

    apiClient
      .get<PaginatedResponse<Account>>(
        `/accounts?company_id=${selectedCompanyId}&skip=0&limit=500`,
      )
      .then((res) => {
        if (cancelled) return;
        const items = res.data.items;
        setAccounts(items);
        // Auto-select first if current selection is invalid
        const ids = items.map((a) => a.id);
        setSelectedAccountId((prev) => {
          if (prev && ids.includes(prev)) return prev;
          const first = items[0]?.id || null;
          if (first) localStorage.setItem(STORAGE_KEY, String(first));
          else localStorage.removeItem(STORAGE_KEY);
          return first;
        });
      })
      .catch(() => {
        if (!cancelled) setAccounts([]);
      })
      .finally(() => {
        if (!cancelled) setAccountsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedCompanyId]);

  // ── Reset on company change ──
  useEffect(() => {
    setSearchQuery('');
    setStartDate(null);
    setEndDate(null);
    setSelectorOpen(false);
  }, [selectedCompanyId]);

  // ── Ledger hook ──
  const {
    data,
    isLoading: ledgerLoading,
    error,
    fetchReport,
  } = useAccountLedger({
    companyId: selectedCompanyId,
    accountId: selectedAccountId,
    startDate,
    endDate,
  });

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // ── Account select handler ──
  const handleSelectAccount = (id: number) => {
    setSelectedAccountId(id);
    localStorage.setItem(STORAGE_KEY, String(id));
    setSelectorOpen(false);
    setSearchQuery('');
  };

  // ── Computed values ──
  const selectedAccount = accounts.find((a) => a.id === selectedAccountId) || null;

  const totalDebits = useMemo(() => {
    if (!data) return 0;
    return data.lines.reduce((s, l) => s + parseAmount(l.debit), 0);
  }, [data]);

  const totalCredits = useMemo(() => {
    if (!data) return 0;
    return data.lines.reduce((s, l) => s + parseAmount(l.credit), 0);
  }, [data]);

  // ── Client-side search ──
  const filteredLines = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.lines;
    const q = searchQuery.toLowerCase();
    return data.lines.filter(
      (l) =>
        l.entry_no.toLowerCase().includes(q) ||
        (l.description && l.description.toLowerCase().includes(q)) ||
        l.entry_date.includes(q),
    );
  }, [data, searchQuery]);

  const isLoading = companiesLoading || accountsLoading || ledgerLoading;

  const clearDates = () => {
    setStartDate(null);
    setEndDate(null);
  };

  return (
    <>
      {isLoading && <LoadingState />}

      {!isLoading && error && <ErrorState message={error} onRetry={fetchReport} />}

      {!isLoading && !error && (
        <>
          {/* Account selector */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="mb-6"
          >
            <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1.5">Account</label>
            <div className="relative">
              <button
                onClick={() => setSelectorOpen(!selectorOpen)}
                className="w-full sm:w-auto min-w-[320px] flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-surface-800/60 border border-white/[0.06] hover:border-white/[0.12] text-left transition-all"
              >
                {selectedAccount ? (
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono font-semibold text-brand-400">{selectedAccount.code}</span>
                    <span className="text-sm text-gray-200">{selectedAccount.name}</span>
                    <AccountTypeBadge type={selectedAccount.account_type} />
                  </div>
                ) : (
                  <span className="text-sm text-gray-500">Select an account…</span>
                )}
                <ChevronsUpDown className="w-4 h-4 text-gray-500 flex-shrink-0" />
              </button>

              {selectorOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute z-50 mt-1 w-full sm:w-auto min-w-[320px] max-h-[280px] overflow-y-auto rounded-xl bg-surface-800 border border-white/[0.08] shadow-2xl shadow-black/40"
                >
                  {accounts.length === 0 ? (
                    <div className="px-4 py-6 text-center text-sm text-gray-500">No accounts available</div>
                  ) : (
                    accounts.map((acc) => (
                      <button
                        key={acc.id}
                        onClick={() => handleSelectAccount(acc.id)}
                        className={`w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-white/[0.04] transition-colors ${
                          acc.id === selectedAccountId ? 'bg-brand-500/10 border-l-2 border-brand-500' : 'border-l-2 border-transparent'
                        }`}
                      >
                        <span className="text-xs font-mono font-semibold text-brand-400 min-w-[50px]">{acc.code}</span>
                        <span className="text-sm text-gray-200 flex-1 truncate">{acc.name}</span>
                        <AccountTypeBadge type={acc.account_type} />
                      </button>
                    ))
                  )}
                </motion.div>
              )}
            </div>
          </motion.div>

          {/* No account selected state */}
          {!selectedAccountId && (
            <EmptyState
              icon={<BookMarked className="w-7 h-7 text-brand-400" />}
              title="Select an Account"
              description="Choose an account from the dropdown above to view its ledger."
            />
          )}

          {/* Ledger content */}
          {selectedAccountId && data && (
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
                  {/* Title row */}
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-500/20">
                        <BookMarked className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono font-semibold text-brand-400">{data.account_code}</span>
                          <AccountTypeBadge type={data.account_type} />
                        </div>
                        <h1 className="text-xl font-bold text-white">{data.account_name}</h1>
                      </div>
                    </div>
                    <p className="text-sm text-gray-400">
                      {data.start_date && data.end_date
                        ? `${new Date(data.start_date).toLocaleDateString()} — ${new Date(data.end_date).toLocaleDateString()}`
                        : data.start_date
                          ? `From ${new Date(data.start_date).toLocaleDateString()}`
                          : data.end_date
                            ? `Through ${new Date(data.end_date).toLocaleDateString()}`
                            : 'All-time activity'}
                    </p>
                  </div>

                  {/* Metrics grid */}
                  <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">Opening Balance</p>
                      <p className="text-lg font-bold text-white tracking-tight font-mono">
                        {formatCurrency(parseAmount(data.opening_balance))}
                      </p>
                    </div>
                    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <div className="flex items-center gap-1.5 mb-1">
                        <ArrowDownRight className="w-3 h-3 text-emerald-400" />
                        <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Total Debits</p>
                      </div>
                      <p className="text-lg font-bold text-emerald-400 tracking-tight font-mono">
                        {formatCurrency(totalDebits)}
                      </p>
                    </div>
                    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <div className="flex items-center gap-1.5 mb-1">
                        <ArrowUpRight className="w-3 h-3 text-red-400" />
                        <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Total Credits</p>
                      </div>
                      <p className="text-lg font-bold text-red-400 tracking-tight font-mono">
                        {formatCurrency(totalCredits)}
                      </p>
                    </div>
                    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">Closing Balance</p>
                      <p className={`text-lg font-bold tracking-tight font-mono ${parseAmount(data.closing_balance) >= 0 ? 'text-white' : 'text-red-400'}`}>
                        {parseAmount(data.closing_balance) < 0 ? '−' : ''}{formatCurrency(Math.abs(parseAmount(data.closing_balance)))}
                      </p>
                    </div>
                    <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <div className="flex items-center gap-1.5 mb-1">
                        <Hash className="w-3 h-3 text-gray-400" />
                        <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Entries</p>
                      </div>
                      <p className="text-lg font-bold text-white tracking-tight font-mono">
                        {data.lines.length}
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
                className="flex flex-wrap items-end gap-3 mb-6"
              >
                <div className="flex items-end gap-3">
                  <div>
                    <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1.5">Start Date</label>
                    <div className="relative">
                      <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                      <input
                        type="date"
                        value={startDate || ''}
                        onChange={(e) => setStartDate(e.target.value || null)}
                        className="input-field pl-10 text-sm min-w-[160px]"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1.5">End Date</label>
                    <div className="relative">
                      <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                      <input
                        type="date"
                        value={endDate || ''}
                        onChange={(e) => setEndDate(e.target.value || null)}
                        className="input-field pl-10 text-sm min-w-[160px]"
                      />
                    </div>
                  </div>
                  {(startDate || endDate) && (
                    <button
                      onClick={clearDates}
                      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium text-gray-400 hover:text-gray-200 border border-white/[0.06] hover:border-white/[0.12] bg-white/[0.02] transition-all h-[38px]"
                    >
                      <X className="w-3.5 h-3.5" />
                      Clear
                    </button>
                  )}
                </div>

                <div className="relative flex-1 min-w-[260px]">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by entry no, description, or date..."
                    className="input-field pl-10 text-sm"
                  />
                </div>

                <div className="flex items-center h-[38px] px-1">
                  <span className="text-xs text-gray-500 font-medium whitespace-nowrap">
                    {filteredLines.length} of {data.lines.length} entr{data.lines.length !== 1 ? 'ies' : 'y'}
                  </span>
                </div>
              </motion.div>

              {/* Empty state */}
              {data.lines.length === 0 && (
                <EmptyState
                  icon={<BookMarked className="w-7 h-7 text-brand-400" />}
                  title="No Ledger Activity"
                  description="This account has no journal entries. Create entries to see the ledger."
                />
              )}

              {/* Search-empty state */}
              {data.lines.length > 0 && filteredLines.length === 0 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-16">
                  <Search className="w-8 h-8 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400 text-sm">No entries match your search.</p>
                  <button
                    onClick={() => setSearchQuery('')}
                    className="mt-3 text-brand-400 text-xs font-medium hover:text-brand-300 transition-colors"
                  >
                    Clear search
                  </button>
                </motion.div>
              )}

              {/* Ledger table */}
              {filteredLines.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.15 }}
                >
                  {/* Desktop table */}
                  <div className="hidden lg:block glass-panel overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-white/[0.06]">
                            <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Date</th>
                            <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Entry No</th>
                            <th className="text-center text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Line</th>
                            <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Description</th>
                            <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Debit</th>
                            <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Credit</th>
                            <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Balance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {/* Opening balance row */}
                          <tr className="border-b border-white/[0.05] bg-white/[0.01]">
                            <td className="px-4 py-2.5" colSpan={4}>
                              <span className="text-xs font-medium text-gray-500 italic">Opening Balance</span>
                            </td>
                            <td className="px-4 py-2.5" colSpan={2} />
                            <td className="px-4 py-2.5 text-right">
                              <span className="text-sm font-mono font-semibold text-gray-300">{formatCurrency(parseAmount(data.opening_balance))}</span>
                            </td>
                          </tr>
                          {filteredLines.map((line, i) => {
                            const bal = parseAmount(line.running_balance);
                            return (
                              <motion.tr
                                key={`${line.journal_entry_id}-${line.line_no}`}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: i * 0.02 }}
                                className="border-b border-white/[0.03] last:border-0 hover:bg-white/[0.02] transition-colors"
                              >
                                <td className="px-4 py-3">
                                  <span className="text-sm text-gray-300">{new Date(line.entry_date).toLocaleDateString()}</span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className="text-sm font-mono font-semibold text-brand-400">{line.entry_no}</span>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <span className="text-xs text-gray-500">{line.line_no}</span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className="text-sm text-gray-200 truncate block max-w-[250px]">{line.description || '—'}</span>
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <span className="text-sm font-mono text-emerald-400">{fmtAmt(line.debit)}</span>
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <span className="text-sm font-mono text-red-400">{fmtAmt(line.credit)}</span>
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <span className={`text-sm font-mono font-semibold ${bal < 0 ? 'text-red-400' : 'text-white'}`}>
                                    {bal < 0 ? '−' : ''}{formatCurrency(Math.abs(bal))}
                                  </span>
                                </td>
                              </motion.tr>
                            );
                          })}
                        </tbody>
                        <tfoot>
                          <tr className="border-t border-white/[0.08] bg-white/[0.02]">
                            <td className="px-4 py-3" colSpan={4}>
                              <span className="text-sm font-semibold text-white">Closing Balance</span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className="text-sm font-mono font-semibold text-emerald-400">{formatCurrency(totalDebits)}</span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className="text-sm font-mono font-semibold text-red-400">{formatCurrency(totalCredits)}</span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className={`text-sm font-mono font-bold ${parseAmount(data.closing_balance) < 0 ? 'text-red-400' : 'text-white'}`}>
                                {parseAmount(data.closing_balance) < 0 ? '−' : ''}{formatCurrency(Math.abs(parseAmount(data.closing_balance)))}
                              </span>
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>

                  {/* Mobile cards */}
                  <div className="lg:hidden space-y-2">
                    {/* Opening balance card */}
                    <div className="glass-panel p-3 flex items-center justify-between">
                      <span className="text-xs font-medium text-gray-500 italic">Opening Balance</span>
                      <span className="text-sm font-mono font-semibold text-gray-300">{formatCurrency(parseAmount(data.opening_balance))}</span>
                    </div>

                    {filteredLines.map((line, i) => {
                      const bal = parseAmount(line.running_balance);
                      return (
                        <motion.div
                          key={`${line.journal_entry_id}-${line.line_no}`}
                          initial={{ opacity: 0, y: 6 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.04 }}
                          className="glass-panel p-4"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <span className="text-xs font-mono font-semibold text-brand-400">{line.entry_no}</span>
                              <p className="text-sm text-gray-200 mt-0.5">{line.description || 'No description'}</p>
                            </div>
                            <span className="text-xs text-gray-500 whitespace-nowrap">{new Date(line.entry_date).toLocaleDateString()}</span>
                          </div>
                          <div className="grid grid-cols-3 gap-2 mt-3 pt-2 border-t border-white/[0.04]">
                            <div>
                              <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Debit</p>
                              <p className="text-xs font-mono text-emerald-400">{fmtAmt(line.debit)}</p>
                            </div>
                            <div>
                              <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Credit</p>
                              <p className="text-xs font-mono text-red-400">{fmtAmt(line.credit)}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Balance</p>
                              <p className={`text-xs font-mono font-semibold ${bal < 0 ? 'text-red-400' : 'text-white'}`}>
                                {bal < 0 ? '−' : ''}{formatCurrency(Math.abs(bal))}
                              </p>
                            </div>
                          </div>
                        </motion.div>
                      );
                    })}

                    {/* Closing balance card */}
                    <div className="glass-panel p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-white">Closing Balance</span>
                        <span className={`text-sm font-mono font-bold ${parseAmount(data.closing_balance) < 0 ? 'text-red-400' : 'text-white'}`}>
                          {parseAmount(data.closing_balance) < 0 ? '−' : ''}{formatCurrency(Math.abs(parseAmount(data.closing_balance)))}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-[10px] text-gray-500">
                        <span>Dr: <span className="font-mono text-emerald-400">{formatCurrency(totalDebits)}</span></span>
                        <span>Cr: <span className="font-mono text-red-400">{formatCurrency(totalCredits)}</span></span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </>
          )}
        </>
      )}
    </>
  );
}
