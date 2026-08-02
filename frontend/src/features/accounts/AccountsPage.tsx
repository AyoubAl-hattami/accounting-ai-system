import { useState, useEffect, useMemo, useId } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Receipt, Search, Sprout, Loader2, CheckCircle2, AlertCircle, X } from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import { AccountTypeBadge, useAccounts } from '../../entities/account';
import PaginationControls from '../../components/ui/PaginationControls';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import EmptyState from '../../components/feedback/EmptyState';
import { useI18n } from '../../i18n';
import { canManageAccounts } from '../../auth/permissions';
import type { Account, CompanyUserRole } from '../../api/types';

const ACCOUNT_FETCH_LIMIT = 500;
const ACCOUNT_TYPES = ['asset', 'liability', 'equity', 'income', 'expense'];
const PAGE_SIZE = 10;

export default function AccountsPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.accountsPage.pageTitle}
      pageSubtitle={t.accountsPage.pageSubtitle}
      activePath="/accounts"
    >
      {({ selectedCompanyId, companiesLoading, userRole }) => (
        <AccountsContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
          userRole={userRole}
        />
      )}
    </PageLayout>
  );
}

interface AccountsContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
  userRole: CompanyUserRole | null;
}

function AccountsContent({ selectedCompanyId, companiesLoading, userRole }: AccountsContentProps) {
  const { t } = useI18n();
  const searchId = useId();
  const typeId = useId();

  const [skip, setSkip] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const {
    accounts,
    total,
    isLoading: accountsLoading,
    error,
    fetchAccounts,
    seedDefaults,
  } = useAccounts({
    companyId: selectedCompanyId,
    skip: 0,
    limit: ACCOUNT_FETCH_LIMIT, // backend enforces max 500
  });

  const [isSeeding, setIsSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<{ created: number; skipped: number } | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);

  useEffect(() => {
    setSkip(0);
    setSearchQuery('');
    setTypeFilter('');
    setSeedResult(null);
    setSeedError(null);
  }, [selectedCompanyId]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const filteredAccounts = useMemo(() => {
    let result = accounts;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (a) =>
          a.code.toLowerCase().includes(q) ||
          a.name.toLowerCase().includes(q) ||
          (a.description && a.description.toLowerCase().includes(q)),
      );
    }

    if (typeFilter) {
      result = result.filter((a) => a.account_type === typeFilter);
    }

    return result;
  }, [accounts, searchQuery, typeFilter]);

  const filteredTotal = filteredAccounts.length;
  const paginatedAccounts = filteredAccounts.slice(skip, skip + PAGE_SIZE);

  useEffect(() => {
    setSkip(0);
  }, [searchQuery, typeFilter]);

  /** Parent codes are shown instead of raw ids, which are meaningless to the reader. */
  const parentCodeOf = (acc: Account): string =>
    acc.parent_id ? accounts.find((a) => a.id === acc.parent_id)?.code || `#${acc.parent_id}` : '—';

  const handleSeed = async () => {
    setIsSeeding(true);
    setSeedResult(null);
    setSeedError(null);

    try {
      const result = await seedDefaults();
      if (result) {
        setSeedResult({ created: result.created_count, skipped: result.skipped_count });
        await fetchAccounts();
      }
    } catch {
      setSeedError(t.accountsPage.seedFailed);
    } finally {
      setIsSeeding(false);
    }
  };

  const clearFilters = () => {
    setSearchQuery('');
    setTypeFilter('');
  };

  const isLoading = companiesLoading || accountsLoading;
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={fetchAccounts} />;

  const canManage = canManageAccounts(userRole);

  return (
    <div className="space-y-5">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
      >
        <div>
          <h2 className="page-title">{t.accountsPage.pageTitle}</h2>
          <p className="page-description">{t.accountsPage.pageSubtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="numeric text-xs text-subtle-foreground">
            {total} {t.accountsPage.showingAccounts}
          </span>
          {canManage && (
            <button
              type="button"
              onClick={handleSeed}
              disabled={isSeeding}
              className="btn btn-secondary btn-sm"
            >
              {isSeeding ? (
                <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sprout aria-hidden className="h-3.5 w-3.5" />
              )}
              {isSeeding ? t.accountsPage.seeding : t.accountsPage.seedDefaults}
            </button>
          )}
        </div>
      </motion.div>

      <AnimatePresence>
        {seedResult && (
          <motion.div
            key="seed-ok"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            role="status"
            className="callout tone-success"
          >
            <CheckCircle2 aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p className="flex-1">
              <span className="numeric font-semibold">{seedResult.created}</span>{' '}
              {t.accountsPage.created},{' '}
              <span className="numeric font-semibold">{seedResult.skipped}</span>{' '}
              {t.accountsPage.skipped}.
            </p>
            <button
              type="button"
              onClick={() => setSeedResult(null)}
              aria-label={t.common.close}
              className="flex-shrink-0 opacity-70 transition-opacity hover:opacity-100"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          </motion.div>
        )}

        {seedError && (
          <motion.div
            key="seed-error"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            role="alert"
            className="callout tone-danger"
          >
            <AlertCircle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p className="flex-1">{seedError}</p>
            <button
              type="button"
              onClick={() => setSeedError(null)}
              aria-label={t.common.close}
              className="flex-shrink-0 opacity-70 transition-opacity hover:opacity-100"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05 }}
        className="filter-bar"
      >
        <div className="min-w-[16rem] flex-1">
          <label htmlFor={searchId} className="field-label">
            {t.common.search}
          </label>
          <div className="relative">
            <Search
              aria-hidden
              className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle-foreground"
            />
            <input
              id={searchId}
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t.accountsPage.searchPlaceholder}
              className="input ps-10"
            />
          </div>
        </div>

        <div className="min-w-[10rem]">
          <label htmlFor={typeId} className="field-label">
            {t.accountsPage.type}
          </label>
          <select
            id={typeId}
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="select"
          >
            <option value="">{t.accountsPage.allTypes}</option>
            {ACCOUNT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {(searchQuery || typeFilter) && (
          <button type="button" onClick={clearFilters} className="btn btn-ghost btn-sm mb-0.5">
            {t.common.clearFilters}
          </button>
        )}

        <p className="numeric ms-auto pb-2.5 text-xs text-subtle-foreground">
          {filteredTotal} {t.common.of} {accounts.length} {t.accountsPage.showingAccounts}
        </p>
      </motion.div>

      {accounts.length === 0 && (
        <EmptyState
          icon={<Receipt className="h-7 w-7 text-primary" />}
          title={t.accountsPage.noAccountsTitle}
          description={t.accountsPage.noAccountsDescription}
          action={
            canManage ? (
              <button
                type="button"
                onClick={handleSeed}
                disabled={isSeeding}
                className="btn btn-primary"
              >
                {isSeeding ? (
                  <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                ) : (
                  <Sprout aria-hidden className="h-4 w-4" />
                )}
                {t.accountsPage.seedDefaults}
              </button>
            ) : undefined
          }
        />
      )}

      {accounts.length > 0 && filteredTotal === 0 && (
        <EmptyState
          icon={<Search className="h-7 w-7 text-primary" />}
          title={t.accountsPage.noMatchTitle}
          description={t.accountsPage.noMatchDescription}
          action={
            <button type="button" onClick={clearFilters} className="btn btn-secondary btn-sm">
              {t.common.clearFilters}
            </button>
          }
        />
      )}

      {paginatedAccounts.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          {/* Desktop table */}
          <div className="card hidden overflow-hidden md:block">
            <div className="table-wrap">
              <table className="data-table">
                <caption className="sr-only">{t.accountsPage.pageTitle}</caption>
                <thead>
                  <tr>
                    <th scope="col">{t.accountsPage.code}</th>
                    <th scope="col">{t.accountsPage.name}</th>
                    <th scope="col">{t.accountsPage.type}</th>
                    <th scope="col">{t.accountsPage.parentCode}</th>
                    <th scope="col">{t.common.status}</th>
                    <th scope="col">{t.accountsPage.origin}</th>
                    <th scope="col">{t.common.description}</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedAccounts.map((acc) => (
                    <tr key={acc.id}>
                      <td>
                        <span className="numeric text-sm font-semibold text-primary">
                          {acc.code}
                        </span>
                      </td>
                      <td className="font-medium">{acc.name}</td>
                      <td>
                        <AccountTypeBadge type={acc.account_type} />
                      </td>
                      <td className="numeric text-xs text-muted-foreground">{parentCodeOf(acc)}</td>
                      <td>
                        <span className={`badge ${acc.is_active ? 'tone-success' : 'tone-neutral'}`}>
                          {acc.is_active ? t.common.active : t.common.inactive}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${acc.is_system ? 'tone-info' : 'tone-neutral'}`}>
                          {acc.is_system ? t.accountsPage.systemAccount : t.accountsPage.manualAccount}
                        </span>
                      </td>
                      <td
                        className="max-w-[220px] truncate text-xs text-muted-foreground"
                        title={acc.description || undefined}
                      >
                        {acc.description || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="border-t border-border-subtle px-4 py-3">
              <PaginationControls
                skip={skip}
                limit={PAGE_SIZE}
                total={filteredTotal}
                onPrev={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
                onNext={() => setSkip(skip + PAGE_SIZE)}
              />
            </div>
          </div>

          {/* Mobile card list */}
          <div className="space-y-3 md:hidden">
            {paginatedAccounts.map((acc) => (
              <div key={acc.id} className="card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <span className="numeric text-xs font-semibold text-primary">{acc.code}</span>
                    <h3 className="mt-0.5 text-sm font-medium text-foreground">{acc.name}</h3>
                  </div>
                  <AccountTypeBadge type={acc.account_type} />
                </div>

                {acc.description && (
                  <p className="mt-2 text-xs text-muted-foreground">{acc.description}</p>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className={`badge ${acc.is_active ? 'tone-success' : 'tone-neutral'}`}>
                    {acc.is_active ? t.common.active : t.common.inactive}
                  </span>
                  <span className={`badge ${acc.is_system ? 'tone-info' : 'tone-neutral'}`}>
                    {acc.is_system ? t.accountsPage.systemAccount : t.accountsPage.manualAccount}
                  </span>
                  {acc.parent_id && (
                    <span className="numeric text-[11px] text-subtle-foreground">
                      {t.accountsPage.parent}: {parentCodeOf(acc)}
                    </span>
                  )}
                </div>
              </div>
            ))}

            <PaginationControls
              skip={skip}
              limit={PAGE_SIZE}
              total={filteredTotal}
              onPrev={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
              onNext={() => setSkip(skip + PAGE_SIZE)}
            />
          </div>
        </motion.div>
      )}
    </div>
  );
}
