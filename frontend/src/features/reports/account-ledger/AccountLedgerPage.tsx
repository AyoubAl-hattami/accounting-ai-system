import { useState, useEffect, useMemo, useId } from 'react';
import { motion } from 'framer-motion';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import {
  BookMarked,
  Search,
  ArrowDownRight,
  ArrowUpRight,
  Scale,
  Wallet,
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
import { useAccountLedger } from './useAccountLedger';
import { useI18n } from '../../../i18n';
import { formatCurrency, formatSignedCurrency } from '../../../lib/format';
import apiClient from '../../../api/client';
import type {
  Account,
  AccountLedgerLine,
  PaginatedResponse,
} from '../../../api/types';
import type { Translations } from '../../../i18n/types';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

/** Zero movements render as an em dash so real postings stand out when scanning. */
function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(Math.abs(n));
}

const STORAGE_KEY = 'accounting-ai-selected-account';

export default function AccountLedgerPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.reports.accountLedger.pageTitle}
      pageSubtitle={t.reports.accountLedger.pageSubtitle}
      activePath="/reports/account-ledger"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <AccountLedgerContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface AccountLedgerContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function AccountLedgerContent({ selectedCompanyId, companiesLoading }: AccountLedgerContentProps) {
  const { t } = useI18n();
  const accountSelectId = useId();

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? parseInt(saved, 10) : null;
  });

  const [startDate, setStartDate] = useState<string | null>(null);
  const [endDate, setEndDate] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  useEffect(() => {
    if (!selectedCompanyId) return;
    let cancelled = false;
    setAccountsLoading(true);

    apiClient
      .get<PaginatedResponse<Account>>(
        `/accounts?company_id=${selectedCompanyId}&skip=0&limit=500`,
      )
      .then((res) => {
        if (cancelled) return;
        const items = res.data.items;
        setAccounts(items);
        // Auto-select first if current selection is invalid
        const ids = items.map((a) => a.id);
        setSelectedAccountId((prev) => {
          if (prev && ids.includes(prev)) return prev;
          const first = items[0]?.id || null;
          if (first) localStorage.setItem(STORAGE_KEY, String(first));
          else localStorage.removeItem(STORAGE_KEY);
          return first;
        });
      })
      .catch(() => {
        if (!cancelled) setAccounts([]);
      })
      .finally(() => {
        if (!cancelled) setAccountsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedCompanyId]);

  useEffect(() => {
    setSearchQuery('');
    setStartDate(null);
    setEndDate(null);
  }, [selectedCompanyId]);

  const {
    data,
    isLoading: ledgerLoading,
    error,
    fetchReport,
  } = useAccountLedger({
    companyId: selectedCompanyId,
    accountId: selectedAccountId,
    startDate,
    endDate,
  });

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleSelectAccount = (id: number) => {
    setSelectedAccountId(id);
    localStorage.setItem(STORAGE_KEY, String(id));
    setSearchQuery('');
  };

  const totalDebits = useMemo(
    () => (data ? data.lines.reduce((s, l) => s + parseAmount(l.debit), 0) : 0),
    [data],
  );

  const totalCredits = useMemo(
    () => (data ? data.lines.reduce((s, l) => s + parseAmount(l.credit), 0) : 0),
    [data],
  );

  const filteredLines = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.lines;
    const q = searchQuery.toLowerCase();
    return data.lines.filter(
      (l) =>
        l.entry_no.toLowerCase().includes(q) ||
        (l.description && l.description.toLowerCase().includes(q)) ||
        l.entry_date.includes(q),
    );
  }, [data, searchQuery]);

  const handleExportCsv = async () => {
    if (!selectedCompanyId || !selectedAccountId) return;
    setExporting(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/account-ledger/export.csv', {
        company_id: selectedCompanyId,
        account_id: selectedAccountId,
        start_date: startDate,
        end_date: endDate,
      }, 'account-ledger.csv');
    } catch {
      alert(t.common.exportFailed);
    } finally {
      setExporting(false);
    }
  };

  const handleExportPdf = async () => {
    if (!selectedCompanyId || !selectedAccountId) return;
    setExportingPdf(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/account-ledger/export.pdf', {
        company_id: selectedCompanyId,
        account_id: selectedAccountId,
        start_date: startDate,
        end_date: endDate,
      }, 'account-ledger.pdf');
    } catch {
      alert(t.common.pdfExportFailed);
    } finally {
      setExportingPdf(false);
    }
  };

  const isLoading = companiesLoading || accountsLoading || ledgerLoading;
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={fetchReport} />;

  const closing = data ? parseAmount(data.closing_balance) : 0;

  const periodLabel = !data
    ? ''
    : data.start_date && data.end_date
      ? `${new Date(data.start_date).toLocaleDateString()} — ${new Date(data.end_date).toLocaleDateString()}`
      : data.start_date
        ? `${t.common.from} ${new Date(data.start_date).toLocaleDateString()}`
        : data.end_date
          ? `${t.common.through} ${new Date(data.end_date).toLocaleDateString()}`
          : t.common.allTime;

  /* The account picker drives which ledger is loaded, so it stays visible even
     when nothing is selected yet. */
  const toolbar = (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.05 }}
      className="filter-bar"
    >
      <div className="min-w-[16rem] flex-1">
        <label htmlFor={accountSelectId} className="field-label">
          {t.common.account}
        </label>
        <select
          id={accountSelectId}
          value={selectedAccountId ?? ''}
          onChange={(e) => handleSelectAccount(Number(e.target.value))}
          disabled={accounts.length === 0}
          className="select"
        >
          {selectedAccountId === null && <option value="">{t.common.selectAccountPrompt}</option>}
          {accounts.map((acc) => (
            <option key={acc.id} value={acc.id}>
              {acc.code} — {acc.name}
            </option>
          ))}
        </select>
      </div>

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
        placeholder={t.common.searchByEntryPlaceholder}
      />

      {data && (
        <p className="numeric pb-2.5 text-xs text-subtle-foreground">
          {filteredLines.length} {t.common.of} {data.lines.length} {t.reports.shared.linesShown}
        </p>
      )}
    </motion.div>
  );

  if (!selectedAccountId || !data) {
    return (
      <div className="space-y-5">
        {toolbar}
        <EmptyState
          icon={<BookMarked className="h-7 w-7 text-primary" />}
          title={t.common.selectAccount}
          description={t.common.selectAccountPrompt}
        />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <ReportHeader
        icon={BookMarked}
        title={`${data.account_code} · ${data.account_name}`}
        periodLabel={periodLabel}
        actions={
          <>
            <AccountTypeBadge type={data.account_type} />
            <ReportExportButtons
              onExportCsv={handleExportCsv}
              onExportPdf={handleExportPdf}
              exportingCsv={exporting}
              exportingPdf={exportingPdf}
            />
          </>
        }
      >
        <ReportSummaryTile
          label={t.reports.accountLedger.openingBalance}
          value={formatSignedCurrency(parseAmount(data.opening_balance))}
          icon={Wallet}
        />
        <ReportSummaryTile
          label={t.reports.accountLedger.totalDebits}
          value={formatCurrency(totalDebits)}
          tone="success"
          icon={ArrowDownRight}
        />
        <ReportSummaryTile
          label={t.reports.accountLedger.totalCredits}
          value={formatCurrency(totalCredits)}
          tone="danger"
          icon={ArrowUpRight}
        />
        <ReportSummaryTile
          label={t.reports.accountLedger.closingBalance}
          value={formatSignedCurrency(closing)}
          tone={closing < 0 ? 'danger' : 'primary'}
          icon={Scale}
          hint={`${data.lines.length} ${t.reports.accountLedger.entries.toLowerCase()}`}
          emphasis
        />
      </ReportHeader>

      {toolbar}

      {data.lines.length > 1 && <RunningBalanceChart lines={data.lines} t={t} />}

      {data.lines.length === 0 && (
        <EmptyState
          icon={<BookMarked className="h-7 w-7 text-primary" />}
          title={t.reports.shared.noDataTitle}
          description={t.reports.shared.noDataDescription}
        />
      )}

      {data.lines.length > 0 && filteredLines.length === 0 && (
        <EmptyState
          icon={<Search className="h-7 w-7 text-primary" />}
          title={t.reports.shared.noEntryMatchTitle}
          description={t.reports.shared.noEntryMatchDescription}
          action={
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="btn btn-secondary btn-sm"
            >
              {t.common.clearSearch}
            </button>
          }
        />
      )}

      {filteredLines.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="card overflow-hidden"
        >
          {/* Desktop table */}
          <div className="table-wrap hidden lg:block">
            <table className="data-table">
              <caption className="sr-only">
                {data.account_code} {data.account_name} — {periodLabel}
              </caption>
              <thead>
                <tr>
                  <th scope="col">{t.reports.accountLedger.date}</th>
                  <th scope="col">{t.reports.accountLedger.entryNo}</th>
                  <th scope="col" className="cell-numeric">
                    {t.reports.accountLedger.line}
                  </th>
                  <th scope="col">{t.reports.accountLedger.description}</th>
                  <th scope="col" className="cell-numeric">
                    {t.reports.accountLedger.debit}
                  </th>
                  <th scope="col" className="cell-numeric">
                    {t.reports.accountLedger.credit}
                  </th>
                  <th scope="col" className="cell-numeric">
                    {t.reports.accountLedger.balance}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className="row-total">
                  <td colSpan={6}>{t.reports.accountLedger.openingBalance}</td>
                  <td className="cell-numeric">
                    {formatSignedCurrency(parseAmount(data.opening_balance))}
                  </td>
                </tr>
                {filteredLines.map((line) => (
                  <LedgerRow key={`${line.journal_entry_id}-${line.line_no}`} line={line} />
                ))}
              </tbody>
              <tfoot>
                <tr className="row-grand">
                  <td colSpan={4}>{t.reports.accountLedger.closingBalance}</td>
                  <td className="cell-numeric text-debit">{formatCurrency(totalDebits)}</td>
                  <td className="cell-numeric text-credit">{formatCurrency(totalCredits)}</td>
                  <td className={`cell-numeric ${closing < 0 ? 'text-danger' : 'text-foreground'}`}>
                    {formatSignedCurrency(closing)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="lg:hidden">
            <div className="flex items-center justify-between border-b border-border bg-surface-muted px-4 py-3">
              <span className="overline">{t.reports.accountLedger.openingBalance}</span>
              <span className="numeric text-sm text-muted-foreground">
                {formatSignedCurrency(parseAmount(data.opening_balance))}
              </span>
            </div>

            <div className="divide-y divide-border-subtle">
              {filteredLines.map((line) => (
                <MobileLedgerCard key={`${line.journal_entry_id}-${line.line_no}`} line={line} />
              ))}
            </div>

            <div className="border-t-2 border-border-strong bg-surface-sunken px-4 py-4">
              <div className="mb-1.5 flex items-center justify-between gap-3">
                <span className="text-sm font-bold text-foreground">
                  {t.reports.accountLedger.closingBalance}
                </span>
                <span
                  className={`numeric text-base font-bold ${closing < 0 ? 'text-danger' : 'text-foreground'}`}
                >
                  {formatSignedCurrency(closing)}
                </span>
              </div>
              <div className="flex items-center gap-4 text-[11px] text-subtle-foreground">
                <span>
                  {t.reports.accountLedger.debit}:{' '}
                  <span className="numeric text-debit">{formatCurrency(totalDebits)}</span>
                </span>
                <span>
                  {t.reports.accountLedger.credit}:{' '}
                  <span className="numeric text-credit">{formatCurrency(totalCredits)}</span>
                </span>
              </div>
            </div>
          </div>
        </motion.section>
      )}
    </div>
  );
}

function LedgerRow({ line }: { line: AccountLedgerLine }) {
  const bal = parseAmount(line.running_balance);
  return (
    <tr>
      <td className="whitespace-nowrap text-muted-foreground">
        {new Date(line.entry_date).toLocaleDateString()}
      </td>
      <td className="numeric text-sm font-semibold text-primary">{line.entry_no}</td>
      <td className="cell-numeric text-xs text-subtle-foreground">{line.line_no}</td>
      <td className="max-w-[260px] truncate">{line.description || '—'}</td>
      <td className="cell-numeric text-debit">{fmtAmt(line.debit)}</td>
      <td className="cell-numeric text-credit">{fmtAmt(line.credit)}</td>
      <td className={`cell-numeric font-semibold ${bal < 0 ? 'text-danger' : 'text-foreground'}`}>
        {formatSignedCurrency(bal)}
      </td>
    </tr>
  );
}

function MobileLedgerCard({ line }: { line: AccountLedgerLine }) {
  const { t } = useI18n();
  const bal = parseAmount(line.running_balance);
  return (
    <div className="px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="numeric text-xs font-semibold text-primary">{line.entry_no}</span>
          <p className="mt-0.5 text-sm text-foreground">
            {line.description || t.common.noDescription}
          </p>
        </div>
        <span className="whitespace-nowrap text-xs text-subtle-foreground">
          {new Date(line.entry_date).toLocaleDateString()}
        </span>
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-2 border-t border-border-subtle pt-2">
        <div>
          <dt className="overline">{t.reports.accountLedger.debit}</dt>
          <dd className="numeric mt-0.5 text-xs text-debit">{fmtAmt(line.debit)}</dd>
        </div>
        <div>
          <dt className="overline">{t.reports.accountLedger.credit}</dt>
          <dd className="numeric mt-0.5 text-xs text-credit">{fmtAmt(line.credit)}</dd>
        </div>
        <div className="text-end">
          <dt className="overline">{t.reports.accountLedger.balance}</dt>
          <dd
            className={`numeric mt-0.5 text-xs font-semibold ${bal < 0 ? 'text-danger' : 'text-foreground'}`}
          >
            {formatSignedCurrency(bal)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

function RunningBalanceChart({ lines, t }: { lines: AccountLedgerLine[]; t: Translations }) {
  const chartData = useMemo(() => {
    // Aggregate by date: keep the last running balance per date
    const byDate = new Map<string, number>();
    for (const l of lines) {
      byDate.set(l.entry_date, parseFloat(l.running_balance) || 0);
    }
    return Array.from(byDate.entries()).map(([date, balance]) => ({ date, balance }));
  }, [lines]);

  // Evenly-spaced ticks so long ranges do not crowd the axis
  const ticks = useMemo(() => {
    if (chartData.length <= 8) return chartData.map((d) => d.date);
    const step = Math.ceil(chartData.length / 7);
    const result: string[] = [];
    for (let i = 0; i < chartData.length; i += step) {
      result.push(chartData[i].date);
    }
    const last = chartData[chartData.length - 1].date;
    if (result[result.length - 1] !== last) result.push(last);
    return result;
  }, [chartData]);

  if (chartData.length < 2) return null;

  return (
    <ChartCard title={t.charts.runningBalance} delay={0.08} height={200}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
          <defs>
            <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.3} />
              <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis
            dataKey="date"
            tick={{ fill: 'var(--muted-foreground)', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            ticks={ticks}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: 'var(--muted-foreground)', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--surface-raised)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              fontSize: 12,
            }}
            itemStyle={{ color: 'var(--chart-1)' }}
            labelStyle={{ color: 'var(--muted-foreground)' }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any) => [
              Number(value).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              }),
              t.charts.balance,
            ]}
          />
          <Area
            type="monotone"
            dataKey="balance"
            stroke="var(--chart-1)"
            strokeWidth={2}
            fill="url(#balanceGrad)"
            dot={chartData.length <= 20}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
