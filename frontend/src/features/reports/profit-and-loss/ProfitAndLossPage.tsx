import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
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
import {
  FileText,
  TrendingUp,
  TrendingDown,
  Search,
  ArrowUpRight,
  ArrowDownRight,
  Wallet,
} from 'lucide-react';
import PageLayout from '../../../components/layout/PageLayout';
import ChartCard from '../../../components/charts/ChartCard';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import ReportHeader from '../components/ReportHeader';
import ReportSummaryTile from '../components/ReportSummaryTile';
import ReportSectionTable from '../components/ReportSectionTable';
import ReportExportButtons from '../components/ReportExportButtons';
import ReportDateField from '../components/ReportDateField';
import ReportSearchField from '../components/ReportSearchField';
import { useProfitAndLoss } from './useProfitAndLoss';
import { useI18n } from '../../../i18n';
import { formatCurrency, formatSignedCurrency } from '../../../lib/format';
import type { Translations } from '../../../i18n/types';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

export default function ProfitAndLossPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.reports.profitAndLoss.pageTitle}
      pageSubtitle={t.reports.profitAndLoss.pageSubtitle}
      activePath="/reports/profit-and-loss"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <ProfitAndLossContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface ProfitAndLossContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function ProfitAndLossContent({ selectedCompanyId, companiesLoading }: ProfitAndLossContentProps) {
  const { t } = useI18n();
  const [searchParams] = useSearchParams();
  const [startDate, setStartDate] = useState<string | null>(() => searchParams.get('start_date'));
  const [endDate, setEndDate] = useState<string | null>(() => searchParams.get('end_date'));
  const [searchQuery, setSearchQuery] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  const {
    data,
    isLoading: reportLoading,
    error,
    fetchReport,
  } = useProfitAndLoss({ companyId: selectedCompanyId, startDate, endDate });

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    setSearchQuery('');
  }, [selectedCompanyId]);

  // Client-side search across both income and expense lines
  const filteredIncome = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.income_lines;
    const q = searchQuery.toLowerCase();
    return data.income_lines.filter(
      (l) =>
        l.account_code.toLowerCase().includes(q) ||
        l.account_name.toLowerCase().includes(q) ||
        l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const filteredExpenses = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.expense_lines;
    const q = searchQuery.toLowerCase();
    return data.expense_lines.filter(
      (l) =>
        l.account_code.toLowerCase().includes(q) ||
        l.account_name.toLowerCase().includes(q) ||
        l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const totalFiltered = filteredIncome.length + filteredExpenses.length;
  const totalLines = data ? data.income_lines.length + data.expense_lines.length : 0;

  const isLoading = companiesLoading || reportLoading;

  const handleExportCsv = async () => {
    if (!selectedCompanyId) return;
    setExporting(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/profit-loss/export.csv', {
        company_id: selectedCompanyId,
        start_date: startDate,
        end_date: endDate,
      }, 'profit-and-loss.csv');
    } catch {
      alert(t.common.exportFailed);
    } finally {
      setExporting(false);
    }
  };

  const handleExportPdf = async () => {
    if (!selectedCompanyId) return;
    setExportingPdf(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/profit-loss/export.pdf', {
        company_id: selectedCompanyId,
        start_date: startDate,
        end_date: endDate,
      }, 'profit-and-loss.pdf');
    } catch {
      alert(t.common.pdfExportFailed);
    } finally {
      setExportingPdf(false);
    }
  };

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={fetchReport} />;
  if (!data) return null;

  const netProfit = parseAmount(data.net_profit);
  const isProfit = netProfit >= 0;

  const periodLabel =
    data.start_date && data.end_date
      ? `${new Date(data.start_date).toLocaleDateString()} — ${new Date(data.end_date).toLocaleDateString()}`
      : data.start_date
        ? `${t.common.from} ${new Date(data.start_date).toLocaleDateString()}`
        : data.end_date
          ? `${t.common.through} ${new Date(data.end_date).toLocaleDateString()}`
          : t.common.allTime;

  return (
    <div className="space-y-5">
      <ReportHeader
        icon={FileText}
        title={t.reports.profitAndLoss.pageTitle}
        periodLabel={periodLabel}
        columns={3}
        status={{
          label: t.reports.profitAndLoss.netIncome,
          tone: isProfit ? 'success' : 'danger',
          icon: isProfit ? TrendingUp : TrendingDown,
        }}
        actions={
          <ReportExportButtons
            onExportCsv={handleExportCsv}
            onExportPdf={handleExportPdf}
            exportingCsv={exporting}
            exportingPdf={exportingPdf}
          />
        }
      >
        <ReportSummaryTile
          label={t.reports.profitAndLoss.totalIncome}
          value={formatCurrency(parseAmount(data.total_income))}
          tone="success"
          icon={ArrowDownRight}
        />
        <ReportSummaryTile
          label={t.reports.profitAndLoss.totalExpenses}
          value={formatCurrency(parseAmount(data.total_expenses))}
          tone="danger"
          icon={ArrowUpRight}
        />
        <ReportSummaryTile
          label={t.reports.profitAndLoss.netResult}
          value={formatSignedCurrency(netProfit)}
          tone={isProfit ? 'success' : 'danger'}
          icon={Wallet}
          hint={t.reports.profitAndLoss.incomeMinusExpenses}
          emphasis
        />
      </ReportHeader>

      <PLChart data={data} t={t} />

      {/* Toolbar */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05 }}
        className="filter-bar"
      >
        <ReportDateField
          label={t.common.startDate}
          value={startDate}
          onChange={setStartDate}
          max={endDate ?? undefined}
        />
        <ReportDateField
          label={t.common.endDate}
          value={endDate}
          onChange={setEndDate}
          min={startDate ?? undefined}
        />
        <ReportSearchField
          label={t.common.search}
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder={t.common.searchByAccountPlaceholder}
        />
        <p className="numeric pb-2.5 text-xs text-subtle-foreground">
          {totalFiltered} {t.common.of} {totalLines} {t.reports.shared.accountsShown}
        </p>
      </motion.div>

      {totalLines === 0 && (
        <EmptyState
          icon={<FileText className="h-7 w-7 text-primary" />}
          title={t.reports.shared.noDataTitle}
          description={t.reports.shared.noDataDescription}
        />
      )}

      {totalLines > 0 && totalFiltered === 0 && (
        <EmptyState
          icon={<Search className="h-7 w-7 text-primary" />}
          title={t.reports.shared.noMatchTitle}
          description={t.reports.shared.noMatchDescription}
          action={
            <button type="button" onClick={() => setSearchQuery('')} className="btn btn-secondary btn-sm">
              {t.common.clearSearch}
            </button>
          }
        />
      )}

      {totalFiltered > 0 && (
        <>
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <ReportSectionTable
              title={t.reports.profitAndLoss.income}
              icon={ArrowDownRight}
              tone="success"
              lines={filteredIncome}
              totalLabel={t.reports.profitAndLoss.totalIncome}
              totalAmount={data.total_income}
              delay={0.1}
            />
            <ReportSectionTable
              title={t.reports.profitAndLoss.expenses}
              icon={ArrowUpRight}
              tone="danger"
              lines={filteredExpenses}
              totalLabel={t.reports.profitAndLoss.totalExpenses}
              totalAmount={data.total_expenses}
              delay={0.15}
            />
          </div>

          {/* Bottom line */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className={`card flex flex-wrap items-center justify-between gap-5 border-2 bg-surface-sunken px-6 py-6 ${
              isProfit ? 'border-success-border' : 'border-danger-border'
            }`}
          >
            <div className="flex items-center gap-3">
              <span
                aria-hidden
                className={`badge tone-${isProfit ? 'success' : 'danger'} h-11 w-11 flex-shrink-0 justify-center rounded-lg p-0`}
              >
                {isProfit ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
              </span>
              <div>
                <p className="text-base font-bold text-foreground">
                  {t.reports.profitAndLoss.netIncome}
                </p>
                <p className="text-xs text-subtle-foreground">
                  {t.reports.profitAndLoss.incomeMinusExpenses}
                </p>
              </div>
            </div>
            <p
              className={`numeric text-3xl font-bold ${isProfit ? 'text-success' : 'text-danger'}`}
            >
              {formatSignedCurrency(netProfit)}
            </p>
          </motion.div>
        </>
      )}
    </div>
  );
}

function PLChart({ data, t }: { data: { total_income: string; total_expenses: string; net_profit: string }; t: Translations }) {
  const chartData = useMemo(() => {
    const income = parseAmount(data.total_income);
    const expenses = Math.abs(parseAmount(data.total_expenses));
    const net = parseAmount(data.net_profit);
    if (income === 0 && expenses === 0) return [];
    return [
      { name: t.charts.revenue, value: income, fill: 'var(--success)' },
      { name: t.charts.expenses, value: expenses, fill: 'var(--danger)' },
      { name: t.charts.netIncome, value: net, fill: net >= 0 ? 'var(--success)' : 'var(--danger)' },
    ];
  }, [data, t]);

  if (chartData.length === 0) return null;

  return (
    <ChartCard title={t.charts.revenueVsExpenses} delay={0.08} height={220}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }} barSize={48}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey="name" tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
          <Tooltip
            cursor={{ fill: 'var(--surface-muted)' }}
            contentStyle={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
            itemStyle={{ color: 'var(--foreground)' }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any) => Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          />
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
