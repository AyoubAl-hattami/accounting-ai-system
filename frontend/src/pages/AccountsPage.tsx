import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import AppShell from '../components/layout/AppShell';
import AccountTypeBadge from '../components/AccountTypeBadge';
import PaginationControls from '../components/PaginationControls';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import { useCompanies } from '../hooks/useCompanies';
import { useAccounts } from '../hooks/useAccounts';
import {
  Receipt,
  Search,
  Filter,
  Sprout,
  Loader2,
  CheckCircle2,
  Building2,
  X,
} from 'lucide-react';

const ACCOUNT_FETCH_LIMIT = 500;
const ACCOUNT_TYPES = ['asset', 'liability', 'equity', 'income', 'expense'];
const PAGE_SIZE = 10;

export default function AccountsPage() {
  const {
    companies,
    selectedCompanyId,
    selectedCompany,
    selectCompany,
    isLoading: companiesLoading,
  } = useCompanies();

  // ── Pagination ──
  const [skip, setSkip] = useState(0);

  // ── Filters ──
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const {
    accounts,
    total,
    isLoading: accountsLoading,
    error,
    fetchAccounts,
    seedDefaults,
  } = useAccounts({
    companyId: selectedCompanyId,
    skip: 0,
    limit: ACCOUNT_FETCH_LIMIT, // backend enforces max 500
  });

  // ── Seed state ──
  const [isSeeding, setIsSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<{ created: number; skipped: number } | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);

  // Reset pagination and filters on company change
  useEffect(() => {
    setSkip(0);
    setSearchQuery('');
    setTypeFilter('');
    setSeedResult(null);
    setSeedError(null);
  }, [selectedCompanyId]);

  // Fetch on mount and company change
  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  // ── Client-side filtering ──
  const filteredAccounts = useMemo(() => {
    let result = accounts;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (a) =>
          a.code.toLowerCase().includes(q) ||
          a.name.toLowerCase().includes(q) ||
          (a.description && a.description.toLowerCase().includes(q)),
      );
    }

    if (typeFilter) {
      result = result.filter((a) => a.account_type === typeFilter);
    }

    return result;
  }, [accounts, searchQuery, typeFilter]);

  const filteredTotal = filteredAccounts.length;
  const paginatedAccounts = filteredAccounts.slice(skip, skip + PAGE_SIZE);

  // Reset skip when filter changes
  useEffect(() => {
    setSkip(0);
  }, [searchQuery, typeFilter]);

  // ── Seed handler ──
  const handleSeed = async () => {
    setIsSeeding(true);
    setSeedResult(null);
    setSeedError(null);

    try {
      const result = await seedDefaults();
      if (result) {
        setSeedResult({ created: result.created_count, skipped: result.skipped_count });
        await fetchAccounts();
      }
    } catch {
      setSeedError('Failed to seed default accounts. Please try again.');
    } finally {
      setIsSeeding(false);
    }
  };

  const isLoading = companiesLoading || accountsLoading;

  // ── No companies ──
  if (!companiesLoading && companies.length === 0) {
    return (
      <AppShell
        companies={companies}
        selectedCompany={selectedCompany}
        onSelectCompany={selectCompany}
        pageTitle="Chart of Accounts"
        pageSubtitle="Manage your account structure"
      >
        <EmptyState
          icon={<Building2 className="w-7 h-7 text-brand-400" />}
          title="No Companies Yet"
          description="Create a company from the backend or ask an administrator for access."
          className="py-32"
        />
      </AppShell>
    );
  }

  const subtitle = selectedCompany
    ? `${selectedCompany.name} — Account structure & categories`
    : 'Manage your account structure';

  return (
    <AppShell
      companies={companies}
      selectedCompany={selectedCompany}
      onSelectCompany={selectCompany}
      pageTitle="Chart of Accounts"
      pageSubtitle={subtitle}
      activePath="/accounts"
    >
      {/* Loading */}
      {isLoading && <LoadingState />}

      {/* Error */}
      {!isLoading && error && <ErrorState message={error} onRetry={fetchAccounts} />}

      {/* Content */}
      {!isLoading && !error && (
        <>
          {/* Header row */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6"
          >
            <div>
              <h1 className="text-2xl font-bold text-white mb-1">Chart of Accounts</h1>
              <p className="text-sm text-gray-400">
                Define your company's accounting structure with hierarchical categories and codes.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 font-medium">
                {total} account{total !== 1 ? 's' : ''} total
              </span>
              <button
                onClick={handleSeed}
                disabled={isSeeding}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600/20 border border-brand-500/30 text-brand-300 text-xs font-semibold hover:bg-brand-600/30 hover:border-brand-500/40 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSeeding ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sprout className="w-3.5 h-3.5" />
                )}
                Seed Defaults
              </button>
            </div>
          </motion.div>

          {/* Seed result toast */}
          <AnimatePresence>
            {seedResult && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mb-4 flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20"
              >
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <p className="text-sm text-emerald-300">
                    <span className="font-semibold">{seedResult.created}</span> account{seedResult.created !== 1 ? 's' : ''} created,{' '}
                    <span className="font-semibold">{seedResult.skipped}</span> skipped.
                  </p>
                </div>
                <button onClick={() => setSeedResult(null)} className="text-emerald-400 hover:text-emerald-300 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Seed error toast */}
          <AnimatePresence>
            {seedError && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mb-4 flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20"
              >
                <p className="text-sm text-red-300">{seedError}</p>
                <button onClick={() => setSeedError(null)} className="text-red-400 hover:text-red-300 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Search & filter bar */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="flex flex-col sm:flex-row gap-3 mb-6"
          >
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by code, name, or description..."
                className="input-field pl-10 text-sm"
              />
            </div>
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="input-field pl-10 pr-8 text-sm appearance-none cursor-pointer min-w-[160px]"
              >
                <option value="">All Types</option>
                {ACCOUNT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </motion.div>

          {/* Empty state */}
          {accounts.length === 0 && (
            <EmptyState
              icon={<Receipt className="w-7 h-7 text-brand-400" />}
              title="No Accounts"
              description="This company has no accounts yet. Seed the default chart of accounts to get started."
              action={
                <button
                  onClick={handleSeed}
                  disabled={isSeeding}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-brand-500 text-white text-sm font-semibold hover:from-brand-500 hover:to-brand-400 hover:shadow-lg hover:shadow-brand-500/25 transition-all duration-300 disabled:opacity-50"
                >
                  {isSeeding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sprout className="w-4 h-4" />}
                  Seed Default Accounts
                </button>
              }
            />
          )}

          {/* Filtered empty state */}
          {accounts.length > 0 && filteredAccounts.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-16"
            >
              <Search className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No accounts match your search or filter.</p>
              <button
                onClick={() => { setSearchQuery(''); setTypeFilter(''); }}
                className="mt-3 text-brand-400 text-xs font-medium hover:text-brand-300 transition-colors"
              >
                Clear filters
              </button>
            </motion.div>
          )}

          {/* Table — desktop */}
          {paginatedAccounts.length > 0 && (
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
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Name</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Type</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Parent</th>
                        <th className="text-center text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Active</th>
                        <th className="text-center text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">System</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedAccounts.map((acc, i) => (
                        <motion.tr
                          key={acc.id}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: i * 0.03 }}
                          className="border-b border-white/[0.03] last:border-0 hover:bg-white/[0.02] transition-colors"
                        >
                          <td className="px-4 py-3">
                            <span className="text-sm font-mono font-semibold text-brand-400">{acc.code}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm text-gray-200">{acc.name}</span>
                          </td>
                          <td className="px-4 py-3">
                            <AccountTypeBadge type={acc.account_type} />
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs text-gray-500">
                              {acc.parent_id
                                ? accounts.find((a) => a.id === acc.parent_id)?.code || `#${acc.parent_id}`
                                : '—'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-block w-2 h-2 rounded-full ${acc.is_active ? 'bg-emerald-400' : 'bg-gray-600'}`} />
                          </td>
                          <td className="px-4 py-3 text-center">
                            {acc.is_system ? (
                              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">SYS</span>
                            ) : (
                              <span className="text-[10px] text-gray-600">Manual</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs text-gray-500 truncate block max-w-[200px]">
                              {acc.description || '—'}
                            </span>
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="px-4 py-3 border-t border-white/[0.04]">
                  <PaginationControls
                    skip={skip}
                    limit={PAGE_SIZE}
                    total={filteredTotal}
                    onPrev={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
                    onNext={() => setSkip(skip + PAGE_SIZE)}
                  />
                </div>
              </div>

              {/* Mobile card list */}
              <div className="md:hidden space-y-3">
                {paginatedAccounts.map((acc, i) => (
                  <motion.div
                    key={acc.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="glass-panel p-4"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <span className="text-xs font-mono font-semibold text-brand-400">{acc.code}</span>
                        <h4 className="text-sm font-medium text-white mt-0.5">{acc.name}</h4>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${acc.is_active ? 'bg-emerald-400' : 'bg-gray-600'}`} />
                        <AccountTypeBadge type={acc.account_type} />
                      </div>
                    </div>
                    {acc.description && (
                      <p className="text-xs text-gray-500 mb-2">{acc.description}</p>
                    )}
                    <div className="flex items-center gap-3 text-[10px] text-gray-500">
                      {acc.is_system && (
                        <span className="font-semibold uppercase px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">SYS</span>
                      )}
                      {acc.parent_id && (
                        <span>Parent: {accounts.find((a) => a.id === acc.parent_id)?.code || `#${acc.parent_id}`}</span>
                      )}
                    </div>
                  </motion.div>
                ))}

                {/* Mobile pagination */}
                <PaginationControls
                  skip={skip}
                  limit={PAGE_SIZE}
                  total={filteredTotal}
                  onPrev={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
                  onNext={() => setSkip(skip + PAGE_SIZE)}
                />
              </div>
            </motion.div>
          )}
        </>
      )}
    </AppShell>
  );
}
