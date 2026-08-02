import { useState, useEffect, useMemo, useId, Fragment } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, Search, ChevronDown, CheckCircle2, Plus } from 'lucide-react';
import { dataEvents } from '../../lib/dataEvents';
import PageLayout from '../../components/layout/PageLayout';
import { useI18n } from '../../i18n';
import {
  canCreateJournal,
  canReviewJournal,
  canPostJournal,
  canVoidJournal,
  canReverseJournal,
} from '../../auth/permissions';
import type { CompanyUserRole } from '../../api/types';
import { useToast } from '../../components/feedback/useToast';
import JournalStatusBadge from './JournalStatusBadge';
import JournalEntryLines from './JournalEntryLines';
import PaginationControls from '../../components/ui/PaginationControls';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import EmptyState from '../../components/feedback/EmptyState';
import { useJournalEntries } from './useJournalEntries';
import { formatCurrency as fmtCurrency } from '../../lib/format';
import type { JournalEntry, JournalEntryStatus } from '../../api/types';
import type { Translations } from '../../i18n/types';
import CreateJournalEntryModal from './CreateJournalEntryModal';
import { useReviewJournalEntry } from './useReviewJournalEntry';
import ReviewJournalEntryModal from './ReviewJournalEntryModal';
import { usePostJournalEntry } from './usePostJournalEntry';
import PostJournalEntryModal from './PostJournalEntryModal';
import { useVoidJournalEntry } from './useVoidJournalEntry';
import VoidJournalEntryModal from './VoidJournalEntryModal';
import { useReverseJournalEntry } from './useReverseJournalEntry';
import ReverseJournalEntryModal from './ReverseJournalEntryModal';

const STATUSES: JournalEntryStatus[] = ['draft', 'reviewed', 'posted', 'void', 'reversed'];

function calcTotals(entry: JournalEntry) {
  let debit = 0;
  let credit = 0;
  for (const line of entry.lines) {
    debit += parseFloat(line.debit) || 0;
    credit += parseFloat(line.credit) || 0;
  }
  return { debit, credit, balanced: Math.abs(debit - credit) < 0.005 };
}

/** Unknown source types fall back to a readable form of the raw backend value. */
function journalSourceLabel(sourceType: string | null, t: Translations): string {
  const labels: Record<string, string> = {
    manual: t.journals.sourceManual,
    gemini_assistant: t.journals.sourceAssistant,
    reversal: t.journals.sourceReversal,
    opening_balance: t.journals.sourceOpeningBalance,
  };
  const key = sourceType || 'manual';
  return labels[key] || key.replace(/_/g, ' ');
}

export default function JournalEntriesPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.journals.pageTitle}
      pageSubtitle={t.journals.pageSubtitle}
      activePath="/journal-entries"
    >
      {({ selectedCompanyId, companiesLoading, userRole }) => (
        <JournalEntriesContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
          userRole={userRole}
        />
      )}
    </PageLayout>
  );
}

interface JournalEntriesContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
  userRole: CompanyUserRole | null;
}

function JournalEntriesContent({
  selectedCompanyId,
  companiesLoading,
  userRole,
}: JournalEntriesContentProps) {
  const { t } = useI18n();
  const toast = useToast();
  const searchId = useId();
  const statusId = useId();

  const [skip, setSkip] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [searchParams] = useSearchParams();
  const requestedEntryId = Number(searchParams.get('entry_id'));
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedReviewEntry, setSelectedReviewEntry] = useState<JournalEntry | null>(null);
  const [selectedPostEntry, setSelectedPostEntry] = useState<JournalEntry | null>(null);
  const [selectedVoidEntry, setSelectedVoidEntry] = useState<JournalEntry | null>(null);
  const [selectedReverseEntry, setSelectedReverseEntry] = useState<JournalEntry | null>(null);

  const {
    entries,
    total,
    isLoading: entriesLoading,
    error,
    fetchEntries,
    pageSize,
  } = useJournalEntries({ companyId: selectedCompanyId, skip });

  useEffect(() => {
    if (!Number.isInteger(requestedEntryId) || requestedEntryId <= 0 || entriesLoading) return;
    if (entries.some((entry) => entry.id === requestedEntryId)) setExpandedId(requestedEntryId);
  }, [entries, entriesLoading, requestedEntryId]);

  const {
    reviewJournalEntry,
    isSubmitting: isReviewSubmitting,
    submitError: reviewSubmitError,
    setSubmitError: setReviewSubmitError,
  } = useReviewJournalEntry();

  const {
    postJournalEntry,
    isSubmitting: isPostSubmitting,
    submitError: postSubmitError,
    setSubmitError: setPostSubmitError,
  } = usePostJournalEntry();

  const {
    voidJournalEntry,
    isSubmitting: isVoidSubmitting,
    submitError: voidSubmitError,
    setSubmitError: setVoidSubmitError,
  } = useVoidJournalEntry();

  const {
    reverseJournalEntry,
    isSubmitting: isReverseSubmitting,
    submitError: reverseSubmitError,
    setSubmitError: setReverseSubmitError,
  } = useReverseJournalEntry();

  const handleOpenReviewModal = (entry: JournalEntry) => {
    setSelectedReviewEntry(entry);
    setReviewSubmitError(null);
  };

  const handleConfirmReview = async () => {
    if (!selectedReviewEntry) return;
    const updated = await reviewJournalEntry(selectedReviewEntry.id);
    if (updated) {
      setSelectedReviewEntry(null);
      toast.success(t.journals.successReviewed);
      fetchEntries();
      dataEvents.emit('journal:mutated');
    }
  };

  const handleOpenPostModal = (entry: JournalEntry) => {
    setSelectedPostEntry(entry);
    setPostSubmitError(null);
  };

  const handleConfirmPost = async () => {
    if (!selectedPostEntry) return;
    const updated = await postJournalEntry(selectedPostEntry.id);
    if (updated) {
      setSelectedPostEntry(null);
      toast.success(t.journals.successPosted);
      fetchEntries();
      dataEvents.emit('journal:mutated');
    }
  };

  const handleOpenVoidModal = (entry: JournalEntry) => {
    setSelectedVoidEntry(entry);
    setVoidSubmitError(null);
  };

  const handleConfirmVoid = async () => {
    if (!selectedVoidEntry) return;
    const updated = await voidJournalEntry(selectedVoidEntry.id);
    if (updated) {
      setSelectedVoidEntry(null);
      toast.success(t.journals.successVoided);
      fetchEntries();
      dataEvents.emit('journal:mutated');
    }
  };

  const handleOpenReverseModal = (entry: JournalEntry) => {
    setSelectedReverseEntry(entry);
    setReverseSubmitError(null);
  };

  const handleConfirmReverse = async (payload: {
    entry_no: string;
    entry_date: string;
    description: string;
  }) => {
    if (!selectedReverseEntry) return;
    const updated = await reverseJournalEntry(selectedReverseEntry.id, payload);
    if (updated) {
      setSelectedReverseEntry(null);
      toast.success(t.journals.successReversalDraft);
      fetchEntries();
      dataEvents.emit('journal:mutated');
    }
  };

  useEffect(() => {
    setSkip(0);
    setSearchQuery('');
    setStatusFilter('');
    setExpandedId(null);
    setIsCreateModalOpen(false);
    setSelectedReviewEntry(null);
    setSelectedPostEntry(null);
    setSelectedVoidEntry(null);
    setSelectedReverseEntry(null);
  }, [selectedCompanyId]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  // Client-side filtering within the loaded page
  const filteredEntries = useMemo(() => {
    let result = entries;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (e) =>
          (e.entry_no && e.entry_no.toLowerCase().includes(q)) ||
          (e.description && e.description.toLowerCase().includes(q)) ||
          (e.source_type && e.source_type.toLowerCase().includes(q)),
      );
    }

    if (statusFilter) {
      result = result.filter((e) => e.status === statusFilter);
    }

    return result;
  }, [entries, searchQuery, statusFilter]);

  const clearFilters = () => {
    setSearchQuery('');
    setStatusFilter('');
  };

  const statusLabel = (status: JournalEntryStatus): string =>
    ({
      draft: t.journals.draft,
      reviewed: t.journals.reviewed,
      posted: t.journals.posted,
      void: t.journals.voided,
      reversed: t.journals.reversed,
    })[status];

  /**
   * The one action that moves an entry forward, plus the destructive escape
   * hatch. Rendering only the legal transitions keeps the row uncluttered and
   * makes the next step obvious.
   */
  const renderActions = (entry: JournalEntry) => (
    <div className="flex items-center justify-end gap-1.5 whitespace-nowrap">
      {entry.status === 'draft' && (
        <>
          {canReviewJournal(userRole) && (
            <button
              type="button"
              onClick={() => handleOpenReviewModal(entry)}
              className="btn btn-tone tone-primary btn-sm"
            >
              {t.journals.review}
            </button>
          )}
          {canVoidJournal(userRole) && (
            <button
              type="button"
              onClick={() => handleOpenVoidModal(entry)}
              className="btn btn-danger-ghost btn-sm"
            >
              {t.journals.void}
            </button>
          )}
        </>
      )}
      {entry.status === 'reviewed' && canPostJournal(userRole) && (
        <button
          type="button"
          onClick={() => handleOpenPostModal(entry)}
          className="btn btn-tone tone-warning btn-sm"
        >
          {t.journals.post}
        </button>
      )}
      {entry.status === 'posted' && canReverseJournal(userRole) && (
        <button
          type="button"
          onClick={() => handleOpenReverseModal(entry)}
          className="btn btn-tone tone-violet btn-sm"
        >
          {t.journals.reverse}
        </button>
      )}
    </div>
  );

  const hasActions = (entry: JournalEntry) =>
    (entry.status === 'draft' && (canReviewJournal(userRole) || canVoidJournal(userRole))) ||
    (entry.status === 'reviewed' && canPostJournal(userRole)) ||
    (entry.status === 'posted' && canReverseJournal(userRole));

  const modals = (
    <>
      <CreateJournalEntryModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          setIsCreateModalOpen(false);
          toast.success(t.journals.successCreatedDraft);
          fetchEntries();
          dataEvents.emit('journal:created');
        }}
        companyId={selectedCompanyId}
      />

      <ReviewJournalEntryModal
        isOpen={!!selectedReviewEntry}
        onClose={() => setSelectedReviewEntry(null)}
        onConfirm={handleConfirmReview}
        isSubmitting={isReviewSubmitting}
        error={reviewSubmitError}
        entryNo={selectedReviewEntry?.entry_no || ''}
      />

      <PostJournalEntryModal
        isOpen={!!selectedPostEntry}
        onClose={() => setSelectedPostEntry(null)}
        onConfirm={handleConfirmPost}
        isSubmitting={isPostSubmitting}
        error={postSubmitError}
        entryNo={selectedPostEntry?.entry_no || ''}
        entryDate={selectedPostEntry?.entry_date}
        entryDescription={selectedPostEntry?.description || undefined}
      />

      <VoidJournalEntryModal
        isOpen={!!selectedVoidEntry}
        onClose={() => setSelectedVoidEntry(null)}
        onConfirm={handleConfirmVoid}
        isSubmitting={isVoidSubmitting}
        error={voidSubmitError}
        entryNo={selectedVoidEntry?.entry_no || ''}
        entryDate={selectedVoidEntry?.entry_date}
        entryDescription={selectedVoidEntry?.description || undefined}
      />

      <ReverseJournalEntryModal
        isOpen={!!selectedReverseEntry}
        onClose={() => setSelectedReverseEntry(null)}
        onConfirm={handleConfirmReverse}
        isSubmitting={isReverseSubmitting}
        error={reverseSubmitError}
        originalEntry={selectedReverseEntry}
      />
    </>
  );

  const isLoading = companiesLoading || entriesLoading;
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={fetchEntries} />;

  return (
    <div className="space-y-5">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
      >
        <div>
          <h2 className="page-title">{t.journals.pageTitle}</h2>
          <p className="page-description">{t.journals.pageSubtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="numeric text-xs text-subtle-foreground">
            {total} {t.journals.showingEntries}
          </span>
          {selectedCompanyId && canCreateJournal(userRole) && (
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(true)}
              className="btn btn-primary"
            >
              <Plus aria-hidden className="h-4 w-4" />
              {t.journals.newEntry}
            </button>
          )}
        </div>
      </motion.div>

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
              placeholder={t.journals.searchPlaceholder}
              className="input ps-10"
            />
          </div>
        </div>

        <div className="min-w-[11rem]">
          <label htmlFor={statusId} className="field-label">
            {t.common.status}
          </label>
          <select
            id={statusId}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="select"
          >
            <option value="">{t.journals.allStatuses}</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
        </div>

        {(searchQuery || statusFilter) && (
          <button type="button" onClick={clearFilters} className="btn btn-ghost btn-sm mb-0.5">
            {t.common.clearFilters}
          </button>
        )}

        <p className="numeric ms-auto pb-2.5 text-xs text-subtle-foreground">
          {filteredEntries.length} {t.common.of} {entries.length} {t.journals.showingEntries}
        </p>
      </motion.div>

      {entries.length === 0 && (
        <EmptyState
          icon={<BookOpen className="h-7 w-7 text-primary" />}
          title={t.journals.noEntriesTitle}
          description={t.journals.noEntriesDescription}
          action={
            selectedCompanyId && canCreateJournal(userRole) ? (
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(true)}
                className="btn btn-primary"
              >
                <Plus aria-hidden className="h-4 w-4" />
                {t.journals.newEntry}
              </button>
            ) : undefined
          }
        />
      )}

      {entries.length > 0 && filteredEntries.length === 0 && (
        <EmptyState
          icon={<Search className="h-7 w-7 text-primary" />}
          title={t.journals.noMatchTitle}
          description={t.journals.noMatchDescription}
          action={
            <button type="button" onClick={clearFilters} className="btn btn-secondary btn-sm">
              {t.common.clearFilters}
            </button>
          }
        />
      )}

      {filteredEntries.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          {/* Desktop table */}
          <div className="card hidden overflow-hidden lg:block">
            <div className="table-wrap">
              <table className="data-table">
                <caption className="sr-only">{t.journals.pageTitle}</caption>
                <thead>
                  <tr>
                    <th scope="col" className="w-8" />
                    <th scope="col">{t.journals.entryNo}</th>
                    <th scope="col">{t.journals.entryDate}</th>
                    <th scope="col">{t.common.description}</th>
                    <th scope="col">{t.common.status}</th>
                    {/* Provenance is context, not a decision input — it yields
                        width first, and stays available in the expanded row. */}
                    <th scope="col" className="hidden xl:table-cell">
                      {t.common.source}
                    </th>
                    <th scope="col" className="cell-numeric">
                      {t.journals.debit}
                    </th>
                    <th scope="col" className="cell-numeric">
                      {t.journals.credit}
                    </th>
                    <th scope="col" className="cell-sticky-end text-end">
                      {t.common.actions}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEntries.map((entry) => {
                    const totals = calcTotals(entry);
                    const isExpanded = expandedId === entry.id;
                    const panelId = `journal-lines-${entry.id}`;

                    return (
                      <Fragment key={entry.id}>
                        <tr
                          onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                          className={`cursor-pointer ${isExpanded ? 'bg-surface-muted' : ''}`}
                        >
                          <td>
                            <button
                              type="button"
                              aria-expanded={isExpanded}
                              aria-controls={panelId}
                              aria-label={entry.entry_no}
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedId(isExpanded ? null : entry.id);
                              }}
                              className="text-subtle-foreground transition-colors hover:text-foreground"
                            >
                              <ChevronDown
                                aria-hidden
                                className={`h-4 w-4 transition-transform duration-normal ease-emphasized ${
                                  isExpanded ? 'rotate-180' : ''
                                }`}
                              />
                            </button>
                          </td>
                          <td>
                            <span
                              className="numeric block max-w-[140px] truncate text-sm font-semibold text-primary"
                              title={entry.entry_no}
                            >
                              {entry.entry_no}
                            </span>
                          </td>
                          <td className="whitespace-nowrap text-muted-foreground">
                            {new Date(entry.entry_date).toLocaleDateString()}
                          </td>
                          <td>
                            <span
                              className="block max-w-[200px] truncate xl:max-w-[260px]"
                              title={entry.description || undefined}
                            >
                              {entry.description || '—'}
                            </span>
                          </td>
                          <td>
                            <JournalStatusBadge status={entry.status} />
                          </td>
                          <td className="hidden xl:table-cell">
                            <span className="block text-xs font-medium text-muted-foreground">
                              {journalSourceLabel(entry.source_type, t)}
                            </span>
                            <span className="block max-w-[140px] truncate text-[11px] text-subtle-foreground">
                              {t.common.by}: {entry.creator_name || t.common.notAvailable}
                            </span>
                          </td>
                          <td className="cell-numeric text-debit">
                            {fmtCurrency(totals.debit)}
                          </td>
                          <td className="cell-numeric">
                            <span className="inline-flex items-center gap-1.5">
                              <span className="text-credit">{fmtCurrency(totals.credit)}</span>
                              {totals.balanced && (
                                <CheckCircle2
                                  aria-label={t.journals.balanced}
                                  className="h-3.5 w-3.5 flex-shrink-0 text-success"
                                />
                              )}
                            </span>
                          </td>
                          <td
                            className="cell-sticky-end"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {renderActions(entry)}
                          </td>
                        </tr>

                        {isExpanded && (
                          <tr id={panelId}>
                            <td colSpan={9} className="p-0">
                              <div className="flex flex-wrap gap-x-5 gap-y-1 border-b border-border-subtle bg-surface-muted px-4 py-2 text-[11px] text-subtle-foreground">
                                <span>
                                  {t.journals.lines}: {entry.lines.length}
                                </span>
                                <span>
                                  {t.journals.posted}:{' '}
                                  {entry.posted_at
                                    ? new Date(entry.posted_at).toLocaleDateString()
                                    : '—'}
                                </span>
                                <span>
                                  {t.common.source}: {journalSourceLabel(entry.source_type, t)} ·{' '}
                                  {t.common.by}: {entry.creator_name || t.common.notAvailable}
                                </span>
                              </div>
                              <JournalEntryLines lines={entry.lines} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="border-t border-border-subtle px-4 py-3">
              <PaginationControls
                skip={skip}
                limit={pageSize}
                total={total}
                onPrev={() => setSkip(Math.max(0, skip - pageSize))}
                onNext={() => setSkip(skip + pageSize)}
                entityName={t.journals.showingEntries}
              />
            </div>
          </div>

          {/* Mobile cards */}
          <div className="space-y-3 lg:hidden">
            {filteredEntries.map((entry) => {
              const totals = calcTotals(entry);
              const isExpanded = expandedId === entry.id;
              const panelId = `journal-lines-mobile-${entry.id}`;

              return (
                <div key={entry.id} className="card overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                    aria-expanded={isExpanded}
                    aria-controls={panelId}
                    className="w-full p-4 text-start"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <span className="numeric text-xs font-semibold text-primary">
                          {entry.entry_no}
                        </span>
                        <p className="mt-0.5 text-sm font-medium text-foreground">
                          {entry.description || t.common.noDescription}
                        </p>
                      </div>
                      <div className="flex flex-shrink-0 items-center gap-2">
                        <JournalStatusBadge status={entry.status} />
                        <ChevronDown
                          aria-hidden
                          className={`h-4 w-4 text-subtle-foreground transition-transform duration-normal ease-emphasized ${
                            isExpanded ? 'rotate-180' : ''
                          }`}
                        />
                      </div>
                    </div>

                    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-subtle-foreground">
                      <span>{new Date(entry.entry_date).toLocaleDateString()}</span>
                      <span>
                        {entry.lines.length} {t.journals.lines.toLowerCase()}
                      </span>
                      <span>
                        {journalSourceLabel(entry.source_type, t)} · {t.common.by}:{' '}
                        {entry.creator_name || t.common.notAvailable}
                      </span>
                    </div>

                    <div className="mt-3 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <span className="numeric text-xs text-debit">
                          {t.journals.debit} {fmtCurrency(totals.debit)}
                        </span>
                        <span className="numeric text-xs text-credit">
                          {t.journals.credit} {fmtCurrency(totals.credit)}
                        </span>
                      </div>
                      {totals.balanced && (
                        <span className="badge tone-success">
                          <CheckCircle2 aria-hidden className="h-3 w-3" />
                          {t.journals.balanced}
                        </span>
                      )}
                    </div>
                  </button>

                  {hasActions(entry) && (
                    <div className="flex items-center justify-between border-t border-border-subtle bg-surface-muted px-4 py-2.5">
                      <span className="overline">{t.common.actions}</span>
                      {renderActions(entry)}
                    </div>
                  )}

                  <AnimatePresence>
                    {isExpanded && (
                      <div id={panelId} className="border-t border-border-subtle">
                        <JournalEntryLines lines={entry.lines} />
                      </div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}

            <PaginationControls
              skip={skip}
              limit={pageSize}
              total={total}
              onPrev={() => setSkip(Math.max(0, skip - pageSize))}
              onNext={() => setSkip(skip + pageSize)}
              entityName={t.journals.showingEntries}
            />
          </div>
        </motion.div>
      )}

      {modals}
    </div>
  );
}
