import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Lock, RefreshCw, Calendar, User, Tag } from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import PaginationControls from '../../components/ui/PaginationControls';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import EmptyState from '../../components/feedback/EmptyState';
import { useAuditLogs } from './useAuditLogs';
import AuditActionBadge from './AuditActionBadge';
import { useI18n } from '../../i18n';

export default function AuditLogsPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.auditLogs.pageTitle}
      pageSubtitle={t.auditLogs.pageSubtitle}
      activePath="/audit-logs"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <AuditLogsContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface AuditLogsContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function AuditLogsContent({ selectedCompanyId, companiesLoading }: AuditLogsContentProps) {
  const { t } = useI18n();
  const [skip, setSkip] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('');

  const {
    logs,
    total,
    isLoading,
    error,
    statusCode,
    fetchLogs,
    pageSize,
  } = useAuditLogs({
    companyId: selectedCompanyId,
    skip,
    entityType: entityTypeFilter || null,
  });

  useEffect(() => {
    if (selectedCompanyId) {
      fetchLogs();
    }
  }, [selectedCompanyId, skip, entityTypeFilter, fetchLogs]);

  // Reset pagination when filter changes
  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setEntityTypeFilter(e.target.value);
    setSkip(0);
  };

  // Extract unique entity types for filter dropdown options
  // (While we filter on backend via entityTypeFilter, we can also extract from current list or use standard list)
  const ENTITY_TYPES = ['account', 'journal_entry', 'company_user', 'company', 'fiscal_year'];

  // Clientside search filter
  const filteredLogs = useMemo(() => {
    if (!searchQuery.trim()) return logs;
    const query = searchQuery.toLowerCase();
    return logs.filter(
      (log) =>
        log.actor.toLowerCase().includes(query) ||
        log.action.toLowerCase().includes(query) ||
        (log.description && log.description.toLowerCase().includes(query)) ||
        log.entity_type.toLowerCase().includes(query)
    );
  }, [logs, searchQuery]);

  const formatDateTime = (dateString: string | null | undefined): string => {
    if (!dateString) return '—';
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const handlePrevPage = () => {
    setSkip((prev) => Math.max(0, prev - pageSize));
  };

  const handleNextPage = () => {
    setSkip((prev) => prev + pageSize);
  };

  if (companiesLoading) {
    return <LoadingState />;
  }

  if (!selectedCompanyId) {
    return (
      <EmptyState
        title={t.common.noCompanySelected}
        description={t.common.selectCompanyPrompt}
      />
    );
  }

  // Handle 403 Forbidden State Elegantly
  if (statusCode === 403) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-center py-20 px-4"
      >
        <div className="glass-panel p-8 max-w-md text-center border-red-500/10">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5 shadow-[0_0_15px_rgba(239,68,68,0.07)]">
            <Lock className="w-8 h-8 text-red-400 animate-pulse" />
          </div>
          <h3 className="text-white font-bold text-xl mb-3">{t.settingsPage.accessDenied}</h3>
          <p className="text-gray-400 text-sm leading-relaxed mb-6">
            You do not have permission to view this page. Access to audit logs is strictly restricted to users with <span className="text-indigo-400 font-semibold">Admin</span> or <span className="text-indigo-400 font-semibold">Auditor</span> roles.
          </p>
          <div className="text-xs text-gray-500 border-t border-white/[0.06] pt-4">
            If you believe this is an error, please contact your administrator.
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters and Search Bar */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 flex-col gap-3 sm:flex-row">
          {/* Search bar */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder={t.auditLogs.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 pl-10 pr-4 text-sm text-white placeholder-gray-500 focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none focus:ring-0 transition-all duration-200"
            />
          </div>

          {/* Entity type dropdown */}
          <div className="relative w-full sm:w-56">
            <select
              value={entityTypeFilter}
              onChange={handleFilterChange}
              className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 pl-3 pr-8 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition-all duration-200 appearance-none cursor-pointer"
            >
              <option value="" className="bg-slate-900 text-white">{t.auditLogs.allEntityTypes}</option>
              {ENTITY_TYPES.map((type) => (
                <option key={type} value={type} className="bg-slate-900 text-white">
                  {type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
              <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
              </svg>
            </div>
          </div>
        </div>

        <button
          onClick={fetchLogs}
          className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-gray-300 text-sm font-medium hover:bg-white/[0.08] hover:text-white transition-all duration-200"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Main content body */}
      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchLogs} />
      ) : filteredLogs.length === 0 ? (
        <EmptyState
          title={t.auditLogs.noLogsTitle}
          description={
            searchQuery || entityTypeFilter
              ? t.common.noResults
              : t.auditLogs.noLogsDescription
          }
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop Table View */}
          <div className="hidden lg:block glass-panel overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-white/[0.01]">
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.auditLogs.timestamp}</th>
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.auditLogs.actor}</th>
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.auditLogs.action}</th>
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.auditLogs.entityType}</th>
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.common.description}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  <AnimatePresence mode="popLayout">
                    {filteredLogs.map((log) => (
                      <motion.tr
                        key={log.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="hover:bg-white/[0.02] transition-colors duration-150"
                      >
                        <td className="py-4 px-6 text-sm text-gray-300 whitespace-nowrap">
                          {formatDateTime(log.created_at)}
                        </td>
                        <td className="py-4 px-6 text-sm font-medium text-white whitespace-nowrap">
                          {log.actor}
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <AuditActionBadge action={log.action} />
                        </td>
                        <td className="py-4 px-6 text-sm text-gray-300 whitespace-nowrap">
                          <span className="text-gray-500 text-xs mr-2 font-mono uppercase bg-white/[0.03] px-2 py-1 rounded">
                            {log.entity_type}
                          </span>
                          {log.entity_id && (
                            <span className="text-indigo-400 font-semibold font-mono">
                              #{log.entity_id}
                            </span>
                          )}
                        </td>
                        <td className="py-4 px-6 text-sm text-gray-400 max-w-xs truncate" title={log.description || ''}>
                          {log.description || '—'}
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile Card View */}
          <div className="lg:hidden space-y-3">
            <AnimatePresence mode="popLayout">
              {filteredLogs.map((log) => (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="glass-panel p-5 space-y-3"
                >
                  <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
                    <span className="text-xs text-gray-500 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5" />
                      {formatDateTime(log.created_at)}
                    </span>
                    <AuditActionBadge action={log.action} />
                  </div>

                  <div className="grid grid-cols-2 gap-y-3 gap-x-2 text-sm pt-1">
                    <div>
                      <span className="text-xs text-gray-500 block">{t.auditLogs.actor}</span>
                      <span className="text-white font-medium break-all flex items-center gap-1 mt-0.5">
                        <User className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                        {log.actor}
                      </span>
                    </div>

                    <div>
                      <span className="text-xs text-gray-500 block">{t.auditLogs.entityType}</span>
                      <span className="text-gray-300 font-mono text-xs flex items-center gap-1 mt-0.5">
                        <Tag className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                        <span className="uppercase">{log.entity_type}</span>
                        {log.entity_id && <span className="text-indigo-400">#{log.entity_id}</span>}
                      </span>
                    </div>
                  </div>

                  {log.description && (
                    <div className="bg-black/10 border border-white/[0.04] p-3 rounded-lg text-xs text-gray-400">
                      <div className="text-[10px] text-gray-500 font-semibold mb-1 uppercase tracking-wider">{t.common.description}</div>
                      {log.description}
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {/* Pagination */}
          <PaginationControls
            skip={skip}
            limit={pageSize}
            total={total}
            onPrev={handlePrevPage}
            onNext={handleNextPage}
            entityName="logs"
          />
        </div>
      )}
    </div>
  );
}
