import { useLayoutEffect } from 'react';
import {
  Ban,
  Building2,
  CalendarClock,
  CheckCircle2,
  CircleOff,
  Clock,
  PauseCircle,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import ErrorState from '../../components/feedback/ErrorState';
import LoadingState from '../../components/feedback/LoadingState';
import DashboardMetricCard from '../../components/ui/DashboardMetricCard';
import { usePageMeta } from '../../components/layout/pageMeta';
import { useI18n } from '../../i18n';
import type { SubscriptionStatus } from '../../api/types';
import { usePlatformDashboard } from './usePlatformDashboard';

const STATUS_APPEARANCE: Record<SubscriptionStatus, { tone: string; icon: LucideIcon }> = {
  active: { tone: 'tone-success', icon: CheckCircle2 },
  trial: { tone: 'tone-primary', icon: Sparkles },
  past_due: { tone: 'tone-warning', icon: Clock },
  suspended: { tone: 'tone-danger', icon: PauseCircle },
  cancelled: { tone: 'tone-neutral', icon: Ban },
};

export default function PlatformDashboardPage() {
  const { t, language } = useI18n();
  const { setMeta } = usePageMeta();
  const { data, isLoading, error, refetch } = usePlatformDashboard();
  const copy = t.platformDashboard;

  useLayoutEffect(() => {
    setMeta({
      pageTitle: copy.pageTitle,
      pageSubtitle: copy.pageSubtitle,
      activePath: '/platform/dashboard',
    });
  }, [copy, setMeta]);

  if (isLoading) return <LoadingState />;
  if (error || !data) return <ErrorState message={copy.loadFailed} onRetry={refetch} />;

  const blocked =
    data.past_due_subscriptions + data.suspended_subscriptions + data.cancelled_subscriptions;
  const distribution = [
    ['trial', data.trial_subscriptions, 'bg-info'],
    ['active', data.active_subscriptions, 'bg-success'],
    ['past_due', data.past_due_subscriptions, 'bg-warning'],
    ['suspended', data.suspended_subscriptions, 'bg-danger'],
    ['cancelled', data.cancelled_subscriptions, 'bg-muted-foreground'],
  ] as const;

  return (
    <div className="space-y-6">
      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <DashboardMetricCard label={copy.totalClients} value={data.total_clients} icon={Building2} tone="primary" />
        <DashboardMetricCard label={copy.trialSubscriptions} value={data.trial_subscriptions} icon={CalendarClock} tone="info" />
        <DashboardMetricCard label={copy.activeSubscriptions} value={data.active_subscriptions} icon={CheckCircle2} tone="success" />
        <DashboardMetricCard label={copy.blockedSubscriptions} value={blocked} icon={PauseCircle} tone="warning" />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.6fr)]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
            <h2 className="section-title">{copy.recentClients}</h2>
            <Link to="/platform/onboarding" className="btn btn-secondary btn-sm">
              {t.nav.platformOnboarding}
            </Link>
          </div>
          {data.recent_clients.length === 0 ? (
            <div className="px-4 py-12 text-center text-sm text-muted-foreground">
              <CircleOff aria-hidden className="mx-auto mb-3 h-5 w-5" />
              {copy.noClients}
            </div>
          ) : (
            <ul className="divide-y divide-border-subtle">
              {data.recent_clients.map((client) => (
                <li key={client.company_id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">{client.company_name}</p>
                    <p className="truncate text-xs text-subtle-foreground">
                      {client.primary_admin_email ?? copy.noAdminEmail}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 sm:flex-shrink-0">
                    <span className="numeric text-xs text-subtle-foreground">
                      {client.created_at
                        ? new Date(client.created_at).toLocaleDateString(language === 'ar' ? 'ar' : 'en-GB')
                        : copy.unknownDate}
                    </span>
                    <PlatformStatusBadge status={client.effective_status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card p-4">
          <h2 className="section-title mb-4">{copy.statusDistribution}</h2>
          <div className="space-y-4">
            {distribution.map(([status, count, color]) => {
              const width = data.total_clients ? Math.max(2, (count / data.total_clients) * 100) : 0;
              return (
                <div key={status}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{t.subscriptionStatus[status]}</span>
                    <span className="numeric font-medium text-foreground">{count}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-surface-muted">
                    <div className={`h-full ${color}`} style={{ width: `${width}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          <Link to="/platform/subscriptions" className="btn btn-secondary btn-block mt-6">
            {copy.manageSubscriptions}
          </Link>
        </div>
      </section>
    </div>
  );
}

function PlatformStatusBadge({ status }: { status: SubscriptionStatus }) {
  const { t } = useI18n();
  const { tone, icon: Icon } = STATUS_APPEARANCE[status];
  return (
    <span className={`badge ${tone}`}>
      <Icon aria-hidden className="h-3 w-3" />
      {t.subscriptionStatus[status]}
    </span>
  );
}
