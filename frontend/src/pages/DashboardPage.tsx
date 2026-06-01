import { motion } from 'framer-motion';
import AppShell from '../components/AppShell';
import DashboardMetricCard from '../components/DashboardMetricCard';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import { useCompanies } from '../hooks/useCompanies';
import { useDashboardData } from '../hooks/useDashboardData';
import { formatCompactCurrency as formatCurrency } from '../lib/format';
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
  FileText,
  Building2,
} from 'lucide-react';

export default function DashboardPage() {
  const {
    companies,
    selectedCompanyId,
    selectedCompany,
    selectCompany,
    isLoading: companiesLoading,
  } = useCompanies();

  const {
    data,
    isLoading: dataLoading,
    error,
    refetch,
  } = useDashboardData(selectedCompanyId);

  const isLoading = companiesLoading || dataLoading;

  // ── No companies state ──
  if (!companiesLoading && companies.length === 0) {
    return (
      <AppShell
        companies={companies}
        selectedCompany={selectedCompany}
        onSelectCompany={selectCompany}
      >
        <EmptyState
          icon={<Building2 className="w-7 h-7 text-brand-400" />}
          title="No Companies Yet"
          description="Create a company from the backend or ask an administrator for access. Once a company is available, your financial dashboard will appear here."
          className="py-32"
        />
      </AppShell>
    );
  }

  // ── Derived values ──
  const bs = data.balanceSheet;
  const pl = data.profitLoss;
  const tb = data.trialBalance;

  const totalAssets = bs?.total_assets ?? 0;
  const totalLiabilities = bs?.total_liabilities ?? 0;
  const totalEquity = bs?.total_equity ?? 0;
  const netIncome = pl?.net_income ?? 0;
  const isBalanced = tb?.is_balanced ?? false;
  const journalCount = data.journalEntries?.total ?? 0;
  const accountCount = data.accounts?.total ?? 0;

  const subtitle = selectedCompany
    ? `${selectedCompany.name} — Financial overview`
    : 'Financial overview';

  return (
    <AppShell
      companies={companies}
      selectedCompany={selectedCompany}
      onSelectCompany={selectCompany}
      pageSubtitle={subtitle}
    >
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
                  <h1 className="text-2xl font-bold text-white mb-1">Financial Overview</h1>
                  <p className="text-sm text-gray-400">
                    Real-time financial position for {selectedCompany?.name || 'your company'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {isBalanced ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Balanced
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold">
                      <XCircle className="w-3.5 h-3.5" />
                      Unbalanced
                    </span>
                  )}
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
                    netIncome >= 0
                      ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                      : 'bg-red-500/10 border border-red-500/20 text-red-400'
                  }`}>
                    {netIncome >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                    {netIncome >= 0 ? 'Profit' : 'Loss'}
                  </span>
                </div>
              </div>

              {/* Key figures row */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">Net Income</p>
                  <p className={`text-2xl font-bold tracking-tight ${netIncome >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {formatCurrency(netIncome)}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">Total Assets</p>
                  <p className="text-2xl font-bold text-white tracking-tight">{formatCurrency(totalAssets)}</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">Total Liabilities</p>
                  <p className="text-2xl font-bold text-white tracking-tight">{formatCurrency(totalLiabilities)}</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-1">Total Equity</p>
                  <p className="text-2xl font-bold text-white tracking-tight">{formatCurrency(totalEquity)}</p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Metric cards grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <DashboardMetricCard
              label="Total Assets"
              value={formatCurrency(totalAssets)}
              icon={Landmark}
              index={0}
              trend="neutral"
              iconColor="text-blue-400"
            />
            <DashboardMetricCard
              label="Total Liabilities"
              value={formatCurrency(totalLiabilities)}
              icon={HandCoins}
              index={1}
              trend="neutral"
              iconColor="text-amber-400"
            />
            <DashboardMetricCard
              label="Total Equity"
              value={formatCurrency(totalEquity)}
              icon={Scale}
              index={2}
              trend="neutral"
              iconColor="text-violet-400"
            />
            <DashboardMetricCard
              label="Net Income"
              value={formatCurrency(netIncome)}
              icon={netIncome >= 0 ? TrendingUp : TrendingDown}
              index={3}
              trend={netIncome >= 0 ? 'up' : 'down'}
              chip={netIncome >= 0 ? 'Profit' : 'Loss'}
              chipColor={netIncome >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}
              iconColor={netIncome >= 0 ? 'text-emerald-400' : 'text-red-400'}
            />
          </div>

          {/* Secondary metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <DashboardMetricCard
              label="Trial Balance"
              value={isBalanced ? 'Balanced' : 'Unbalanced'}
              icon={BarChart3}
              index={4}
              chip={isBalanced ? 'OK' : 'Warning'}
              chipColor={isBalanced ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}
              iconColor="text-blue-400"
            />
            <DashboardMetricCard
              label="Journal Entries"
              value={journalCount.toLocaleString()}
              icon={BookOpen}
              index={5}
              iconColor="text-amber-400"
            />
            <DashboardMetricCard
              label="Accounts"
              value={accountCount.toLocaleString()}
              icon={Receipt}
              index={6}
              iconColor="text-rose-400"
            />
          </div>

          {/* Reports & recent data */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Income vs Expenses */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="glass-panel p-6"
            >
              <div className="flex items-center gap-2 mb-4">
                <FileText className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-white">Profit & Loss Breakdown</h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-sm text-gray-300">Total Income</span>
                  </div>
                  <span className="text-sm font-semibold text-emerald-400">{formatCurrency(pl?.total_income ?? 0)}</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-red-400" />
                    <span className="text-sm text-gray-300">Total Expenses</span>
                  </div>
                  <span className="text-sm font-semibold text-red-400">{formatCurrency(pl?.total_expenses ?? 0)}</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <span className="text-sm font-medium text-white">Net Result</span>
                  <span className={`text-sm font-bold ${netIncome >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {formatCurrency(netIncome)}
                  </span>
                </div>
              </div>
            </motion.div>

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
                  <h3 className="text-sm font-semibold text-white">Recent Journal Entries</h3>
                </div>
                <span className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">
                  {journalCount} total
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
                <p className="text-sm text-gray-500 text-center py-6">No journal entries yet</p>
              )}
            </motion.div>
          </div>
        </>
      )}
    </AppShell>
  );
}
