import { useState, useEffect, useMemo, useId } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Library,
  Search,
  ChevronDown,
  ChevronRight,
  Hash,
  ArrowDownRight,
  ArrowUpRight,
  ListTree,
} from 'lucide-react';
import PageLayout from '../../../components/layout/PageLayout';
import LoadingState from '../../../components/feedback/LoadingState';
import ErrorState from '../../../components/feedback/ErrorState';
import EmptyState from '../../../components/feedback/EmptyState';
import { AccountTypeBadge } from '../../../entities/account';
import ReportHeader from '../components/ReportHeader';
import ReportSummaryTile from '../components/ReportSummaryTile';
import ReportExportButtons from '../components/ReportExportButtons';
import ReportDateField from '../components/ReportDateField';
import ReportSearchField from '../components/ReportSearchField';
import { useGeneralLedger } from './useGeneralLedger';
import { useI18n } from '../../../i18n';
import { formatCurrency, formatSignedCurrency } from '../../../lib/format';
import type { AccountLedgerRead, AccountLedgerLine } from '../../../api/types';

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

/** Zero movements render as an em dash so real postings stand out when scanning. */
function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(Math.abs(n));
}

const ACCOUNT_TYPES = ['all', 'asset', 'liability', 'equity', 'income', 'expense'] as const;

export default function GeneralLedgerPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.reports.generalLedger.pageTitle}
      pageSubtitle={t.reports.generalLedger.pageSubtitle}
      activePath="/reports/general-ledger"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <GeneralLedgerContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface GeneralLedgerContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function GeneralLedgerContent({ selectedCompanyId, companiesLoading }: GeneralLedgerContentProps) {
  const { t } = useI18n();
  const typeFilterId = useId();
  const [startDate, setStartDate] = useState<string | null>(null);
  const [endDate, setEndDate] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [expandedAccounts, setExpandedAccounts] = useState<Set<number>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  const {
    data,
    isLoading: reportLoading,
    error,
    fetchReport,
  } = useGeneralLedger({ companyId: selectedCompanyId, startDate, endDate });

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    setSearchQuery('');
    setTypeFilter('all');
    setExpandedAccounts(new Set());
  }, [selectedCompanyId]);

  const toggleAccount = (accountId: number) => {
    setExpandedAccounts((prev) => {
      const next = new Set(prev);
      if (next.has(accountId)) next.delete(accountId);
      else next.add(accountId);
      return next;
    });
  };

  // ── Filtering ──
  const filteredAccounts = useMemo(() => {
    if (!data) return [];
    let accounts = data.accounts;

    if (typeFilter !== 'all') {
      accounts = accounts.filter((a) => a.account_type === typeFilter);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      accounts = accounts.filter((a) => {
        const accountMatch =
          a.account_code.toLowerCase().includes(q) ||
          a.account_name.toLowerCase().includes(q) ||
          a.account_type.toLowerCase().includes(q);
        const lineMatch = a.lines.some(
          (l) =>
            l.entry_no.toLowerCase().includes(q) ||
            (l.description && l.description.toLowerCase().includes(q)),
        );
        return accountMatch || lineMatch;
      });
    }

    return accounts;
  }, [data, typeFilter, searchQuery]);

  // ── Aggregates ──
  const totalAccounts = data?.accounts.length ?? 0;
  const accountsWithActivity = data?.accounts.filter((a) => a.lines.length > 0).length ?? 0;
  const totalLines = data?.accounts.reduce((s, a) => s + a.lines.length, 0) ?? 0;
  const aggregateOpening = data?.accounts.reduce((s, a) => s + parseAmount(a.opening_balance), 0) ?? 0;
  const aggregateClosing = data?.accounts.reduce((s, a) => s + parseAmount(a.closing_balance), 0) ?? 0;

  const isLoading = companiesLoading || reportLoading;

  const expandAll = () => {
    setExpandedAccounts(new Set(filteredAccounts.map((a) => a.account_id)));
  };

  const collapseAll = () => {
    setExpandedAccounts(new Set());
  };

  const handleExportCsv = async () => {
    if (!selectedCompanyId) return;
    setExporting(true);
    try {
      const { downloadFile } = await import('../../../lib/downloadFile');
      await downloadFile('/reports/general-ledger/export.csv', {
        company_id: selectedCompanyId,
        start_date: startDate,
        end_date: endDate,
      }, 'general-ledger.csv');
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
      await downloadFile('/reports/general-ledger/export.pdf', {
        company_id: selectedCompanyId,
        start_date: startDate,
        end_date: endDate,
      }, 'general-ledger.pdf');
    } catch {
      alert(t.common.pdfExportFailed);
    } finally {
      setExportingPdf(false);
    }
  };

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={fetchReport} />;
  if (!data) return null;

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
        icon={Library}
        title={t.reports.generalLedger.pageTitle}
        periodLabel={periodLabel}
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
          label={t.reports.generalLedger.accounts}
          value={String(totalAccounts)}
          tone="teal"
          icon={Hash}
          hint={`${accountsWithActivity} ${t.common.withActivity}`}
        />
        <ReportSummaryTile
          label={`Σ ${t.common.opening}`}
          value={formatSignedCurrency(aggregateOpening)}
          tone={aggregateOpening < 0 ? 'danger' : 'neutral'}
          icon={ArrowDownRight}
        />
        <ReportSummaryTile
          label={`Σ ${t.common.closing}`}
          value={formatSignedCurrency(aggregateClosing)}
          tone={aggregateClosing < 0 ? 'danger' : 'neutral'}
          icon={ArrowUpRight}
        />
        <ReportSummaryTile
          label={t.reports.generalLedger.totalLines}
          value={String(totalLines)}
          icon={ListTree}
        />
      </ReportHeader>

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

        <div className="min-w-[10rem]">
          <label htmlFor={typeFilterId} className="field-label">
            {t.common.type}
          </label>
          <select
            id={typeFilterId}
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="select"
          >
            {ACCOUNT_TYPES.map((acctType) => (
              <option key={acctType} value={acctType}>
                {acctType === 'all'
                  ? t.reports.generalLedger.allTypes
                  : acctType.charAt(0).toUpperCase() + acctType.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <ReportSearchField
          label={t.common.search}
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder={t.reports.generalLedger.searchPlaceholder}
        />

        <div className="flex items-center gap-2 pb-0.5">
          <button type="button" onClick={expandAll} className="btn btn-secondary btn-sm">
            {t.common.expandAll}
          </button>
          <button type="button" onClick={collapseAll} className="btn btn-ghost btn-sm">
            {t.common.collapseAll}
          </button>
        </div>

        <p className="numeric pb-2.5 text-xs text-subtle-foreground">
          {filteredAccounts.length} {t.common.of} {totalAccounts}{' '}
          {t.reports.shared.accountsShown}
        </p>
      </motion.div>

      {totalAccounts === 0 && (
        <EmptyState
          icon={<Library className="h-7 w-7 text-primary" />}
          title={t.reports.generalLedger.noDataTitle}
          description={t.reports.generalLedger.noDataDescription}
        />
      )}

      {totalAccounts > 0 && filteredAccounts.length === 0 && (
        <EmptyState
          icon={<Search className="h-7 w-7 text-primary" />}
          title={t.reports.shared.noMatchTitle}
          description={t.reports.generalLedger.noMatchFilters}
          action={
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setTypeFilter('all');
              }}
              className="btn btn-secondary btn-sm"
            >
              {t.common.clearFilters}
            </button>
          }
        />
      )}

      {filteredAccounts.length > 0 && (
        <div className="space-y-3">
          {filteredAccounts.map((account, i) => (
            <AccountCard
              key={account.account_id}
              account={account}
              isExpanded={expandedAccounts.has(account.account_id)}
              onToggle={() => toggleAccount(account.account_id)}
              index={i}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface AccountCardProps {
  account: AccountLedgerRead;
  isExpanded: boolean;
  onToggle: () => void;
  index: number;
}

function AccountCard({ account, isExpanded, onToggle, index }: AccountCardProps) {
  const { t } = useI18n();
  const panelId = useId();
  const closing = parseAmount(account.closing_balance);
  const hasActivity = account.lines.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: Math.min(index * 0.03, 0.4) }}
      className="card overflow-hidden"
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-controls={panelId}
        className="flex w-full items-center gap-4 px-4 py-3.5 text-start transition-colors hover:bg-surface-muted lg:px-5"
      >
        <span aria-hidden className="flex-shrink-0 text-subtle-foreground">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4 rtl:rotate-180" />
          )}
        </span>

        <span className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          <span className="numeric text-xs font-semibold text-primary">{account.account_code}</span>
          <span className="truncate text-sm font-medium text-foreground">{account.account_name}</span>
          <AccountTypeBadge type={account.account_type} />
          {!hasActivity && (
            <span className="badge tone-neutral">{t.common.noActivity}</span>
          )}
        </span>

        <span className="hidden flex-shrink-0 items-center gap-6 sm:flex">
          <HeaderFigure
            label={t.reports.generalLedger.opening}
            value={formatSignedCurrency(parseAmount(account.opening_balance))}
          />
          <HeaderFigure
            label={t.reports.generalLedger.closing}
            value={formatSignedCurrency(closing)}
            emphasis
            className={closing < 0 ? 'text-danger' : 'text-foreground'}
          />
          <HeaderFigure
            label={t.reports.generalLedger.lines}
            value={String(account.lines.length)}
          />
        </span>

        <span className="flex flex-shrink-0 flex-col items-end sm:hidden">
          <span
            className={`numeric text-xs font-semibold ${closing < 0 ? 'text-danger' : 'text-foreground'}`}
          >
            {formatSignedCurrency(closing)}
          </span>
          <span className="text-[10px] text-subtle-foreground">
            {account.lines.length} {t.reports.generalLedger.lines.toLowerCase()}
          </span>
        </span>
      </button>

      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            id={panelId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border">
              {account.lines.length === 0 ? (
                <p className="px-6 py-8 text-center text-sm text-subtle-foreground">
                  {t.common.noActivity}
                </p>
              ) : (
                <>
                  {/* Desktop table */}
                  <div className="table-wrap hidden md:block">
                    <table className="data-table">
                      <caption className="sr-only">
                        {account.account_code} {account.account_name}
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">{t.reports.generalLedger.date}</th>
                          <th scope="col">{t.reports.generalLedger.entryNo}</th>
                          <th scope="col" className="cell-numeric">{t.reports.generalLedger.ln}</th>
                          <th scope="col">{t.reports.generalLedger.description}</th>
                          <th scope="col" className="cell-numeric">{t.reports.generalLedger.debit}</th>
                          <th scope="col" className="cell-numeric">{t.reports.generalLedger.credit}</th>
                          <th scope="col" className="cell-numeric">{t.reports.generalLedger.balance}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="row-total">
                          <td colSpan={6}>{t.common.openingBalance}</td>
                          <td className="cell-numeric">
                            {formatSignedCurrency(parseAmount(account.opening_balance))}
                          </td>
                        </tr>
                        {account.lines.map((line) => (
                          <LedgerRow key={`${line.journal_entry_id}-${line.line_no}`} line={line} />
                        ))}
                      </tbody>
                      <tfoot>
                        <tr>
                          <td colSpan={4}>{t.common.closingBalance}</td>
                          <td className="cell-numeric text-success">
                            {formatCurrency(account.lines.reduce((s, l) => s + parseAmount(l.debit), 0))}
                          </td>
                          <td className="cell-numeric text-danger">
                            {formatCurrency(account.lines.reduce((s, l) => s + parseAmount(l.credit), 0))}
                          </td>
                          <td className={`cell-numeric ${closing < 0 ? 'text-danger' : 'text-foreground'}`}>
                            {formatSignedCurrency(closing)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  {/* Mobile cards */}
                  <div className="space-y-2 p-3 md:hidden">
                    <div className="flex items-center justify-between px-1">
                      <span className="overline">{t.common.opening}</span>
                      <span className="numeric text-xs text-muted-foreground">
                        {formatSignedCurrency(parseAmount(account.opening_balance))}
                      </span>
                    </div>
                    {account.lines.map((line) => (
                      <MobileLedgerCard key={`${line.journal_entry_id}-${line.line_no}`} line={line} />
                    ))}
                    <div className="flex items-center justify-between border-t border-border px-1 pt-2">
                      <span className="text-xs font-semibold text-foreground">{t.common.closing}</span>
                      <span
                        className={`numeric text-xs font-semibold ${closing < 0 ? 'text-danger' : 'text-foreground'}`}
                      >
                        {formatSignedCurrency(closing)}
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function HeaderFigure({
  label,
  value,
  emphasis,
  className = 'text-muted-foreground',
}: {
  label: string;
  value: string;
  emphasis?: boolean;
  className?: string;
}) {
  return (
    <span className="block text-end">
      <span className="overline block">{label}</span>
      <span className={`numeric block text-xs ${emphasis ? 'font-semibold' : ''} ${className}`}>
        {value}
      </span>
    </span>
  );
}

function LedgerRow({ line }: { line: AccountLedgerLine }) {
  const bal = parseAmount(line.running_balance);
  return (
    <tr>
      <td className="whitespace-nowrap text-xs text-muted-foreground">
        {new Date(line.entry_date).toLocaleDateString()}
      </td>
      <td className="numeric text-xs text-primary">{line.entry_no}</td>
      <td className="cell-numeric text-xs text-subtle-foreground">{line.line_no}</td>
      <td className="max-w-[240px] truncate text-xs text-muted-foreground">
        {line.description || '—'}
      </td>
      <td className="cell-numeric text-xs text-debit">{fmtAmt(line.debit)}</td>
      <td className="cell-numeric text-xs text-credit">{fmtAmt(line.credit)}</td>
      <td
        className={`cell-numeric text-xs font-semibold ${bal < 0 ? 'text-danger' : 'text-foreground'}`}
      >
        {formatSignedCurrency(bal)}
      </td>
    </tr>
  );
}

function MobileLedgerCard({ line }: { line: AccountLedgerLine }) {
  const { t } = useI18n();
  const bal = parseAmount(line.running_balance);
  return (
    <div className="rounded-lg border border-border-subtle bg-surface-muted p-3">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="numeric text-[11px] text-primary">{line.entry_no}</span>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {line.description || t.common.noDescription}
          </p>
        </div>
        <span className="whitespace-nowrap text-[10px] text-subtle-foreground">
          {new Date(line.entry_date).toLocaleDateString()}
        </span>
      </div>
      <dl className="grid grid-cols-3 gap-2 border-t border-border-subtle pt-2">
        <div>
          <dt className="overline">{t.reports.generalLedger.debit}</dt>
          <dd className="numeric text-[11px] text-debit">{fmtAmt(line.debit)}</dd>
        </div>
        <div>
          <dt className="overline">{t.reports.generalLedger.credit}</dt>
          <dd className="numeric text-[11px] text-credit">{fmtAmt(line.credit)}</dd>
        </div>
        <div className="text-end">
          <dt className="overline">{t.reports.generalLedger.balance}</dt>
          <dd
            className={`numeric text-[11px] font-semibold ${bal < 0 ? 'text-danger' : 'text-foreground'}`}
          >
            {formatSignedCurrency(bal)}
          </dd>
        </div>
      </dl>
    </div>
  );
}
