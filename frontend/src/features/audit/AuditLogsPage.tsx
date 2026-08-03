import { useState, useEffect, useId, useMemo, Fragment } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Lock, RefreshCw, ChevronDown, ChevronUp, X, ScrollText } from 'lucide-react';
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

export default function AuditLogsPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.auditLogs.pageTitle}
      pageSubtitle={t.auditLogs.pageSubtitle}
      activePath="/audit-logs"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <AuditLogsContent selectedCompanyId={selectedCompanyId} companiesLoading={companiesLoading} />
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
  const searchId = useId();
  const actionFilterId = useId();
  const entityFilterId = useId();
  const detailsIdPrefix = useId();

  const [skip, setSkip] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const { logs, total, isLoading, error, statusCode, fetchLogs, pageSize } = useAuditLogs({
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

  /** Timestamps carry seconds because audit order matters more than brevity. */
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

  // Client-side search over the page the API returned.
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
        log.entity_type.toLowerCase().includes(q),
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

  const humanizeEntityType = (type: string) =>
    type
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

  const humanizeAction = (action: string) => {
    const auditT = t.auditLogs as unknown as Record<string, string>;
    const camelKey = action.toLowerCase().replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
    if (auditT[camelKey]) return auditT[camelKey];
    return action
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  const actorName = (log: AuditLog) => log.actor_name || log.actor_email || log.actor;

  const renderExpandButton = (log: AuditLog, isExpanded: boolean) => (
    <button
      type="button"
      onClick={() => toggleExpand(log.id)}
      aria-expanded={isExpanded}
      aria-controls={`${detailsIdPrefix}-${log.id}`}
      aria-label={isExpanded ? t.auditLogs.hideDetails : t.auditLogs.showDetails}
      className="btn-icon h-8 w-8"
    >
      {isExpanded ? (
        <ChevronUp aria-hidden className="h-4 w-4" />
      ) : (
        <ChevronDown aria-hidden className="h-4 w-4" />
      )}
    </button>
  );

  if (companiesLoading) return <LoadingState />;

  if (!selectedCompanyId) {
    return <EmptyState title={t.common.noCompanySelected} description={t.common.selectCompanyPrompt} />;
  }

  if (statusCode === 403) {
    return (
      <EmptyState
        icon={<Lock className="h-6 w-6 text-danger" />}
        title={t.settingsPage.accessDenied}
        description={t.auditLogs.accessDeniedDescription}
        action={<p className="text-xs text-subtle-foreground">{t.auditLogs.accessDeniedHint}</p>}
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="filter-bar">
        <div className="min-w-[220px] flex-1">
          <label htmlFor={searchId} className="field-label">
            {t.common.search}
          </label>
          <div className="relative">
            <Search
              aria-hidden
              className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle-foreground"
            />
            <input
              id={searchId}
              type="search"
              placeholder={t.auditLogs.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input ps-9"
            />
          </div>
        </div>

        <div className="w-full sm:w-52">
          <label htmlFor={actionFilterId} className="field-label">
            {t.auditLogs.action}
          </label>
          <select id={actionFilterId} value={actionFilter} onChange={handleActionChange} className="select">
            <option value="">{t.auditLogs.filterByAction}</option>
            {COMMON_ACTIONS.map((a) => (
              <option key={a} value={a}>
                {humanizeAction(a)}
              </option>
            ))}
          </select>
        </div>

        <div className="w-full sm:w-48">
          <label htmlFor={entityFilterId} className="field-label">
            {t.auditLogs.entityType}
          </label>
          <select
            id={entityFilterId}
            value={entityTypeFilter}
            onChange={handleEntityTypeChange}
            className="select"
          >
            <option value="">{t.auditLogs.filterByEntity}</option>
            {ENTITY_TYPES.map((type) => (
              <option key={type} value={type}>
                {humanizeEntityType(type)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button type="button" onClick={handleClearFilters} className="btn btn-ghost btn-sm">
              <X aria-hidden className="h-3.5 w-3.5" />
              {t.auditLogs.clearFilters}
            </button>
          )}
          <button type="button" onClick={fetchLogs} className="btn btn-secondary btn-sm">
            <RefreshCw aria-hidden className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            {t.common.refresh}
          </button>
        </div>
      </div>

      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchLogs} />
      ) : filteredLogs.length === 0 ? (
        <EmptyState
          icon={<ScrollText className="h-6 w-6" />}
          title={t.auditLogs.noLogsTitle}
          description={hasActiveFilters ? t.common.noResults : t.auditLogs.noLogsDescription}
          action={
            hasActiveFilters ? (
              <button type="button" onClick={handleClearFilters} className="btn btn-secondary btn-sm">
                {t.auditLogs.clearFilters}
              </button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop table */}
          <div className="card hidden overflow-hidden lg:block">
            <div className="table-wrap">
              <table className="data-table">
                <caption className="sr-only">{t.auditLogs.pageTitle}</caption>
                <thead>
                  <tr>
                    <th scope="col" className="w-52">
                      {t.auditLogs.timestamp}
                    </th>
                    <th scope="col">{t.auditLogs.actor}</th>
                    <th scope="col">{t.auditLogs.action}</th>
                    <th scope="col">{t.auditLogs.entity}</th>
                    <th scope="col" className="w-12">
                      <span className="sr-only">{t.auditLogs.auditDetails}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.map((log) => {
                    const isExpanded = expandedRows.has(log.id);
                    const showDetails = hasDetails(log);
                    return (
                      <Fragment key={log.id}>
                        <tr className={isExpanded ? 'bg-surface-muted' : undefined}>
                          <td className="numeric whitespace-nowrap align-top text-xs text-muted-foreground">
                            {formatDateTime(log.created_at)}
                          </td>

                          <td className="align-top">
                            <span className="block truncate text-sm font-medium text-foreground">
                              {actorName(log)}
                            </span>
                            {log.actor_name && log.actor_email && (
                              <span className="block truncate text-xs text-subtle-foreground">
                                {log.actor_email}
                              </span>
                            )}
                          </td>

                          <td className="align-top">
                            <AuditActionBadge action={log.action} />
                            {log.description && (
                              <p className="mt-1.5 max-w-xs truncate text-xs text-subtle-foreground">
                                {log.description}
                              </p>
                            )}
                          </td>

                          <td className="align-top">
                            <span className="text-xs text-muted-foreground">
                              {humanizeEntityType(log.entity_type)}
                            </span>
                            {log.entity_id && (
                              <span className="numeric ms-2 text-xs font-semibold text-primary">
                                #{log.entity_id}
                              </span>
                            )}
                          </td>

                          <td className="align-top text-end">
                            {showDetails && renderExpandButton(log, isExpanded)}
                          </td>
                        </tr>

                        {showDetails && isExpanded && (
                          <tr id={`${detailsIdPrefix}-${log.id}`} className="bg-surface-sunken">
                            <td colSpan={5} className="pb-4 pt-0">
                              <p className="overline mb-2">{t.auditLogs.auditDetails}</p>
                              <AuditDetailsPanel oldValues={log.old_values} newValues={log.new_values} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile cards */}
          <div className="space-y-3 lg:hidden">
            {filteredLogs.map((log) => {
              const isExpanded = expandedRows.has(log.id);
              const showDetails = hasDetails(log);
              return (
                <div key={log.id} className="card space-y-3 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1.5">
                      <p className="numeric text-xs text-subtle-foreground">{formatDateTime(log.created_at)}</p>
                      <AuditActionBadge action={log.action} />
                    </div>
                    {showDetails && renderExpandButton(log, isExpanded)}
                  </div>

                  <dl className="grid grid-cols-2 gap-x-3 gap-y-3 border-t border-border-subtle pt-3 text-sm">
                    <div className="min-w-0">
                      <dt className="overline">{t.auditLogs.actor}</dt>
                      <dd className="mt-0.5 truncate font-medium text-foreground">{actorName(log)}</dd>
                      {log.actor_name && log.actor_email && (
                        <dd className="truncate text-xs text-subtle-foreground">{log.actor_email}</dd>
                      )}
                    </div>

                    <div className="min-w-0">
                      <dt className="overline">{t.auditLogs.entity}</dt>
                      <dd className="mt-0.5 truncate text-xs text-muted-foreground">
                        {humanizeEntityType(log.entity_type)}
                        {log.entity_id && (
                          <span className="numeric ms-1.5 font-semibold text-primary">#{log.entity_id}</span>
                        )}
                      </dd>
                    </div>
                  </dl>

                  {log.description && (
                    <div className="panel p-3">
                      <p className="overline">{t.common.description}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{log.description}</p>
                    </div>
                  )}

                  {showDetails && (
                    <AnimatePresence initial={false}>
                      {isExpanded && (
                        <motion.div
                          id={`${detailsIdPrefix}-${log.id}`}
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="border-t border-border-subtle pt-3">
                            <p className="overline mb-2">{t.auditLogs.auditDetails}</p>
                            <AuditDetailsPanel oldValues={log.old_values} newValues={log.new_values} />
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  )}
                </div>
              );
            })}
          </div>

          <PaginationControls
            skip={skip}
            limit={pageSize}
            total={total}
            onPrev={() => setSkip((p) => Math.max(0, p - pageSize))}
            onNext={() => setSkip((p) => p + pageSize)}
            entityName={t.auditLogs.logEntries}
          />
        </div>
      )}
    </div>
  );
}
