import { useState, useEffect, useMemo, type ReactNode } from 'react';
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
  Scale,
  CheckCircle2,
  XCircle,
  Search,
  Landmark,
  HandCoins,
  Gem,
  TrendingUp,
  TrendingDown,
  Equal,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import PageLayout from '../../../components/layout/PageLayout';
import ChartCard from '../../../components/charts/ChartCard';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import ReportHeader from '../components/ReportHeader';
import ReportSummaryTile from '../components/ReportSummaryTile';
import { reportToneText, type ReportTone } from '../components/reportTone';
import ReportSectionTable from '../components/ReportSectionTable';
import ReportExportButtons from '../components/ReportExportButtons';
import ReportDateField from '../components/ReportDateField';
import ReportSearchField from '../components/ReportSearchField';
import MoneyAmount from '../../../components/ui/MoneyAmount';
import { useBalanceSheet } from './useBalanceSheet';
import { useI18n } from '../../../i18n';
import { formatCurrency } from '../../../lib/format';
import type { Translations } from '../../../i18n/types';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

export default function BalanceSheetPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.reports.balanceSheet.pageTitle}
      pageSubtitle={t.reports.balanceSheet.pageSubtitle}
      activePath="/reports/balance-sheet"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <BalanceSheetContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface BalanceSheetContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function BalanceSheetContent({ selectedCompanyId, companiesLoading }: BalanceSheetContentProps) {
  const { t } = useI18n();
  const [asOfDate, setAsOfDate] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  const {
    data,
    isLoading: reportLoading,
    error,
    fetchReport,
  } = useBalanceSheet({ companyId: selectedCompanyId, asOfDate });

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    setSearchQuery('');
  }, [selectedCompanyId]);

  // Client-side search — inlined into useMemo for correct deps
  const filteredAssets = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.asset_lines;
    const q = searchQuery.toLowerCase();
    return data.asset_lines.filter(
      (l) => l.account_code.toLowerCase().includes(q) || l.account_name.toLowerCase().includes(q) || l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const filteredLiabilities = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.liability_lines;
    const q = searchQuery.toLowerCase();
    return data.liability_lines.filter(
      (l) => l.account_code.toLowerCase().includes(q) || l.account_name.toLowerCase().includes(q) || l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const filteredEquity = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.equity_lines;
    const q = searchQuery.toLowerCase();
    return data.equity_lines.filter(
      (l) => l.account_code.toLowerCase().includes(q) || l.account_name.toLowerCase().includes(q) || l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const totalFiltered = filteredAssets.length + filteredLiabilities.length + filteredEquity.length;
  const totalLines = data ? data.asset_lines.length + data.liability_lines.length + data.equity_lines.length : 0;

  const isLoading = companiesLoading || reportLoading;

  const handleExportCsv = async () => {
    if (!selectedCompanyId) return;
    setExporting(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/balance-sheet/export.csv', {
        company_id: selectedCompanyId,
        as_of_date: asOfDate,
      }, 'balance-sheet.csv');
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
      await downloadFile('/reports/balance-sheet/export.pdf', {
        company_id: selectedCompanyId,
        as_of_date: asOfDate,
      }, 'balance-sheet.pdf');
    } catch {
      alert(t.common.pdfExportFailed);
    } finally {
      setExportingPdf(false);
    }
  };

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={fetchReport} />;
  if (!data) return null;

  const periodLabel = data.as_of_date
    ? `${t.common.through} ${new Date(data.as_of_date).toLocaleDateString()}`
    : t.common.allTime;

  const retained = parseAmount(data.retained_earnings);
  const currentYear = parseAmount(data.current_year_earnings);

  return (
    <div className="space-y-5">
      <ReportHeader
        icon={Scale}
        title={t.reports.balanceSheet.pageTitle}
        periodLabel={periodLabel}
        columns={3}
        status={{
          label: data.is_balanced
            ? t.reports.trialBalance.balanced
            : t.reports.trialBalance.unbalanced,
          tone: data.is_balanced ? 'success' : 'danger',
          icon: data.is_balanced ? CheckCircle2 : XCircle,
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
          label={t.reports.balanceSheet.totalAssets}
          value={formatCurrency(parseAmount(data.total_assets))}
          tone="info"
          icon={Landmark}
        />
        <ReportSummaryTile
          label={t.reports.balanceSheet.liabilities}
          value={formatCurrency(parseAmount(data.total_liabilities))}
          tone="warning"
          icon={HandCoins}
        />
        <ReportSummaryTile
          label={t.reports.balanceSheet.equityAccountsTotal}
          value={formatCurrency(parseAmount(data.equity_accounts_total))}
          tone="violet"
          icon={Gem}
        />
        <ReportSummaryTile
          label={t.reports.balanceSheet.retainedEarnings}
          value={<MoneyAmount value={retained} />}
          tone={retained < 0 ? 'danger' : 'teal'}
          icon={retained < 0 ? TrendingDown : TrendingUp}
        />
        <ReportSummaryTile
          label={t.reports.balanceSheet.currentYearEarnings}
          value={<MoneyAmount value={currentYear} showPlus />}
          tone={currentYear < 0 ? 'danger' : 'success'}
          icon={currentYear < 0 ? TrendingDown : TrendingUp}
        />
        <ReportSummaryTile
          label={t.reports.balanceSheet.totalEquity}
          value={formatCurrency(parseAmount(data.total_equity))}
          icon={Equal}
          emphasis
        />
      </ReportHeader>

      {/* Accounting equation */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05 }}
        className="card px-5 py-4"
      >
        <p className="overline mb-3">{t.reports.balanceSheet.liabilitiesAndEquity}</p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3 text-sm">
          <EquationTerm
            icon={Landmark}
            tone="info"
            label={t.reports.balanceSheet.assets}
            value={formatCurrency(parseAmount(data.total_assets))}
          />
          <EquationOperator symbol="=" />
          <EquationTerm
            icon={HandCoins}
            tone="warning"
            label={t.reports.balanceSheet.liabilities}
            value={formatCurrency(parseAmount(data.total_liabilities))}
          />
          <EquationOperator symbol="+" />
          <EquationTerm
            icon={Gem}
            tone="violet"
            label={t.reports.balanceSheet.equityAccountsTotal}
            value={formatCurrency(parseAmount(data.equity_accounts_total))}
          />
          <EquationOperator symbol="+" />
          <EquationTerm
            icon={retained < 0 ? TrendingDown : TrendingUp}
            tone={retained < 0 ? 'danger' : 'teal'}
            label={t.reports.balanceSheet.retainedEarnings}
            value={<MoneyAmount value={retained} />}
          />
          <EquationOperator symbol="+" />
          <EquationTerm
            icon={currentYear < 0 ? TrendingDown : TrendingUp}
            tone={currentYear < 0 ? 'danger' : 'success'}
            label={t.reports.balanceSheet.currentYearEarnings}
            value={<MoneyAmount value={currentYear} showPlus />}
          />
        </div>
      </motion.div>

      <BSChart data={data} t={t} />

      {/* Toolbar */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="filter-bar"
      >
        <ReportDateField label={t.common.asOfDate} value={asOfDate} onChange={setAsOfDate} />
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
          icon={<Scale className="h-7 w-7 text-primary" />}
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
        <div className="space-y-5">
          <ReportSectionTable
            title={t.reports.balanceSheet.assets}
            icon={Landmark}
            tone="info"
            lines={filteredAssets}
            totalLabel={t.reports.balanceSheet.totalAssets}
            totalAmount={data.total_assets}
            delay={0.15}
          />
          <ReportSectionTable
            title={t.reports.balanceSheet.liabilities}
            icon={HandCoins}
            tone="warning"
            lines={filteredLiabilities}
            totalLabel={t.reports.balanceSheet.totalLiabilities}
            totalAmount={data.total_liabilities}
            delay={0.2}
          />
          <ReportSectionTable
            title={t.reports.balanceSheet.equity}
            icon={Gem}
            tone="violet"
            lines={filteredEquity}
            totalLabel={t.reports.balanceSheet.equityAccountsTotal}
            totalAmount={data.equity_accounts_total}
            delay={0.25}
          />
        </div>
      )}
    </div>
  );
}

function EquationOperator({ symbol }: { symbol: string }) {
  return (
    <span aria-hidden className="text-base font-semibold text-subtle-foreground">
      {symbol}
    </span>
  );
}

function EquationTerm({
  icon: Icon,
  tone,
  label,
  value,
}: {
  icon: LucideIcon;
  tone: ReportTone;
  label: string;
  /** A node so signed figures can bring their own positive/negative colour. */
  value: ReactNode;
}) {
  return (
    <span className="flex items-center gap-2">
      <Icon aria-hidden className={`h-4 w-4 ${reportToneText[tone]}`} />
      <span className="text-muted-foreground">{label}</span>
      <span className={`numeric font-semibold ${reportToneText[tone]}`}>{value}</span>
    </span>
  );
}

function BSChart({ data, t }: { data: { total_assets: string; total_liabilities: string; equity_accounts_total: string; retained_earnings: string; current_year_earnings: string }; t: Translations }) {
  const parseAmt = (v: string) => parseFloat(v) || 0;

  const chartData = useMemo(() => {
    const assets = parseAmt(data.total_assets);
    const liab = parseAmt(data.total_liabilities);
    const equityAccounts = parseAmt(data.equity_accounts_total);
    const retained = parseAmt(data.retained_earnings);
    const cye = parseAmt(data.current_year_earnings);
    if (assets === 0 && liab === 0 && equityAccounts === 0 && retained === 0 && cye === 0) return [];
    const items = [
      { name: t.charts.assets, value: assets, fill: 'var(--info)' },
      { name: t.charts.liabilities, value: liab, fill: 'var(--warning)' },
      { name: t.reports.balanceSheet.equityAccountsTotal, value: equityAccounts, fill: 'var(--violet)' },
      { name: t.reports.balanceSheet.retainedEarnings, value: retained, fill: retained >= 0 ? 'var(--teal)' : 'var(--danger)' },
      { name: t.reports.balanceSheet.currentYearEarnings, value: cye, fill: cye >= 0 ? 'var(--success)' : 'var(--danger)' },
    ];
    // Filter out zero values for a cleaner chart
    return items.filter((item) => item.value !== 0);
  }, [data, t]);

  if (chartData.length === 0) return null;

  return (
    <ChartCard title={t.charts.financialComposition} delay={0.08} height={220}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }} barSize={44}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey="name" tick={{ fill: 'var(--muted-foreground)', fontSize: 10 }} axisLine={false} tickLine={false} />
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
