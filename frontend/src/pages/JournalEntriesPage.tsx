import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import AppShell from '../components/AppShell';
import JournalStatusBadge from '../components/JournalStatusBadge';
import JournalEntryLines from '../components/JournalEntryLines';
import PaginationControls from '../components/PaginationControls';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import { useCompanies } from '../hooks/useCompanies';
import { useJournalEntries } from '../hooks/useJournalEntries';
import { formatCurrency as fmtCurrency } from '../lib/format';
import type { JournalEntry, JournalEntryStatus } from '../api/types';
import {
  BookOpen,
  Search,
  Filter,
  ChevronDown,
  CheckCircle2,
  Building2,
} from 'lucide-react';

const STATUSES: JournalEntryStatus[] = ['draft', 'reviewed', 'posted', 'void', 'reversed'];

function calcTotals(entry: JournalEntry) {
  let debit = 0;
  let credit = 0;
  for (const line of entry.lines) {
    debit += parseFloat(line.debit) || 0;
    credit += parseFloat(line.credit) || 0;
  }
  return { debit, credit, balanced: Math.abs(debit - credit) < 0.005 };
}

export default function JournalEntriesPage() {
  const {
    companies,
    selectedCompanyId,
    selectedCompany,
    selectCompany,
    isLoading: companiesLoading,
  } = useCompanies();

  const [skip, setSkip] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const {
    entries,
    total,
    isLoading: entriesLoading,
    error,
    fetchEntries,
    pageSize,
  } = useJournalEntries({ companyId: selectedCompanyId, skip });

  // Reset on company change
  useEffect(() => {
    setSkip(0);
    setSearchQuery('');
    setStatusFilter('');
    setExpandedId(null);
  }, [selectedCompanyId]);

  // Fetch on mount, company, or skip change
  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  // Client-side filtering (within loaded page)
  const filteredEntries = useMemo(() => {
    let result = entries;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (e) =>
          (e.entry_no && e.entry_no.toLowerCase().includes(q)) ||
          (e.description && e.description.toLowerCase().includes(q)) ||
          (e.source_type && e.source_type.toLowerCase().includes(q)),
      );
    }

    if (statusFilter) {
      result = result.filter((e) => e.status === statusFilter);
    }

    return result;
  }, [entries, searchQuery, statusFilter]);

  const isLoading = companiesLoading || entriesLoading;

  // No companies
  if (!companiesLoading && companies.length === 0) {
    return (
      <AppShell
        companies={companies}
        selectedCompany={selectedCompany}
        onSelectCompany={selectCompany}
        pageTitle="Journal Entries"
        pageSubtitle="Accounting entries"
        activePath="/journal-entries"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex items-center justify-center py-32"
        >
          <div className="glass-panel p-10 max-w-md text-center">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto mb-5">
              <Building2 className="w-8 h-8 text-brand-400" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">No Companies Yet</h2>
            <p className="text-gray-400 text-sm leading-relaxed">
              Create a company from the backend or ask an administrator for access.
            </p>
          </div>
        </motion.div>
      </AppShell>
    );
  }

  const subtitle = selectedCompany
    ? `${selectedCompany.name} — Review and monitor accounting entries`
    : 'Review and monitor accounting entries across the selected company';

  return (
    <AppShell
      companies={companies}
      selectedCompany={selectedCompany}
      onSelectCompany={selectCompany}
      pageTitle="Journal Entries"
      pageSubtitle={subtitle}
      activePath="/journal-entries"
    >
      {isLoading && <LoadingState />}

      {!isLoading && error && <ErrorState message={error} onRetry={fetchEntries} />}

      {!isLoading && !error && (
        <>
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6"
          >
            <div>
              <h1 className="text-2xl font-bold text-white mb-1">Journal Entries</h1>
              <p className="text-sm text-gray-400">
                Review and monitor accounting entries across the selected company.
              </p>
            </div>
            <span className="text-xs text-gray-500 font-medium">
              {total} entr{total !== 1 ? 'ies' : 'y'} total
            </span>
          </motion.div>

          {/* Search & filter */}
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
                placeholder="Search by entry no, description, or source..."
                className="input-field pl-10 text-sm"
              />
            </div>
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="input-field pl-10 pr-8 text-sm appearance-none cursor-pointer min-w-[160px]"
              >
                <option value="">All Statuses</option>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </motion.div>

          {/* Empty state */}
          {entries.length === 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center justify-center py-20"
            >
              <div className="glass-panel p-8 max-w-sm text-center">
                <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto mb-4">
                  <BookOpen className="w-7 h-7 text-brand-400" />
                </div>
                <h3 className="text-white font-semibold text-lg mb-2">No Journal Entries</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  This company has no journal entries yet. Create entries from the backend to see them here.
                </p>
              </div>
            </motion.div>
          )}

          {/* Filter-empty state */}
          {entries.length > 0 && filteredEntries.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-16">
              <Search className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No entries match your search or filter.</p>
              <button
                onClick={() => { setSearchQuery(''); setStatusFilter(''); }}
                className="mt-3 text-brand-400 text-xs font-medium hover:text-brand-300 transition-colors"
              >
                Clear filters
              </button>
            </motion.div>
          )}

          {/* Entries list */}
          {filteredEntries.length > 0 && (
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
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3 w-8" />
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Entry No</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Date</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Description</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Status</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Source</th>
                        <th className="text-center text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Lines</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Debit</th>
                        <th className="text-right text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Credit</th>
                        <th className="text-left text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Posted</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredEntries.map((entry, i) => {
                        const totals = calcTotals(entry);
                        const isExpanded = expandedId === entry.id;

                        return (
                          <motion.tbody
                            key={entry.id}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: i * 0.03 }}
                          >
                            <tr
                              className={`border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors cursor-pointer ${isExpanded ? 'bg-white/[0.02]' : ''}`}
                              onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                            >
                              <td className="px-4 py-3">
                                <ChevronDown className={`w-3.5 h-3.5 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} />
                              </td>
                              <td className="px-4 py-3">
                                <span className="text-sm font-mono font-semibold text-brand-400">{entry.entry_no}</span>
                              </td>
                              <td className="px-4 py-3">
                                <span className="text-sm text-gray-300">{new Date(entry.entry_date).toLocaleDateString()}</span>
                              </td>
                              <td className="px-4 py-3">
                                <span className="text-sm text-gray-200 truncate block max-w-[200px]">{entry.description || '—'}</span>
                              </td>
                              <td className="px-4 py-3">
                                <JournalStatusBadge status={entry.status} />
                              </td>
                              <td className="px-4 py-3">
                                <span className="text-xs text-gray-500">{entry.source_type || '—'}</span>
                              </td>
                              <td className="px-4 py-3 text-center">
                                <span className="text-xs text-gray-400">{entry.lines.length}</span>
                              </td>
                              <td className="px-4 py-3 text-right">
                                <span className="text-sm font-mono text-emerald-400">{fmtCurrency(totals.debit)}</span>
                              </td>
                              <td className="px-4 py-3 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <span className="text-sm font-mono text-red-400">{fmtCurrency(totals.credit)}</span>
                                  {totals.balanced && (
                                    <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                                  )}
                                </div>
                              </td>
                              <td className="px-4 py-3">
                                <span className="text-xs text-gray-500">
                                  {entry.posted_at ? new Date(entry.posted_at).toLocaleDateString() : '—'}
                                </span>
                              </td>
                            </tr>
                            {/* Expanded lines */}
                            <AnimatePresence>
                              {isExpanded && (
                                <tr>
                                  <td colSpan={10} className="p-0 border-b border-white/[0.05]">
                                    <JournalEntryLines lines={entry.lines} />
                                  </td>
                                </tr>
                              )}
                            </AnimatePresence>
                          </motion.tbody>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="px-4 py-3 border-t border-white/[0.04]">
                  <PaginationControls
                    skip={skip}
                    limit={pageSize}
                    total={total}
                    onPrev={() => setSkip(Math.max(0, skip - pageSize))}
                    onNext={() => setSkip(skip + pageSize)}
                  />
                </div>
              </div>

              {/* Mobile cards */}
              <div className="lg:hidden space-y-3">
                {filteredEntries.map((entry, i) => {
                  const totals = calcTotals(entry);
                  const isExpanded = expandedId === entry.id;

                  return (
                    <motion.div
                      key={entry.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.04 }}
                      className="glass-panel overflow-hidden"
                    >
                      <div
                        className="p-4 cursor-pointer"
                        onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <span className="text-xs font-mono font-semibold text-brand-400">{entry.entry_no}</span>
                            <p className="text-sm font-medium text-white mt-0.5">{entry.description || 'No description'}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <JournalStatusBadge status={entry.status} />
                            <ChevronDown className={`w-3.5 h-3.5 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} />
                          </div>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-gray-500 mb-2">
                          <span>{new Date(entry.entry_date).toLocaleDateString()}</span>
                          <span>{entry.lines.length} line{entry.lines.length !== 1 ? 's' : ''}</span>
                          {entry.source_type && <span>{entry.source_type}</span>}
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="text-xs font-mono text-emerald-400">Dr {fmtCurrency(totals.debit)}</span>
                            <span className="text-xs font-mono text-red-400">Cr {fmtCurrency(totals.credit)}</span>
                          </div>
                          {totals.balanced && (
                            <div className="flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                              <span className="text-[10px] text-emerald-400 font-medium">Balanced</span>
                            </div>
                          )}
                        </div>
                      </div>

                      <AnimatePresence>
                        {isExpanded && <JournalEntryLines lines={entry.lines} />}
                      </AnimatePresence>
                    </motion.div>
                  );
                })}

                {/* Mobile pagination */}
                <PaginationControls
                  skip={skip}
                  limit={pageSize}
                  total={total}
                  onPrev={() => setSkip(Math.max(0, skip - pageSize))}
                  onNext={() => setSkip(skip + pageSize)}
                />
              </div>
            </motion.div>
          )}
        </>
      )}
    </AppShell>
  );
}
