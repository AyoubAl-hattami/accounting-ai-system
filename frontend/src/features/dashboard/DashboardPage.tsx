import { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import PageLayout from '../../components/layout/PageLayout';
import DashboardMetricCard from '../../components/ui/DashboardMetricCard';
import MoneyAmount from '../../components/ui/MoneyAmount';
import ChartCard from '../../components/charts/ChartCard';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import { useDashboardData } from './useDashboardData';
import { useI18n } from '../../i18n';
import { formatCompactCurrency as formatCurrency } from '../../lib/format';
import {
  Landmark,
  HandCoins,
  Scale,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  XCircle,
  BookOpen,
  Receipt,
  BarChart3,
} from 'lucide-react';

export default function DashboardPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.dashboard.pageTitle}
      pageSubtitle={t.dashboard.pageSubtitle}
    >
      {({ selectedCompanyId, selectedCompany, companiesLoading }) => (
        <DashboardContent
          selectedCompanyId={selectedCompanyId}
          selectedCompany={selectedCompany}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface DashboardContentProps {
  selectedCompanyId: number | null;
  selectedCompany: { name: string } | null;
  companiesLoading: boolean;
}

function DashboardContent({ selectedCompanyId, selectedCompany, companiesLoading }: DashboardContentProps) {
  const { t } = useI18n();
  const {
    data,
    isLoading: dataLoading,
    error,
    refetch,
  } = useDashboardData(selectedCompanyId);

  const isLoading = companiesLoading || dataLoading;

  // ── Derived values ──
  const bs = data.balanceSheet;
  const pl = data.profitLoss;
  const tb = data.trialBalance;

  const totalAssets = Number(bs?.total_assets ?? 0);
  const totalLiabilities = Number(bs?.total_liabilities ?? 0);
  const totalEquity = Number(bs?.total_equity ?? 0);
  const totalEquityAndEarnings = totalEquity;
  const netIncome = Number(pl?.net_profit ?? 0);
  const isBalanced = bs?.is_balanced ?? tb?.is_balanced ?? false;
  const journalCount = data.journalEntries?.total ?? 0;
  const accountCount = data.accounts?.total ?? 0;

  return (
    <>
      {/* Loading */}
      {isLoading && <LoadingState />}

      {/* Error */}
      {!isLoading && error && <ErrorState message={error} onRetry={refetch} />}

      {/* Dashboard content */}
      {!isLoading && !error && (
        <div className="space-y-8">
          <section>
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="page-title">{t.dashboard.financialOverview}</h2>
                <p className="page-description">
                  {t.dashboard.realtimePosition} {selectedCompany?.name || ''}
                </p>
                <p className="mt-1 text-xs text-subtle-foreground">
                  {t.geminiAssistant.postedEntriesOnly}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`badge ${isBalanced ? 'tone-success' : 'tone-warning'}`}>
                  {isBalanced ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5" />
                  )}
                  {isBalanced ? t.dashboard.balanced : t.dashboard.unbalanced}
                </span>
                <span className={`badge ${netIncome >= 0 ? 'tone-success' : 'tone-danger'}`}>
                  {netIncome >= 0 ? (
                    <TrendingUp className="h-3.5 w-3.5" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5" />
                  )}
                  {netIncome >= 0 ? t.dashboard.profit : t.dashboard.loss}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <DashboardMetricCard
                label={t.dashboard.totalAssets}
                value={formatCurrency(totalAssets)}
                icon={Landmark}
                index={0}
                tone="info"
              />
              <DashboardMetricCard
                label={t.dashboard.totalLiabilities}
                value={formatCurrency(totalLiabilities)}
                icon={HandCoins}
                index={1}
                tone="warning"
              />
              <DashboardMetricCard
                label={t.dashboard.totalEquity}
                value={formatCurrency(totalEquityAndEarnings)}
                icon={Scale}
                index={2}
                tone="violet"
              />
              <DashboardMetricCard
                label={t.dashboard.netIncome}
                value={<MoneyAmount value={netIncome} showPlus compact />}
                icon={netIncome >= 0 ? TrendingUp : TrendingDown}
                index={3}
                tone={netIncome >= 0 ? 'success' : 'danger'}
                chip={netIncome >= 0 ? t.dashboard.profit : t.dashboard.loss}
              />
            </div>
          </section>

          <section>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <DashboardMetricCard
                label={t.dashboard.trialBalance}
                value={isBalanced ? t.dashboard.balanced : t.dashboard.unbalanced}
                icon={BarChart3}
                index={0}
                tone="info"
                chip={isBalanced ? t.dashboard.ok : t.dashboard.warning}
                chipTone={isBalanced ? 'success' : 'warning'}
              />
              <DashboardMetricCard
                label={t.dashboard.journalEntries}
                value={journalCount.toLocaleString()}
                icon={BookOpen}
                index={1}
                tone="teal"
              />
              <DashboardMetricCard
                label={t.dashboard.accounts}
                value={accountCount.toLocaleString()}
                icon={Receipt}
                index={2}
                tone="primary"
              />
            </div>
          </section>

          <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <RevenueExpensesChart pl={pl} t={t} />
            <FinancialCompositionChart bs={bs} t={t} />

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.2 }}
              className="card p-5"
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <h3 className="section-title">{t.dashboard.recentJournalEntries}</h3>
                <span className="overline">
                  {journalCount} {t.common.total}
                </span>
              </div>
              {data.journalEntries && data.journalEntries.items.length > 0 ? (
                <ul className="divide-y divide-border-subtle">
                  {data.journalEntries.items.map((je) => (
                    <li key={je.id} className="flex items-center justify-between gap-3 py-2.5">
                      <div className="min-w-0">
                        <p className="truncate text-sm text-foreground">
                          {je.description || je.entry_no || `Entry #${je.id}`}
                        </p>
                        <p className="numeric text-xs text-subtle-foreground">
                          {new Date(je.entry_date).toLocaleDateString()}
                        </p>
                      </div>
                      <span
                        className={`badge badge-uppercase flex-shrink-0 ${
                          je.status === 'posted'
                            ? 'tone-success'
                            : je.status === 'draft'
                              ? 'tone-neutral'
                              : 'tone-warning'
                        }`}
                      >
                        {je.status}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  {t.dashboard.noJournalEntriesYet}
                </p>
              )}
            </motion.div>
          </section>
        </div>
      )}
    </>
  );
}

// ── Chart tooltip ──
function ChartTooltipContent({ active, payload, label }: { active?: boolean; payload?: { value: number; fill: string; name: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-xl border px-3 py-2 shadow-floating">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-sm font-semibold numeric" style={{ color: p.fill }}>
          {p.name}: {p.value?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>
      ))}
    </div>
  );
}

// ── Revenue vs Expenses chart ──
function RevenueExpensesChart({ pl, t }: { pl: DashboardContentProps['selectedCompany'] extends never ? never : ReturnType<typeof useDashboardData>['data']['profitLoss']; t: ReturnType<typeof useI18n>['t'] }) {
  const chartData = useMemo(() => {
    if (!pl) return [];
    const income = parseFloat(String(pl.total_income)) || 0;
    const expenses = parseFloat(String(pl.total_expenses)) || 0;
    const net = parseFloat(String(pl.net_profit)) || 0;
    return [
      { name: t.charts.revenue, value: income, fill: 'var(--success)' },
      { name: t.charts.expenses, value: Math.abs(expenses), fill: 'var(--danger)' },
      { name: t.charts.netIncome, value: net, fill: net >= 0 ? 'var(--success)' : 'var(--danger)' },
    ];
  }, [pl, t]);

  return (
    <ChartCard
      title={t.charts.revenueVsExpenses}
      isEmpty={chartData.length === 0}
      emptyMessage={t.charts.noChartData}
      delay={0.5}
      height={240}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }} barSize={48}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey="name" tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
          <Tooltip content={<ChartTooltipContent />} cursor={{ fill: 'var(--surface-muted)' }} />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ── Financial Composition chart ──
function FinancialCompositionChart({ bs, t }: { bs: ReturnType<typeof useDashboardData>['data']['balanceSheet']; t: ReturnType<typeof useI18n>['t'] }) {
  const chartData = useMemo(() => {
    if (!bs) return [];
    const equity = parseFloat(String(bs.total_equity)) || 0;
    return [
      { name: t.charts.assets, value: parseFloat(String(bs.total_assets)) || 0, fill: 'var(--info)' },
      { name: t.charts.liabilities, value: parseFloat(String(bs.total_liabilities)) || 0, fill: 'var(--warning)' },
      { name: t.charts.equity, value: equity, fill: 'var(--violet)' },
    ];
  }, [bs, t]);

  return (
    <ChartCard
      title={t.charts.financialComposition}
      isEmpty={chartData.length === 0}
      emptyMessage={t.charts.noChartData}
      delay={0.6}
      height={240}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }} barSize={48}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey="name" tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
          <Tooltip content={<ChartTooltipContent />} cursor={{ fill: 'var(--surface-muted)' }} />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
