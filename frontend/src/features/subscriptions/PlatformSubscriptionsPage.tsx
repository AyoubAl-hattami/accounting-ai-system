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

  const renderActions = (entry: CompanySubscription) => (
    <div className="flex flex-wrap items-center justify-end gap-1.5">
      <button
        type="button"
        onClick={() => setConfirming({ action: 'activate', entry })}
        className="btn btn-secondary btn-sm"
      >
        <PlayCircle aria-hidden className="h-3.5 w-3.5" />
        {t.platformSubscriptions.actionActivate}
      </button>
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
        onClick={() => void handleExtend(entry, 'year')}
        disabled={isSubmitting}
        className="btn btn-secondary btn-sm"
      >
        <CalendarClock aria-hidden className="h-3.5 w-3.5" />
        {t.platformSubscriptions.actionExtendYear}
      </button>
      <button
        type="button"
        onClick={() => setEditing(entry)}
        className="btn btn-secondary btn-sm"
      >
        <Pencil aria-hidden className="h-3.5 w-3.5" />
        {t.platformSubscriptions.actionEdit}
      </button>
      <button
        type="button"
        onClick={() => setConfirming({ action: 'suspend', entry })}
        className="btn btn-tone tone-warning btn-sm"
      >
        <PauseCircle aria-hidden className="h-3.5 w-3.5" />
        {t.platformSubscriptions.actionSuspend}
      </button>
      <button
        type="button"
        onClick={() => setConfirming({ action: 'cancel', entry })}
        className="btn btn-danger btn-sm"
      >
        <XCircle aria-hidden className="h-3.5 w-3.5" />
        {t.platformSubscriptions.actionCancel}
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
          <div className="card hidden overflow-hidden xl:block">
            <div className="table-wrap">
              <table className="data-table">
                <caption className="sr-only">{t.platformSubscriptions.pageTitle}</caption>
                <thead>
                  <tr>
                    <th scope="col">{t.platformSubscriptions.columnCompany}</th>
                    <th scope="col">{t.platformSubscriptions.columnCurrency}</th>
                    <th scope="col">{t.platformSubscriptions.columnEffectiveStatus}</th>
                    <th scope="col">{t.platformSubscriptions.columnExpires}</th>
                    <th scope="col">{t.platformSubscriptions.columnDaysRemaining}</th>
                    <th scope="col">{t.platformSubscriptions.columnPlan}</th>
                    <th scope="col">{t.platformSubscriptions.columnMembers}</th>
                    <th scope="col" className="text-end">
                      {t.platformSubscriptions.columnActions}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((entry) => (
                    <tr key={entry.company_id}>
                      <th scope="row" className="text-start align-middle font-medium">
                        {entry.company_name}
                      </th>
                      <td>{entry.base_currency}</td>
                      <td>
                        <SubscriptionStatusBadge status={entry.effective_status} />
                      </td>
                      <td className="numeric">{formatDate(entry.subscription.expires_at)}</td>
                      <td>{renderDaysRemaining(entry)}</td>
                      <td>{entry.subscription.plan_code ?? t.platformSubscriptions.noPlan}</td>
                      <td className="numeric">{entry.member_count}</td>
                      <td>{renderActions(entry)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="space-y-3 xl:hidden">
            {items.map((entry) => (
              <div key={entry.company_id} className="card space-y-3 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">{entry.company_name}</p>
                    <p className="text-xs text-subtle-foreground">
                      {entry.base_currency} · {entry.member_count}{' '}
                      {t.platformSubscriptions.columnMembers}
                    </p>
                  </div>
                  <SubscriptionStatusBadge status={entry.effective_status} />
                </div>
                <dl className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <dt className="text-subtle-foreground">
                      {t.platformSubscriptions.columnExpires}
                    </dt>
                    <dd className="numeric text-foreground">
                      {formatDate(entry.subscription.expires_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-subtle-foreground">
                      {t.platformSubscriptions.columnDaysRemaining}
                    </dt>
                    <dd className="text-foreground">{renderDaysRemaining(entry)}</dd>
                  </div>
                  <div>
                    <dt className="text-subtle-foreground">
                      {t.platformSubscriptions.columnPlan}
                    </dt>
                    <dd className="text-foreground">
                      {entry.subscription.plan_code ?? t.platformSubscriptions.noPlan}
                    </dd>
                  </div>
                </dl>
                {renderActions(entry)}
              </div>
            ))}
          </div>

          <div className="card p-4">
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
