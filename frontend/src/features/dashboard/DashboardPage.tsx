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
  const currentYearEarnings = Number(bs?.current_year_earnings ?? 0);
  const totalEquityAndEarnings = totalEquity + currentYearEarnings;
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
        <>
          {/* Hero financial panel */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="glass-panel relative overflow-hidden mb-6"
          >
            <div className="absolute top-0 right-0 w-72 h-72 bg-brand-500/[0.04] rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
            <div className="relative p-6 lg:p-8">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                <div>
                  <h1 className="text-2xl font-bold text-white mb-1">{t.dashboard.financialOverview}</h1>
                  <p className="text-sm text-gray-400">
                    {t.dashboard.realtimePosition} {selectedCompany?.name || ''}
                  </p>
                  <p className="text-[10px] text-gray-600 mt-0.5 italic">
                    {t.geminiAssistant.postedEntriesOnly}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {isBalanced ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {t.dashboard.balanced}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold">
                      <XCircle className="w-3.5 h-3.5" />
                      {t.dashboard.unbalanced}
                    </span>
                  )}
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
                    netIncome >= 0
                      ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                      : 'bg-red-500/10 border border-red-500/20 text-red-400'
                  }`}>
                    {netIncome >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                    {netIncome >= 0 ? t.dashboard.profit : t.dashboard.loss}
                  </span>
                </div>
              </div>

              {/* Key figures row */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">{t.dashboard.netIncome}</p>
                  <p className={`text-2xl font-bold tracking-tight ${netIncome >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {formatCurrency(netIncome)}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">{t.dashboard.totalAssets}</p>
                  <p className="text-2xl font-bold text-white tracking-tight">{formatCurrency(totalAssets)}</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">{t.dashboard.totalLiabilities}</p>
                  <p className="text-2xl font-bold text-white tracking-tight">{formatCurrency(totalLiabilities)}</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">{t.dashboard.totalEquity}</p>
                  <p className="text-2xl font-bold text-white tracking-tight">{formatCurrency(totalEquityAndEarnings)}</p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Metric cards grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <DashboardMetricCard
              label={t.dashboard.totalAssets}
              value={formatCurrency(totalAssets)}
              icon={Landmark}
              index={0}
              trend="neutral"
              iconColor="text-blue-400"
            />
            <DashboardMetricCard
              label={t.dashboard.totalLiabilities}
              value={formatCurrency(totalLiabilities)}
              icon={HandCoins}
              index={1}
              trend="neutral"
              iconColor="text-amber-400"
            />
            <DashboardMetricCard
              label={t.dashboard.totalEquity}
              value={formatCurrency(totalEquityAndEarnings)}
              icon={Scale}
              index={2}
              trend="neutral"
              iconColor="text-violet-400"
            />
            <DashboardMetricCard
              label={t.dashboard.netIncome}
              value={formatCurrency(netIncome)}
              icon={netIncome >= 0 ? TrendingUp : TrendingDown}
              index={3}
              trend={netIncome >= 0 ? 'up' : 'down'}
              chip={netIncome >= 0 ? t.dashboard.profit : t.dashboard.loss}
              chipColor={netIncome >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}
              iconColor={netIncome >= 0 ? 'text-emerald-400' : 'text-red-400'}
            />
          </div>

          {/* Secondary metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <DashboardMetricCard
              label={t.dashboard.trialBalance}
              value={isBalanced ? t.dashboard.balanced : t.dashboard.unbalanced}
              icon={BarChart3}
              index={4}
              chip={isBalanced ? t.dashboard.ok : t.dashboard.warning}
              chipColor={isBalanced ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}
              iconColor="text-blue-400"
            />
            <DashboardMetricCard
              label={t.dashboard.journalEntries}
              value={journalCount.toLocaleString()}
              icon={BookOpen}
              index={5}
              iconColor="text-amber-400"
            />
            <DashboardMetricCard
              label={t.dashboard.accounts}
              value={accountCount.toLocaleString()}
              icon={Receipt}
              index={6}
              iconColor="text-rose-400"
            />
          </div>

          {/* Charts section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Revenue vs Expenses chart */}
            <RevenueExpensesChart pl={pl} t={t} />

            {/* Financial Composition chart */}
            <FinancialCompositionChart bs={bs} t={t} />

            {/* Recent journal entries */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.6 }}
              className="glass-panel p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-semibold text-white">{t.dashboard.recentJournalEntries}</h3>
                </div>
                <span className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">
                  {journalCount} {t.common.total}
                </span>
              </div>
              {data.journalEntries && data.journalEntries.items.length > 0 ? (
                <div className="space-y-2">
                  {data.journalEntries.items.map((je) => (
                    <div key={je.id} className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                      <div className="min-w-0">
                        <p className="text-sm text-gray-200 truncate">{je.description || je.entry_no || `Entry #${je.id}`}</p>
                        <p className="text-[11px] text-gray-500">{new Date(je.entry_date).toLocaleDateString()}</p>
                      </div>
                      <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                        je.status === 'posted'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : je.status === 'draft'
                            ? 'bg-gray-500/10 text-gray-400'
                            : 'bg-amber-500/10 text-amber-400'
                      }`}>
                        {je.status}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-6">{t.dashboard.noJournalEntriesYet}</p>
              )}
            </motion.div>
          </div>
        </>
      )}
    </>
  );
}

// ── Chart tooltip ──
function ChartTooltipContent({ active, payload, label }: { active?: boolean; payload?: { value: number; fill: string; name: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-900/95 border border-white/10 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-sm font-semibold" style={{ color: p.fill }}>
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
      { name: t.charts.revenue, value: income, fill: '#34d399' },
      { name: t.charts.expenses, value: Math.abs(expenses), fill: '#f87171' },
      { name: t.charts.netIncome, value: net, fill: net >= 0 ? '#34d399' : '#f87171' },
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
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
          <Tooltip content={<ChartTooltipContent />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
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
    const equity = (parseFloat(String(bs.total_equity)) || 0) + (parseFloat(String(bs.current_year_earnings)) || 0);
    return [
      { name: t.charts.assets, value: parseFloat(String(bs.total_assets)) || 0, fill: '#60a5fa' },
      { name: t.charts.liabilities, value: parseFloat(String(bs.total_liabilities)) || 0, fill: '#fbbf24' },
      { name: t.charts.equity, value: equity, fill: '#a78bfa' },
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
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
          <Tooltip content={<ChartTooltipContent />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
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
