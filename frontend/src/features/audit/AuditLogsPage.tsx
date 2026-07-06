import { useState, useEffect, useMemo, Fragment } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Lock,
  RefreshCw,
  Calendar,
  User,
  Tag,
  ChevronDown,
  ChevronUp,
  X,
  Filter,
} from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import PaginationControls from '../../components/ui/PaginationControls';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import EmptyState from '../../components/feedback/EmptyState';
import { useAuditLogs } from './useAuditLogs';
import AuditActionBadge from './AuditActionBadge';
import AuditDetailsPanel from './AuditDetailsPanel';
import { useI18n } from '../../i18n';
import type { AuditLog } from '../../api/types';

// ── Static filter lists ───────────────────────────────────────────────────────
const ENTITY_TYPES = [
  'account',
  'journal_entry',
  'company_user',
  'company',
  'fiscal_year',
  'fiscal_period',
  'invitation',
  'user',
];

const COMMON_ACTIONS = [
  'login_success',
  'login_failure',
  'create_journal_entry',
  'review_journal_entry',
  'post_journal_entry',
  'void_journal_entry',
  'reverse_journal_entry',
  'update_company_user',
  'remove_company_access',
  'restore_company_access',
  'deactivate_user_account',
  'reactivate_user_account',
  'create_invitation',
  'cancel_invitation',
  'accept_invitation',
  'update_account',
  'update_fiscal_year',
  'update_fiscal_period',
];

// ── Main page wrapper ─────────────────────────────────────────────────────────
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

// ── Content ───────────────────────────────────────────────────────────────────
interface AuditLogsContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function AuditLogsContent({ selectedCompanyId, companiesLoading }: AuditLogsContentProps) {
  const { t } = useI18n();

  const [skip, setSkip] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  // Track which rows have their details panel expanded
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const { logs, total, isLoading, error, statusCode, fetchLogs, pageSize } =
    useAuditLogs({
      companyId: selectedCompanyId,
      skip,
      entityType: entityTypeFilter || null,
      action: actionFilter || null,
    });

  useEffect(() => {
    if (selectedCompanyId) {
      fetchLogs();
    }
  }, [selectedCompanyId, skip, entityTypeFilter, actionFilter, fetchLogs]);

  // ── Helpers ─────────────────────────────────────────────────────────────────
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

  const handleEntityTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setEntityTypeFilter(e.target.value);
    setSkip(0);
  };

  const handleActionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setActionFilter(e.target.value);
    setSkip(0);
  };

  const handleClearFilters = () => {
    setEntityTypeFilter('');
    setActionFilter('');
    setSearchQuery('');
    setSkip(0);
  };

  const hasActiveFilters = !!(entityTypeFilter || actionFilter || searchQuery);

  // Client-side search
  const filteredLogs = useMemo(() => {
    if (!searchQuery.trim()) return logs;
    const q = searchQuery.toLowerCase();
    return logs.filter(
      (log) =>
        (log.actor_name && log.actor_name.toLowerCase().includes(q)) ||
        (log.actor_email && log.actor_email.toLowerCase().includes(q)) ||
        log.actor.toLowerCase().includes(q) ||
        log.action.toLowerCase().includes(q) ||
        (log.description && log.description.toLowerCase().includes(q)) ||
        log.entity_type.toLowerCase().includes(q)
    );
  }, [logs, searchQuery]);

  const toggleExpand = (id: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const hasDetails = (log: AuditLog) =>
    !!(log.old_values && Object.keys(log.old_values).length > 0) ||
    !!(log.new_values && Object.keys(log.new_values).length > 0);

  // ── Humanize entity type ─────────────────────────────────────────────────
  const humanizeEntityType = (type: string) =>
    type.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

  // ── Humanize action for dropdown ──────────────────────────────────────────
  const humanizeAction = (action: string) => {
    const auditT = t.auditLogs as unknown as Record<string, string>;
    const camelKey = action
      .toLowerCase()
      .replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
    if (auditT[camelKey]) return auditT[camelKey];
    return action.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  // ── Guard states ─────────────────────────────────────────────────────────
  if (companiesLoading) return <LoadingState />;

  if (!selectedCompanyId) {
    return (
      <EmptyState
        title={t.common.noCompanySelected}
        description={t.common.selectCompanyPrompt}
      />
    );
  }

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
            You do not have permission to view this page. Access to audit logs is strictly
            restricted to users with{' '}
            <span className="text-indigo-400 font-semibold">Admin</span> or{' '}
            <span className="text-indigo-400 font-semibold">Auditor</span> roles.
          </p>
          <div className="text-xs text-gray-500 border-t border-white/[0.06] pt-4">
            If you believe this is an error, please contact your administrator.
          </div>
        </div>
      </motion.div>
    );
  }

  // ── Main render ──────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ── Filter / Search Bar ─────────────────────────────────────────── */}
      <div className="glass-panel p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              id="audit-search"
              type="text"
              placeholder={t.auditLogs.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 pl-10 pr-4 text-sm text-white placeholder-gray-500 focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none transition-all duration-200"
            />
          </div>

          {/* Action filter */}
          <div className="relative w-full sm:w-52">
            <Filter className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <select
              id="audit-action-filter"
              value={actionFilter}
              onChange={handleActionChange}
              className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 pl-8 pr-8 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition-all duration-200 appearance-none cursor-pointer"
            >
              <option value="" className="bg-slate-900 text-white">
                {t.auditLogs.filterByAction}
              </option>
              {COMMON_ACTIONS.map((a) => (
                <option key={a} value={a} className="bg-slate-900 text-white">
                  {humanizeAction(a)}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
              <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
              </svg>
            </div>
          </div>

          {/* Entity type filter */}
          <div className="relative w-full sm:w-48">
            <Tag className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <select
              id="audit-entity-filter"
              value={entityTypeFilter}
              onChange={handleEntityTypeChange}
              className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 pl-8 pr-8 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition-all duration-200 appearance-none cursor-pointer"
            >
              <option value="" className="bg-slate-900 text-white">
                {t.auditLogs.filterByEntity}
              </option>
              {ENTITY_TYPES.map((type) => (
                <option key={type} value={type} className="bg-slate-900 text-white">
                  {humanizeEntityType(type)}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
              <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
              </svg>
            </div>
          </div>

          {/* Clear filters */}
          {hasActiveFilters && (
            <button
              id="audit-clear-filters"
              onClick={handleClearFilters}
              className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl border border-white/[0.06] bg-white/[0.02] text-gray-400 text-sm hover:text-white hover:bg-white/[0.06] transition-all duration-200 whitespace-nowrap"
            >
              <X className="w-3.5 h-3.5" />
              {t.auditLogs.clearFilters}
            </button>
          )}

          {/* Refresh */}
          <button
            id="audit-refresh"
            onClick={fetchLogs}
            className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-gray-300 text-sm font-medium hover:bg-white/[0.08] hover:text-white transition-all duration-200 whitespace-nowrap"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            {t.common.refresh}
          </button>
        </div>
      </div>

      {/* ── Main content ────────────────────────────────────────────────── */}
      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchLogs} />
      ) : filteredLogs.length === 0 ? (
        <EmptyState
          title={t.auditLogs.noLogsTitle}
          description={
            hasActiveFilters ? t.common.noResults : t.auditLogs.noLogsDescription
          }
        />
      ) : (
        <div className="space-y-4">
          {/* ── Desktop Table View ──────────────────────────────────────── */}
          <div className="hidden lg:block glass-panel overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-white/[0.01]">
                    <th className="py-4 px-5 text-xs font-semibold uppercase tracking-wider text-gray-400 w-44">
                      {t.auditLogs.timestamp}
                    </th>
                    <th className="py-4 px-5 text-xs font-semibold uppercase tracking-wider text-gray-400">
                      {t.auditLogs.actor}
                    </th>
                    <th className="py-4 px-5 text-xs font-semibold uppercase tracking-wider text-gray-400">
                      {t.auditLogs.action}
                    </th>
                    <th className="py-4 px-5 text-xs font-semibold uppercase tracking-wider text-gray-400">
                      {t.auditLogs.entity}
                    </th>
                    <th className="py-4 px-5 text-xs font-semibold uppercase tracking-wider text-gray-400 w-8">
                      {/* expand toggle */}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence mode="popLayout">
                    {filteredLogs.map((log) => {
                      const isExpanded = expandedRows.has(log.id);
                      const showDetails = hasDetails(log);
                      return (
                        <Fragment key={log.id}>
                          <motion.tr
                            key={`row-${log.id}`}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className={`border-b border-white/[0.03] transition-colors duration-150 ${
                              isExpanded
                                ? 'bg-white/[0.03]'
                                : 'hover:bg-white/[0.02]'
                            }`}
                          >
                            {/* Timestamp */}
                            <td className="py-4 px-5 text-sm text-gray-400 whitespace-nowrap align-top">
                              <span className="flex items-center gap-1.5">
                                <Calendar className="w-3.5 h-3.5 text-gray-600 shrink-0" />
                                {formatDateTime(log.created_at)}
                              </span>
                            </td>

                            {/* Actor */}
                            <td className="py-4 px-5 align-top">
                              <div className="flex items-center gap-2">
                                <div className="w-7 h-7 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
                                  <User className="w-3.5 h-3.5 text-indigo-400" />
                                </div>
                                <div className="flex flex-col min-w-0">
                                  <span className="text-sm font-semibold text-white truncate">
                                    {log.actor_name || log.actor_email || log.actor}
                                  </span>
                                  {log.actor_name && log.actor_email && (
                                    <span className="text-xs text-gray-500 truncate">
                                      {log.actor_email}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </td>

                            {/* Action */}
                            <td className="py-4 px-5 whitespace-nowrap align-top">
                              <AuditActionBadge action={log.action} />
                              {log.description && (
                                <div
                                  className="mt-1.5 text-xs text-gray-500 max-w-xs truncate"
                                  title={log.description}
                                >
                                  {log.description}
                                </div>
                              )}
                            </td>

                            {/* Entity */}
                            <td className="py-4 px-5 align-top">
                              <span className="text-gray-500 text-xs font-mono uppercase bg-white/[0.03] border border-white/[0.04] px-2 py-0.5 rounded">
                                {humanizeEntityType(log.entity_type)}
                              </span>
                              {log.entity_id && (
                                <span className="ml-2 text-indigo-400 font-semibold font-mono text-sm">
                                  #{log.entity_id}
                                </span>
                              )}
                            </td>

                            {/* Expand toggle */}
                            <td className="py-4 px-5 align-top text-right">
                              {showDetails && (
                                <button
                                  id={`audit-expand-${log.id}`}
                                  onClick={() => toggleExpand(log.id)}
                                  className="p-1.5 rounded-lg hover:bg-white/[0.06] text-gray-500 hover:text-indigo-400 transition-all duration-150"
                                  title={isExpanded ? 'Hide details' : 'Show details'}
                                >
                                  {isExpanded ? (
                                    <ChevronUp className="w-4 h-4" />
                                  ) : (
                                    <ChevronDown className="w-4 h-4" />
                                  )}
                                </button>
                              )}
                            </td>
                          </motion.tr>

                          {/* Details expansion row */}
                          {showDetails && isExpanded && (
                            <motion.tr
                              key={`details-${log.id}`}
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              exit={{ opacity: 0 }}
                              className="bg-black/[0.12] border-b border-white/[0.03]"
                            >
                              <td colSpan={5} className="px-5 pb-4 pt-2">
                                <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-2 flex items-center gap-1.5">
                                  <span className="w-3 h-px bg-gray-600 inline-block" />
                                  {t.auditLogs.auditDetails}
                                </div>
                                <AuditDetailsPanel
                                  oldValues={log.old_values}
                                  newValues={log.new_values}
                                />
                              </td>
                            </motion.tr>
                          )}
                        </Fragment>
                      );
                    })}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Mobile Card View ────────────────────────────────────────── */}
          <div className="lg:hidden space-y-3">
            <AnimatePresence mode="popLayout">
              {filteredLogs.map((log) => {
                const isExpanded = expandedRows.has(log.id);
                const showDetails = hasDetails(log);
                return (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="glass-panel p-4 space-y-3"
                  >
                    {/* Header row */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex flex-col gap-1 min-w-0">
                        <span className="text-xs text-gray-500 flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 shrink-0" />
                          {formatDateTime(log.created_at)}
                        </span>
                        <AuditActionBadge action={log.action} />
                      </div>
                      {showDetails && (
                        <button
                          id={`audit-mobile-expand-${log.id}`}
                          onClick={() => toggleExpand(log.id)}
                          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-gray-500 hover:text-indigo-400 transition-all duration-150 shrink-0"
                        >
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </button>
                      )}
                    </div>

                    {/* Actor + Entity */}
                    <div className="grid grid-cols-2 gap-y-3 gap-x-2 text-sm border-t border-white/[0.05] pt-3">
                      <div>
                        <span className="text-xs text-gray-500 block mb-0.5">{t.auditLogs.actor}</span>
                        <span className="text-white font-medium flex items-center gap-1">
                          <User className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                          <span className="truncate">
                            {log.actor_name || log.actor_email || log.actor}
                          </span>
                        </span>
                        {log.actor_name && log.actor_email && (
                          <span className="text-xs text-gray-500 block mt-0.5 truncate pl-5">
                            {log.actor_email}
                          </span>
                        )}
                      </div>

                      <div>
                        <span className="text-xs text-gray-500 block mb-0.5">{t.auditLogs.entity}</span>
                        <span className="text-gray-300 font-mono text-xs flex items-center gap-1">
                          <Tag className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                          <span className="uppercase">{humanizeEntityType(log.entity_type)}</span>
                          {log.entity_id && (
                            <span className="text-indigo-400 font-semibold">#{log.entity_id}</span>
                          )}
                        </span>
                      </div>
                    </div>

                    {/* Description */}
                    {log.description && (
                      <div className="bg-black/10 border border-white/[0.04] p-3 rounded-lg text-xs text-gray-400">
                        <div className="text-[10px] text-gray-500 font-semibold mb-1 uppercase tracking-wider">
                          {t.common.description}
                        </div>
                        {log.description}
                      </div>
                    )}

                    {/* Expandable details */}
                    {showDetails && (
                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="border-t border-white/[0.05] pt-3">
                              <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-2">
                                {t.auditLogs.auditDetails}
                              </div>
                              <AuditDetailsPanel
                                oldValues={log.old_values}
                                newValues={log.new_values}
                              />
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>

          {/* Pagination */}
          <PaginationControls
            skip={skip}
            limit={pageSize}
            total={total}
            onPrev={() => setSkip((p) => Math.max(0, p - pageSize))}
            onNext={() => setSkip((p) => p + pageSize)}
            entityName="logs"
          />
        </div>
      )}
    </div>
  );
}
