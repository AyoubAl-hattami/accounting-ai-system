import { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import {
  Building2,
  CalendarClock,
  CalendarPlus,
  PauseCircle,
  Pencil,
  PlayCircle,
  Search,
  XCircle,
} from 'lucide-react';
import EmptyState from '../../components/feedback/EmptyState';
import ErrorState from '../../components/feedback/ErrorState';
import LoadingState from '../../components/feedback/LoadingState';
import PaginationControls from '../../components/ui/PaginationControls';
import { usePageMeta } from '../../components/layout/pageMeta';
import { useToast } from '../../components/feedback/useToast';
import { useI18n } from '../../i18n';
import type { CompanySubscription, SubscriptionStatus } from '../../api/types';
import EditSubscriptionModal from './EditSubscriptionModal';
import SubscriptionConfirmModal, { type ConfirmAction } from './SubscriptionConfirmModal';
import SubscriptionStatusBadge from './SubscriptionStatusBadge';
import { usePlatformSubscriptions } from './usePlatformSubscriptions';

const STATUS_FILTERS: SubscriptionStatus[] = [
  'trial',
  'active',
  'past_due',
  'suspended',
  'cancelled',
];

export default function PlatformSubscriptionsPage() {
  const { t, language } = useI18n();
  const { setMeta } = usePageMeta();
  const toast = useToast();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<SubscriptionStatus | ''>('');
  const [skip, setSkip] = useState(0);
  const [confirming, setConfirming] = useState<{
    action: ConfirmAction;
    entry: CompanySubscription;
  } | null>(null);
  const [editing, setEditing] = useState<CompanySubscription | null>(null);

  const {
    items,
    total,
    isLoading,
    error,
    isSubmitting,
    pageSize,
    fetchSubscriptions,
    activate,
    suspend,
    cancel,
    extend,
    update,
  } = usePlatformSubscriptions({ search, status: statusFilter, skip });

  useLayoutEffect(() => {
    setMeta({
      pageTitle: t.platformSubscriptions.pageTitle,
      pageSubtitle: t.platformSubscriptions.pageSubtitle,
      activePath: '/platform/subscriptions',
    });
  }, [setMeta, t]);

  useEffect(() => {
    void fetchSubscriptions();
  }, [fetchSubscriptions]);

  const formatDate = useCallback(
    (value: string | null) => {
      if (!value) return t.platformSubscriptions.noExpiry;
      const parsed = new Date(value);
      if (Number.isNaN(parsed.getTime())) return t.platformSubscriptions.noExpiry;
      return parsed.toLocaleDateString(language === 'ar' ? 'ar' : 'en-GB', {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
      });
    },
    [language, t],
  );

  const afterAction = useCallback(
    async (result: CompanySubscription | null, successMessage: string) => {
      if (!result) {
        toast.error(t.platformSubscriptions.actionFailed);
        return;
      }
      toast.success(successMessage);
      await fetchSubscriptions();
    },
    [fetchSubscriptions, t, toast],
  );

  const handleConfirm = async (reason: string | null) => {
    if (!confirming) return;
    const { action, entry } = confirming;

    const result =
      action === 'activate'
        ? await activate(entry.company_id)
        : action === 'suspend'
          ? await suspend(entry.company_id, reason)
          : await cancel(entry.company_id, reason);

    const message =
      action === 'activate'
        ? t.platformSubscriptions.activatedToast
        : action === 'suspend'
          ? t.platformSubscriptions.suspendedToast
          : t.platformSubscriptions.cancelledToast;

    setConfirming(null);
    await afterAction(result, message);
  };

  const handleExtend = async (entry: CompanySubscription, period: 'month' | 'year') => {
    const result = await extend(entry.company_id, period);
    await afterAction(result, t.platformSubscriptions.extendedToast);
  };

  const handleEditSubmit = async (payload: {
    status: SubscriptionStatus;
    plan_code: string | null;
    expires_at: string | null;
  }) => {
    if (!editing) return;
    const result = await update(editing.company_id, payload);
    setEditing(null);
    await afterAction(result, t.platformSubscriptions.updatedToast);
  };

  const renderDaysRemaining = (entry: CompanySubscription) => {
    const days = entry.days_remaining;
    if (days === null) return <span className="text-subtle-foreground">—</span>;
    if (days < 0) {
      return <span className="text-danger">{t.platformSubscriptions.expiredAgo}</span>;
    }
    return (
      <span className="numeric">
        {days} {t.platformSubscriptions.daysLeft}
      </span>
    );
  };

  /**
   * Three labelled controls, then the rest as icons behind a divider.
   *
   * Six equally weighted buttons made the action cell wider than the data it
   * belonged to, so the row read as a toolbar with a company name attached.
   * Activate is the one action that is conditional: on an already-active
   * subscription it does nothing a reader would expect, so it is not offered.
   */
  const renderActions = (entry: CompanySubscription) => (
    <div className="flex flex-wrap items-center justify-end gap-1">
      {entry.effective_status !== 'active' && (
        <button
          type="button"
          onClick={() => setConfirming({ action: 'activate', entry })}
          className="btn btn-secondary btn-sm"
        >
          <PlayCircle aria-hidden className="h-3.5 w-3.5" />
          {t.platformSubscriptions.actionActivate}
        </button>
      )}
      <button
        type="button"
        onClick={() => void handleExtend(entry, 'month')}
        disabled={isSubmitting}
        className="btn btn-secondary btn-sm"
      >
        <CalendarPlus aria-hidden className="h-3.5 w-3.5" />
        {t.platformSubscriptions.actionExtendMonth}
      </button>
      <button
        type="button"
        onClick={() => setEditing(entry)}
        className="btn btn-secondary btn-sm"
      >
        <Pencil aria-hidden className="h-3.5 w-3.5" />
        {t.platformSubscriptions.actionEdit}
      </button>

      <span aria-hidden className="mx-0.5 h-5 w-px bg-border" />

      <button
        type="button"
        onClick={() => void handleExtend(entry, 'year')}
        disabled={isSubmitting}
        title={t.platformSubscriptions.actionExtendYear}
        aria-label={t.platformSubscriptions.actionExtendYear}
        className="btn-icon btn-icon-sm"
      >
        <CalendarClock aria-hidden className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => setConfirming({ action: 'suspend', entry })}
        title={t.platformSubscriptions.actionSuspend}
        aria-label={t.platformSubscriptions.actionSuspend}
        className="btn-icon btn-icon-sm hover:text-warning"
      >
        <PauseCircle aria-hidden className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => setConfirming({ action: 'cancel', entry })}
        title={t.platformSubscriptions.actionCancel}
        aria-label={t.platformSubscriptions.actionCancel}
        className="btn-icon btn-icon-sm hover:text-danger"
      >
        <XCircle aria-hidden className="h-4 w-4" />
      </button>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-end gap-3 p-4">
        <div className="relative min-w-[220px] flex-1">
          <Search
            aria-hidden
            className="pointer-events-none absolute top-1/2 h-4 w-4 -translate-y-1/2 text-subtle-foreground start-3"
          />
          <input
            type="search"
            value={search}
            onChange={(e) => {
              setSkip(0);
              setSearch(e.target.value);
            }}
            placeholder={t.platformSubscriptions.searchPlaceholder}
            aria-label={t.platformSubscriptions.searchPlaceholder}
            className="input ps-9"
          />
        </div>
        <div className="min-w-[160px]">
          <label htmlFor="subscription-status-filter" className="field-label">
            {t.platformSubscriptions.statusFilterLabel}
          </label>
          <select
            id="subscription-status-filter"
            value={statusFilter}
            onChange={(e) => {
              setSkip(0);
              setStatusFilter(e.target.value as SubscriptionStatus | '');
            }}
            className="select"
          >
            <option value="">{t.platformSubscriptions.allStatuses}</option>
            {STATUS_FILTERS.map((value) => (
              <option key={value} value={value}>
                {t.subscriptionStatus[value]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && <LoadingState />}

      {!isLoading && error && (
        <ErrorState
          message={t.platformSubscriptions.loadFailed}
          onRetry={() => void fetchSubscriptions()}
        />
      )}

      {!isLoading && !error && items.length === 0 && (
        <EmptyState
          icon={<Building2 className="h-6 w-6" />}
          title={t.platformSubscriptions.emptyTitle}
          description={t.platformSubscriptions.emptyDescription}
        />
      )}

      {!isLoading && !error && items.length > 0 && (
        <>
          {/* Currency and member count ride under the company name, and the
              days remaining under the expiry date, so eight columns become
              five. Nothing is dropped — the pairs are read together anyway,
              and the width they gave back is what lets the row stay one
              line. */}
          <div className="card hidden overflow-hidden lg:block">
            <div className="table-wrap">
              <table className="data-table data-table-compact">
                <caption className="sr-only">{t.platformSubscriptions.pageTitle}</caption>
                <thead>
                  <tr>
                    <th scope="col">{t.platformSubscriptions.columnCompany}</th>
                    <th scope="col">{t.platformSubscriptions.columnEffectiveStatus}</th>
                    <th scope="col">{t.platformSubscriptions.columnExpires}</th>
                    <th scope="col">{t.platformSubscriptions.columnPlan}</th>
                    <th scope="col" className="text-end">
                      {t.platformSubscriptions.columnActions}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((entry) => (
                    <tr key={entry.company_id}>
                      <th scope="row" className="max-w-[18rem] text-start align-middle">
                        <span className="block truncate font-medium text-foreground">
                          {entry.company_name}
                        </span>
                        <span className="block text-xs font-normal text-subtle-foreground">
                          {entry.base_currency} · {entry.member_count}{' '}
                          {t.platformSubscriptions.columnMembers}
                        </span>
                      </th>
                      <td>
                        <SubscriptionStatusBadge status={entry.effective_status} />
                      </td>
                      <td className="whitespace-nowrap">
                        <span className="numeric block">
                          {formatDate(entry.subscription.expires_at)}
                        </span>
                        <span className="block text-xs text-subtle-foreground">
                          {renderDaysRemaining(entry)}
                        </span>
                      </td>
                      <td className="whitespace-nowrap">
                        {entry.subscription.plan_code ?? t.platformSubscriptions.noPlan}
                      </td>
                      <td className="cell-sticky-end">{renderActions(entry)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="space-y-2 lg:hidden">
            {items.map((entry) => (
              <div key={entry.company_id} className="card space-y-2.5 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">{entry.company_name}</p>
                    <p className="text-xs text-subtle-foreground">
                      {entry.base_currency} · {entry.member_count}{' '}
                      {t.platformSubscriptions.columnMembers} ·{' '}
                      {entry.subscription.plan_code ?? t.platformSubscriptions.noPlan}
                    </p>
                  </div>
                  <SubscriptionStatusBadge status={entry.effective_status} />
                </div>
                <p className="text-xs text-subtle-foreground">
                  {t.platformSubscriptions.columnExpires}:{' '}
                  <span className="numeric text-foreground">
                    {formatDate(entry.subscription.expires_at)}
                  </span>{' '}
                  · {renderDaysRemaining(entry)}
                </p>
                {renderActions(entry)}
              </div>
            ))}
          </div>

          <div className="card p-3">
            <PaginationControls
              skip={skip}
              limit={pageSize}
              total={total}
              onPrev={() => setSkip((prev) => Math.max(0, prev - pageSize))}
              onNext={() => setSkip((prev) => prev + pageSize)}
            />
          </div>
        </>
      )}

      <SubscriptionConfirmModal
        action={confirming?.action ?? 'activate'}
        companyName={confirming?.entry.company_name ?? ''}
        isOpen={confirming !== null}
        busy={isSubmitting}
        onClose={() => setConfirming(null)}
        onConfirm={(reason) => void handleConfirm(reason)}
      />

      <EditSubscriptionModal
        entry={editing}
        isOpen={editing !== null}
        busy={isSubmitting}
        onClose={() => setEditing(null)}
        onSubmit={(payload) => void handleEditSubmit(payload)}
      />
    </div>
  );
}
