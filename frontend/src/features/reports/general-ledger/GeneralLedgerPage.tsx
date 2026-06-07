import { useState, useEffect, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PageLayout from '../../../components/layout/PageLayout';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import AccountTypeBadge from '../../accounts/AccountTypeBadge';
import { useGeneralLedger } from './useGeneralLedger';
import { formatCurrency } from '../../../lib/format';
import type { AccountLedgerRead } from '../../../api/types';
import type { AccountLedgerLine } from '../../../api/types';
import {
  Library,
  Search,
  Calendar,
  X,
  ChevronDown,
  ChevronRight,
  Hash,
  ArrowDownRight,
  ArrowUpRight,
  Filter,
  Check,
} from 'lucide-react';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(Math.abs(n));
}

const ACCOUNT_TYPES = ['all', 'asset', 'liability', 'equity', 'income', 'expense'] as const;

export default function GeneralLedgerPage() {
  return (
    <PageLayout
      pageTitle="General Ledger"
      pageSubtitle="Review all account ledgers and running balances across the selected company"
      activePath="/reports/general-ledger"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <GeneralLedgerContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface GeneralLedgerContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function GeneralLedgerContent({ selectedCompanyId, companiesLoading }: GeneralLedgerContentProps) {
  const [startDate, setStartDate] = useState<string | null>(null);
  const [endDate, setEndDate] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [expandedAccounts, setExpandedAccounts] = useState<Set<number>>(new Set());
  const [typeDropdownOpen, setTypeDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const {
    data,
    isLoading: reportLoading,
    error,
    fetchReport,
  } = useGeneralLedger({ companyId: selectedCompanyId, startDate, endDate });

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    setSearchQuery('');
    setTypeFilter('all');
    setExpandedAccounts(new Set());
    setTypeDropdownOpen(false);
  }, [selectedCompanyId]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setTypeDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // ── Toggle expand ──
  const toggleAccount = (accountId: number) => {
    setExpandedAccounts((prev) => {
      const next = new Set(prev);
      if (next.has(accountId)) next.delete(accountId);
      else next.add(accountId);
      return next;
    });
  };

  // ── Filtering ──
  const filteredAccounts = useMemo(() => {
    if (!data) return [];
    let accounts = data.accounts;

    // Type filter
    if (typeFilter !== 'all') {
      accounts = accounts.filter((a) => a.account_type === typeFilter);
    }

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      accounts = accounts.filter((a) => {
        const accountMatch =
          a.account_code.toLowerCase().includes(q) ||
          a.account_name.toLowerCase().includes(q) ||
          a.account_type.toLowerCase().includes(q);
        const lineMatch = a.lines.some(
          (l) =>
            l.entry_no.toLowerCase().includes(q) ||
            (l.description && l.description.toLowerCase().includes(q)),
        );
        return accountMatch || lineMatch;
      });
    }

    return accounts;
  }, [data, typeFilter, searchQuery]);

  // ── Aggregates ──
  const totalAccounts = data?.accounts.length ?? 0;
  const accountsWithActivity = data?.accounts.filter((a) => a.lines.length > 0).length ?? 0;
  const totalLines = data?.accounts.reduce((s, a) => s + a.lines.length, 0) ?? 0;
  const aggregateOpening = data?.accounts.reduce((s, a) => s + parseAmount(a.opening_balance), 0) ?? 0;
  const aggregateClosing = data?.accounts.reduce((s, a) => s + parseAmount(a.closing_balance), 0) ?? 0;

  const isLoading = companiesLoading || reportLoading;

  const clearDates = () => {
    setStartDate(null);
    setEndDate(null);
  };

  const expandAll = () => {
    setExpandedAccounts(new Set(filteredAccounts.map((a) => a.account_id)));
  };

  const collapseAll = () => {
    setExpandedAccounts(new Set());
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
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-700 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                    <Library className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-white">General Ledger</h1>
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
                </div>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Hash className="w-3 h-3 text-cyan-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Accounts</p>
                  </div>
                  <p className="text-xl font-bold text-white tracking-tight font-mono">{totalAccounts}</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">{accountsWithActivity} with activity</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowDownRight className="w-3 h-3 text-gray-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Σ Opening</p>
                  </div>
                  <p className="text-xl font-bold text-white tracking-tight font-mono">
                    {formatCurrency(Math.abs(aggregateOpening))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <ArrowUpRight className="w-3 h-3 text-gray-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Σ Closing</p>
                  </div>
                  <p className={`text-xl font-bold tracking-tight font-mono ${aggregateClosing < 0 ? 'text-red-400' : 'text-white'}`}>
                    {aggregateClosing < 0 ? '−' : ''}{formatCurrency(Math.abs(aggregateClosing))}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Hash className="w-3 h-3 text-gray-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Total Lines</p>
                  </div>
                  <p className="text-xl font-bold text-white tracking-tight font-mono">{totalLines}</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Filter className="w-3 h-3 text-gray-400" />
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">Showing</p>
                  </div>
                  <p className="text-xl font-bold text-white tracking-tight font-mono">{filteredAccounts.length}</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">of {totalAccounts} accounts</p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Toolbar: dates + type filter + search */}
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

            {/* Account type filter */}
            <div className="relative min-w-[160px] w-full sm:w-auto" ref={dropdownRef}>
              <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1.5">Type</label>
              <button
                type="button"
                onClick={() => setTypeDropdownOpen(!typeDropdownOpen)}
                className="input-field text-sm w-full flex items-center justify-between gap-2 px-4 text-left cursor-pointer select-none bg-white/[0.04] border border-white/[0.08] rounded-xl text-gray-100 hover:border-white/[0.12] transition-all"
              >
                <span>
                  {typeFilter === 'all' ? 'All Types' : typeFilter.charAt(0).toUpperCase() + typeFilter.slice(1)}
                </span>
                <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${typeDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {typeDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.15 }}
                    className="absolute z-50 mt-1 w-full rounded-xl bg-surface-800 border border-white/[0.08] shadow-2xl shadow-black/40 overflow-hidden py-1"
                  >
                    {ACCOUNT_TYPES.map((t) => {
                      const isSelected = typeFilter === t;
                      const label = t === 'all' ? 'All Types' : t.charAt(0).toUpperCase() + t.slice(1);
                      return (
                        <button
                          key={t}
                          type="button"
                          onClick={() => {
                            setTypeFilter(t);
                            setTypeDropdownOpen(false);
                          }}
                          className={`w-full flex items-center justify-between px-3 py-2 text-left text-sm transition-colors hover:bg-white/[0.04] ${
                            isSelected ? 'text-brand-400 bg-brand-500/5 font-medium' : 'text-gray-300'
                          }`}
                        >
                          <span>{label}</span>
                          {isSelected && <Check className="w-3.5 h-3.5 text-brand-400" />}
                        </button>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Search */}
            <div className="relative flex-1 min-w-[260px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search accounts, entry no, or description..."
                className="input-field pl-10 text-sm"
              />
            </div>

            {/* Expand/Collapse controls */}
            <div className="flex items-center rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden h-[46px] p-0.5">
              <button
                type="button"
                onClick={expandAll}
                className="px-5 h-full text-sm font-medium text-gray-300 hover:text-white hover:bg-white/[0.04] rounded-lg transition-all flex items-center justify-center whitespace-nowrap"
              >
                Expand all
              </button>
              <div className="w-[1px] h-5 bg-white/[0.08]" />
              <button
                type="button"
                onClick={collapseAll}
                className="px-5 h-full text-sm font-medium text-gray-300 hover:text-white hover:bg-white/[0.04] rounded-lg transition-all flex items-center justify-center whitespace-nowrap"
              >
                Collapse all
              </button>
            </div>
          </motion.div>

          {/* Empty state */}
          {totalAccounts === 0 && (
            <EmptyState
              icon={<Library className="w-7 h-7 text-brand-400" />}
              title="No General Ledger Data"
              description="There are no accounts to display. Create accounts and journal entries to see the general ledger."
            />
          )}

          {/* Search/filter empty state */}
          {totalAccounts > 0 && filteredAccounts.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-16">
              <Search className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No accounts match your filters.</p>
              <button
                onClick={() => { setSearchQuery(''); setTypeFilter('all'); }}
                className="mt-3 text-brand-400 text-xs font-medium hover:text-brand-300 transition-colors"
              >
                Clear filters
              </button>
            </motion.div>
          )}

          {/* Account cards */}
          {filteredAccounts.length > 0 && (
            <div className="space-y-3">
              {filteredAccounts.map((account, i) => (
                <AccountCard
                  key={account.account_id}
                  account={account}
                  isExpanded={expandedAccounts.has(account.account_id)}
                  onToggle={() => toggleAccount(account.account_id)}
                  index={i}
                />
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}

// ── Account Card ──
interface AccountCardProps {
  account: AccountLedgerRead;
  isExpanded: boolean;
  onToggle: () => void;
  index: number;
}

function AccountCard({ account, isExpanded, onToggle, index }: AccountCardProps) {
  const closing = parseAmount(account.closing_balance);
  const hasActivity = account.lines.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.03, 0.5) }}
      className={`glass-panel overflow-hidden ${!hasActivity ? 'opacity-60' : ''}`}
    >
      {/* Account header — clickable */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-4 p-4 lg:px-6 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex-shrink-0">
          {isExpanded
            ? <ChevronDown className="w-4 h-4 text-gray-500" />
            : <ChevronRight className="w-4 h-4 text-gray-500" />
          }
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono font-semibold text-brand-400">{account.account_code}</span>
            <span className="text-sm font-medium text-white truncate">{account.account_name}</span>
            <AccountTypeBadge type={account.account_type} />
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-6 flex-shrink-0">
          <div className="text-right">
            <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Opening</p>
            <p className="text-xs font-mono text-gray-300">{formatCurrency(parseAmount(account.opening_balance))}</p>
          </div>
          <div className="text-right">
            <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Closing</p>
            <p className={`text-xs font-mono font-semibold ${closing < 0 ? 'text-red-400' : 'text-white'}`}>
              {closing < 0 ? '−' : ''}{formatCurrency(Math.abs(closing))}
            </p>
          </div>
          <div className="text-right min-w-[40px]">
            <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium">Lines</p>
            <p className="text-xs font-mono text-gray-400">{account.lines.length}</p>
          </div>
        </div>
        {/* Mobile metrics */}
        <div className="sm:hidden flex items-center gap-3 flex-shrink-0">
          <div className="text-right">
            <p className={`text-xs font-mono font-semibold ${closing < 0 ? 'text-red-400' : 'text-white'}`}>
              {closing < 0 ? '−' : ''}{formatCurrency(Math.abs(closing))}
            </p>
            <p className="text-[9px] text-gray-500">{account.lines.length} lines</p>
          </div>
        </div>
      </button>

      {/* Expanded ledger lines */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/[0.06]">
              {account.lines.length === 0 ? (
                <div className="px-6 py-8 text-center">
                  <p className="text-sm text-gray-500">No activity for this account.</p>
                </div>
              ) : (
                <>
                  {/* Desktop table */}
                  <div className="hidden md:block overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-white/[0.04]">
                          <th className="text-left text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-6 py-2">Date</th>
                          <th className="text-left text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-4 py-2">Entry No</th>
                          <th className="text-center text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-2 py-2">Ln</th>
                          <th className="text-left text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-4 py-2">Description</th>
                          <th className="text-right text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-4 py-2">Debit</th>
                          <th className="text-right text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-4 py-2">Credit</th>
                          <th className="text-right text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-6 py-2">Balance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* Opening balance */}
                        <tr className="border-b border-white/[0.03] bg-white/[0.01]">
                          <td className="px-6 py-2" colSpan={4}>
                            <span className="text-[11px] text-gray-500 italic">Opening Balance</span>
                          </td>
                          <td colSpan={2} />
                          <td className="px-6 py-2 text-right">
                            <span className="text-xs font-mono text-gray-400">{formatCurrency(parseAmount(account.opening_balance))}</span>
                          </td>
                        </tr>
                        {account.lines.map((line) => (
                          <LedgerRow key={`${line.journal_entry_id}-${line.line_no}`} line={line} />
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="border-t border-white/[0.06] bg-white/[0.02]">
                          <td className="px-6 py-2" colSpan={4}>
                            <span className="text-[11px] font-semibold text-white">Closing Balance</span>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className="text-xs font-mono font-semibold text-emerald-400">
                              {formatCurrency(account.lines.reduce((s, l) => s + parseAmount(l.debit), 0))}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className="text-xs font-mono font-semibold text-red-400">
                              {formatCurrency(account.lines.reduce((s, l) => s + parseAmount(l.credit), 0))}
                            </span>
                          </td>
                          <td className="px-6 py-2 text-right">
                            <span className={`text-xs font-mono font-bold ${closing < 0 ? 'text-red-400' : 'text-white'}`}>
                              {closing < 0 ? '−' : ''}{formatCurrency(Math.abs(closing))}
                            </span>
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  {/* Mobile cards */}
                  <div className="md:hidden p-3 space-y-2">
                    <div className="flex items-center justify-between px-2 py-1">
                      <span className="text-[10px] text-gray-500 italic">Opening: <span className="font-mono text-gray-400">{formatCurrency(parseAmount(account.opening_balance))}</span></span>
                    </div>
                    {account.lines.map((line) => (
                      <MobileLedgerCard key={`${line.journal_entry_id}-${line.line_no}`} line={line} />
                    ))}
                    <div className="flex items-center justify-between px-2 py-1 border-t border-white/[0.06]">
                      <span className="text-[10px] font-semibold text-white">Closing</span>
                      <span className={`text-xs font-mono font-bold ${closing < 0 ? 'text-red-400' : 'text-white'}`}>
                        {closing < 0 ? '−' : ''}{formatCurrency(Math.abs(closing))}
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Desktop ledger row ──
function LedgerRow({ line }: { line: AccountLedgerLine }) {
  const bal = parseAmount(line.running_balance);
  return (
    <tr className="border-b border-white/[0.02] hover:bg-white/[0.015] transition-colors">
      <td className="px-6 py-2">
        <span className="text-xs text-gray-400">{new Date(line.entry_date).toLocaleDateString()}</span>
      </td>
      <td className="px-4 py-2">
        <span className="text-xs font-mono text-brand-400">{line.entry_no}</span>
      </td>
      <td className="px-2 py-2 text-center">
        <span className="text-[10px] text-gray-600">{line.line_no}</span>
      </td>
      <td className="px-4 py-2">
        <span className="text-xs text-gray-300 truncate block max-w-[220px]">{line.description || '—'}</span>
      </td>
      <td className="px-4 py-2 text-right">
        <span className="text-xs font-mono text-emerald-400">{fmtAmt(line.debit)}</span>
      </td>
      <td className="px-4 py-2 text-right">
        <span className="text-xs font-mono text-red-400">{fmtAmt(line.credit)}</span>
      </td>
      <td className="px-6 py-2 text-right">
        <span className={`text-xs font-mono font-semibold ${bal < 0 ? 'text-red-400' : 'text-gray-200'}`}>
          {bal < 0 ? '−' : ''}{formatCurrency(Math.abs(bal))}
        </span>
      </td>
    </tr>
  );
}

// ── Mobile ledger card ──
function MobileLedgerCard({ line }: { line: AccountLedgerLine }) {
  const bal = parseAmount(line.running_balance);
  return (
    <div className="rounded-lg bg-white/[0.02] border border-white/[0.04] p-3">
      <div className="flex items-start justify-between mb-1.5">
        <div>
          <span className="text-[10px] font-mono text-brand-400">{line.entry_no}</span>
          <p className="text-xs text-gray-300 mt-0.5">{line.description || 'No description'}</p>
        </div>
        <span className="text-[10px] text-gray-500 whitespace-nowrap">{new Date(line.entry_date).toLocaleDateString()}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 pt-1.5 border-t border-white/[0.03]">
        <div>
          <p className="text-[8px] uppercase tracking-wider text-gray-600 font-medium">Dr</p>
          <p className="text-[10px] font-mono text-emerald-400">{fmtAmt(line.debit)}</p>
        </div>
        <div>
          <p className="text-[8px] uppercase tracking-wider text-gray-600 font-medium">Cr</p>
          <p className="text-[10px] font-mono text-red-400">{fmtAmt(line.credit)}</p>
        </div>
        <div className="text-right">
          <p className="text-[8px] uppercase tracking-wider text-gray-600 font-medium">Bal</p>
          <p className={`text-[10px] font-mono font-semibold ${bal < 0 ? 'text-red-400' : 'text-gray-200'}`}>
            {bal < 0 ? '−' : ''}{formatCurrency(Math.abs(bal))}
          </p>
        </div>
      </div>
    </div>
  );
}
