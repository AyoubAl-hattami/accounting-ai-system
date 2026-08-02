import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  BarChart3,
  CheckCircle2,
  XCircle,
  Search,
  ArrowDownRight,
  ArrowUpRight,
  Scale,
} from 'lucide-react';
import PageLayout from '../../../components/layout/PageLayout';
import ChartCard from '../../../components/charts/ChartCard';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import { AccountTypeBadge } from '../../../entities/account';
import ReportHeader from '../components/ReportHeader';
import ReportSummaryTile from '../components/ReportSummaryTile';
import ReportExportButtons from '../components/ReportExportButtons';
import ReportDateField from '../components/ReportDateField';
import ReportSearchField from '../components/ReportSearchField';
import { useTrialBalance } from './useTrialBalance';
import { useI18n } from '../../../i18n';
import { formatCurrency } from '../../../lib/format';
import type { TrialBalanceLine } from '../../../api/types';
import type { Translations } from '../../../i18n/types';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

/** Zero balances are shown as an em dash so real figures stand out when scanning. */
function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(n);
}

export default function TrialBalancePage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.reports.trialBalance.pageTitle}
      pageSubtitle={t.reports.trialBalance.pageSubtitle}
      activePath="/reports/trial-balance"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <TrialBalanceContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface TrialBalanceContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function TrialBalanceContent({ selectedCompanyId, companiesLoading }: TrialBalanceContentProps) {
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
  } = useTrialBalance({ companyId: selectedCompanyId, asOfDate });

  // Fetch on mount and when company/date changes
  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Reset filters on company change
  useEffect(() => {
    setSearchQuery('');
  }, [selectedCompanyId]);

  // Client-side search
  const filteredLines = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.lines;
    const q = searchQuery.toLowerCase();
    return data.lines.filter(
      (l) =>
        l.account_code.toLowerCase().includes(q) ||
        l.account_name.toLowerCase().includes(q) ||
        l.account_type.toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  const isLoading = companiesLoading || reportLoading;

  const handleExportCsv = async () => {
    if (!selectedCompanyId) return;
    setExporting(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/trial-balance/export.csv', {
        company_id: selectedCompanyId,
        as_of_date: asOfDate,
      }, 'trial-balance.csv');
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
      await downloadFile('/reports/trial-balance/export.pdf', {
        company_id: selectedCompanyId,
        as_of_date: asOfDate,
      }, 'trial-balance.pdf');
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

  return (
    <div className="space-y-5">
      <ReportHeader
        icon={BarChart3}
        title={t.reports.trialBalance.pageTitle}
        periodLabel={periodLabel}
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
          label={t.common.debitTotal}
          value={formatCurrency(parseAmount(data.total_debit))}
          tone="success"
          icon={ArrowDownRight}
        />
        <ReportSummaryTile
          label={t.common.creditTotal}
          value={formatCurrency(parseAmount(data.total_credit))}
          tone="danger"
          icon={ArrowUpRight}
        />
        <ReportSummaryTile
          label={t.reports.trialBalance.debitBalance}
          value={formatCurrency(parseAmount(data.total_debit_balance))}
          icon={Scale}
        />
        <ReportSummaryTile
          label={t.reports.trialBalance.creditBalance}
          value={formatCurrency(parseAmount(data.total_credit_balance))}
          icon={Scale}
        />
      </ReportHeader>

      {data.lines.length > 0 && <TopAccountsChart lines={data.lines} t={t} />}

      {/* Toolbar */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05 }}
        className="filter-bar"
      >
        <ReportDateField
          label={t.common.asOfDate}
          value={asOfDate}
          onChange={setAsOfDate}
        />
        <ReportSearchField
          label={t.common.search}
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder={t.common.searchByAccountPlaceholder}
        />
        <p className="numeric pb-2.5 text-xs text-subtle-foreground">
          {filteredLines.length} {t.common.of} {data.lines.length} {t.reports.shared.accountsShown}
        </p>
      </motion.div>

      {data.lines.length === 0 && (
        <EmptyState
          icon={<BarChart3 className="h-7 w-7 text-primary" />}
          title={t.reports.shared.noDataTitle}
          description={t.reports.shared.noDataDescription}
        />
      )}

      {data.lines.length > 0 && filteredLines.length === 0 && (
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

      {filteredLines.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          {/* Desktop table */}
          <div className="card hidden overflow-hidden md:block">
            <div className="table-wrap">
              <table className="data-table">
                <caption className="sr-only">
                  {t.reports.trialBalance.pageTitle} — {periodLabel}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">{t.common.code}</th>
                    <th scope="col">{t.reports.trialBalance.accountName}</th>
                    <th scope="col">{t.common.type}</th>
                    <th scope="col" className="cell-numeric">{t.common.debitTotal}</th>
                    <th scope="col" className="cell-numeric">{t.common.creditTotal}</th>
                    <th scope="col" className="cell-numeric">{t.reports.trialBalance.debitBalance}</th>
                    <th scope="col" className="cell-numeric">{t.reports.trialBalance.creditBalance}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLines.map((line) => (
                    <tr key={line.account_id}>
                      <td>
                        <span className="numeric text-sm font-semibold text-primary">
                          {line.account_code}
                        </span>
                      </td>
                      <td className="font-medium">{line.account_name}</td>
                      <td>
                        <AccountTypeBadge type={line.account_type} />
                      </td>
                      <td className="cell-numeric text-debit">{fmtAmt(line.debit_total)}</td>
                      <td className="cell-numeric text-credit">{fmtAmt(line.credit_total)}</td>
                      <td
                        className={`cell-numeric ${parseAmount(line.debit_balance) > 0 ? 'font-medium text-foreground' : 'text-subtle-foreground'}`}
                      >
                        {fmtAmt(line.debit_balance)}
                      </td>
                      <td
                        className={`cell-numeric ${parseAmount(line.credit_balance) > 0 ? 'font-medium text-foreground' : 'text-subtle-foreground'}`}
                      >
                        {fmtAmt(line.credit_balance)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={3}>{t.reports.trialBalance.totals}</td>
                    <td className="cell-numeric text-success">
                      {formatCurrency(parseAmount(data.total_debit))}
                    </td>
                    <td className="cell-numeric text-danger">
                      {formatCurrency(parseAmount(data.total_credit))}
                    </td>
                    <td className="cell-numeric">
                      {formatCurrency(parseAmount(data.total_debit_balance))}
                    </td>
                    <td className="cell-numeric">
                      {formatCurrency(parseAmount(data.total_credit_balance))}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* Mobile cards */}
          <div className="space-y-3 md:hidden">
            {filteredLines.map((line) => (
              <div key={line.account_id} className="card p-4">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <span className="numeric text-xs font-semibold text-primary">
                      {line.account_code}
                    </span>
                    <h3 className="mt-0.5 text-sm font-medium text-foreground">
                      {line.account_name}
                    </h3>
                  </div>
                  <AccountTypeBadge type={line.account_type} />
                </div>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5 border-t border-border-subtle pt-3">
                  <MobileFigure label={t.common.debitTotal} value={fmtAmt(line.debit_total)} className="text-debit" />
                  <MobileFigure label={t.common.creditTotal} value={fmtAmt(line.credit_total)} className="text-credit" />
                  <MobileFigure
                    label={t.reports.trialBalance.debitBalance}
                    value={fmtAmt(line.debit_balance)}
                    className={parseAmount(line.debit_balance) > 0 ? 'text-foreground' : 'text-subtle-foreground'}
                  />
                  <MobileFigure
                    label={t.reports.trialBalance.creditBalance}
                    value={fmtAmt(line.credit_balance)}
                    className={parseAmount(line.credit_balance) > 0 ? 'text-foreground' : 'text-subtle-foreground'}
                  />
                </dl>
              </div>
            ))}

            <div className="card border-primary-border bg-surface-muted p-4">
              <p className="section-title mb-3">{t.reports.trialBalance.totals}</p>
              <dl className="grid grid-cols-2 gap-4">
                <MobileFigure
                  label={t.reports.trialBalance.debit}
                  value={formatCurrency(parseAmount(data.total_debit))}
                  className="text-success"
                />
                <MobileFigure
                  label={t.reports.trialBalance.credit}
                  value={formatCurrency(parseAmount(data.total_credit))}
                  className="text-danger"
                />
              </dl>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}

function MobileFigure({
  label,
  value,
  className = '',
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div>
      <dt className="overline">{label}</dt>
      <dd className={`numeric mt-0.5 text-sm font-semibold ${className}`}>{value}</dd>
    </div>
  );
}

function TopAccountsChart({ lines, t }: { lines: TrialBalanceLine[]; t: Translations }) {
  const chartData = useMemo(() => {
    return [...lines]
      .map((l) => ({
        name: `${l.account_code} ${l.account_name}`.slice(0, 28),
        debit: parseAmount(l.debit_balance),
        credit: parseAmount(l.credit_balance),
      }))
      .filter((a) => a.debit !== 0 || a.credit !== 0)
      .sort((a, b) => Math.max(b.debit, b.credit) - Math.max(a.debit, a.credit))
      .slice(0, 10);
  }, [lines]);

  if (chartData.length === 0) return null;

  return (
    <ChartCard
      title={t.charts.topAccountBalances}
      delay={0.05}
      height={Math.max(200, chartData.length * 36)}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 20, left: 8, bottom: 4 }} barSize={14}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" horizontal={false} />
          <XAxis type="number" tick={{ fill: 'var(--muted-foreground)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
          <YAxis dataKey="name" type="category" tick={{ fill: 'var(--muted-foreground)', fontSize: 10 }} axisLine={false} tickLine={false} width={150} />
          <Tooltip
            cursor={{ fill: 'var(--surface-muted)' }}
            contentStyle={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
            itemStyle={{ color: 'var(--foreground)' }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any) => Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          />
          <Bar dataKey="debit" name={t.charts.debit} fill="var(--debit)" radius={[0, 4, 4, 0]} />
          <Bar dataKey="credit" name={t.charts.credit} fill="var(--chart-1)" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
