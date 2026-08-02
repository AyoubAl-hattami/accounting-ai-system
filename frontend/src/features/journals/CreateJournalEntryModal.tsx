import { useState, useEffect, useId, useMemo } from 'react';
import { Plus, Trash2, CheckCircle2, AlertCircle, Search, Save, Check } from 'lucide-react';
import { useAccounts } from '../../entities/account';
import { useCreateJournalEntry } from './useCreateJournalEntry';
import { formatCurrency as fmtCurrency } from '../../lib/format';
import { useI18n } from '../../i18n';
import { AccountTypeBadge } from '../../entities/account';
import type { Account } from '../../api/types';
import Modal from '../../components/ui/Modal';
import { useToast } from '../../components/feedback/useToast';
import JournalAssistantPanel from './assistant/JournalAssistantPanel';

interface CreateJournalEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  companyId: number | null;
}

interface LineState {
  account_id: number | null;
  debit: string;
  credit: string;
  description: string;
}

function getLocalIsoDate(date = new Date()): string {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 10);
}

// ─── Account picker ──────────────────────────────────────────────────────────

interface AccountPickerProps {
  isOpen: boolean;
  accounts: Account[];
  selectedAccountId: number | null;
  lineIndex: number;
  onSelect: (accountId: number) => void;
  onClose: () => void;
}

/** Searchable list of active accounts, opened on top of the entry dialog. */
function AccountPickerModal({
  isOpen,
  accounts,
  selectedAccountId,
  lineIndex,
  onSelect,
  onClose,
}: AccountPickerProps) {
  const { t } = useI18n();
  const [search, setSearch] = useState('');
  const searchId = useId();

  useEffect(() => {
    if (isOpen) setSearch('');
  }, [isOpen]);

  const filtered = useMemo(() => {
    const active = accounts.filter((a) => a.is_active);
    const q = search.toLowerCase().trim();
    if (!q) return active;
    return active.filter(
      (a) =>
        a.code.toLowerCase().includes(q) ||
        a.name.toLowerCase().includes(q) ||
        a.account_type.toLowerCase().includes(q),
    );
  }, [accounts, search]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t.common.selectAccount}
      description={`${t.createJournal.chooseAccountForLine} ${lineIndex + 1}`}
      size="lg"
      bodyClassName="flex flex-col overflow-hidden"
      footer={
        <>
          <span className="me-auto text-xs text-subtle-foreground">
            <span className="numeric">{filtered.length}</span> {t.createJournal.accountsAvailable}
          </span>
          <button type="button" onClick={onClose} className="btn btn-secondary btn-sm">
            {t.common.cancel}
          </button>
        </>
      }
    >
      <div className="border-b border-border px-6 py-3">
        <label htmlFor={searchId} className="sr-only">
          {t.createJournal.searchAccountsPlaceholder}
        </label>
        <div className="relative">
          <Search
            aria-hidden
            className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle-foreground"
          />
          <input
            id={searchId}
            type="search"
            autoFocus
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t.createJournal.searchAccountsPlaceholder}
            className="input ps-9"
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-1">
        {filtered.length === 0 ? (
          <p className="px-6 py-10 text-center text-sm text-subtle-foreground">
            {t.createJournal.noAccountsMatched}
          </p>
        ) : (
          filtered.map((acc) => {
            const isSelected = acc.id === selectedAccountId;
            return (
              <button
                key={acc.id}
                type="button"
                onClick={() => onSelect(acc.id)}
                aria-current={isSelected}
                className={`flex w-full items-center gap-3 px-6 py-2.5 text-start transition-colors ${
                  isSelected ? 'bg-primary-soft' : 'hover:bg-surface-muted'
                }`}
              >
                <span className="numeric flex-shrink-0 text-sm font-semibold text-primary">{acc.code}</span>
                <span className="min-w-0 flex-1 truncate text-sm text-foreground">{acc.name}</span>
                <AccountTypeBadge type={acc.account_type} />
                {isSelected && <Check aria-hidden className="h-4 w-4 flex-shrink-0 text-primary" />}
              </button>
            );
          })
        )}
      </div>
    </Modal>
  );
}

// ─── Create journal entry ────────────────────────────────────────────────────

export default function CreateJournalEntryModal({
  isOpen,
  onClose,
  onSuccess,
  companyId,
}: CreateJournalEntryModalProps) {
  const { accounts, fetchAccounts } = useAccounts({ companyId, skip: 0, limit: 500 });
  const { createJournalEntry, isSubmitting, submitError, setSubmitError } = useCreateJournalEntry();
  const { t } = useI18n();
  const toast = useToast();

  const formId = useId();
  const entryNoId = useId();
  const entryDateId = useId();
  const descriptionId = useId();

  // ── Assistant State ──
  const [pendingSuggestion, setPendingSuggestion] = useState<{
    debitAccountId?: number;
    creditAccountId?: number;
    amount?: number;
    description: string;
  } | null>(null);
  const [showReplaceConfirm, setShowReplaceConfirm] = useState(false);

  const applySuggestionDirectly = (suggestion: {
    debitAccountId?: number;
    creditAccountId?: number;
    amount?: number;
    description: string;
  }) => {
    if (!description.trim()) {
      setDescription(suggestion.description);
    }
    const amountStr = suggestion.amount !== undefined ? String(suggestion.amount) : '';
    setLines([
      {
        account_id: suggestion.debitAccountId ?? null,
        debit: amountStr,
        credit: '',
        description: suggestion.description,
      },
      {
        account_id: suggestion.creditAccountId ?? null,
        debit: '',
        credit: amountStr,
        description: suggestion.description,
      },
    ]);
    toast.success(t.journals.assistantApplied || 'Assistant suggestion applied.');
  };

  const handleApplySuggestion = (suggestion: {
    debitAccountId?: number;
    creditAccountId?: number;
    amount?: number;
    description: string;
  }) => {
    const empty = lines.every((line) => !line.account_id && !line.debit && !line.credit && !line.description);
    if (empty) {
      applySuggestionDirectly(suggestion);
    } else {
      setPendingSuggestion(suggestion);
      setShowReplaceConfirm(true);
    }
  };

  // ── Auto-generate default entry number ──
  const generateDefaultEntryNo = () => {
    const now = new Date();
    const pad = (num: number) => String(num).padStart(2, '0');
    const yyyymmddhhmmss =
      now.getFullYear() +
      pad(now.getMonth() + 1) +
      pad(now.getDate()) +
      pad(now.getHours()) +
      pad(now.getMinutes()) +
      pad(now.getSeconds());
    return `JE-FE-${yyyymmddhhmmss}`;
  };

  const [entryNo, setEntryNo] = useState('');
  const [entryDate, setEntryDate] = useState(() => getLocalIsoDate());
  const [description, setDescription] = useState('');
  const [sourceType] = useState('manual');
  const [sourceId] = useState('FRONTEND');

  const [lines, setLines] = useState<LineState[]>([
    { account_id: null, debit: '', credit: '', description: '' },
    { account_id: null, debit: '', credit: '', description: '' },
  ]);

  const [pickerLineIndex, setPickerLineIndex] = useState<number | null>(null);

  // Initialize form when modal opens
  useEffect(() => {
    if (isOpen) {
      setEntryNo(generateDefaultEntryNo());
      setEntryDate(getLocalIsoDate());
      setDescription('');
      setLines([
        { account_id: null, debit: '', credit: '', description: '' },
        { account_id: null, debit: '', credit: '', description: '' },
      ]);
      setSubmitError(null);
      setPickerLineIndex(null);
    }
  }, [isOpen, setSubmitError]);

  // Load accounts when modal opens or company changes
  useEffect(() => {
    if (isOpen && companyId) {
      fetchAccounts();
    }
  }, [isOpen, companyId, fetchAccounts]);

  // ── Handlers ──
  const addLine = () => {
    setLines([...lines, { account_id: null, debit: '', credit: '', description: '' }]);
  };

  const removeLine = (index: number) => {
    if (lines.length <= 2) return;
    setLines(lines.filter((_, i) => i !== index));
  };

  const handleLineChange = (index: number, field: keyof LineState, value: string | number | null) => {
    setLines(
      lines.map((line, i) => {
        if (i !== index) return line;
        const updated = { ...line, [field]: value };

        // A line carries one side only, so typing into one clears the other.
        if (field === 'debit' && value !== '') {
          updated.credit = '';
        } else if (field === 'credit' && value !== '') {
          updated.debit = '';
        }

        return updated;
      }),
    );
  };

  const handleAccountSelect = (accountId: number) => {
    if (pickerLineIndex !== null) {
      handleLineChange(pickerLineIndex, 'account_id', accountId);
      setPickerLineIndex(null);
    }
  };

  // ── Calculation / Validation ──
  const totals = useMemo(() => {
    let debit = 0;
    let credit = 0;
    lines.forEach((line) => {
      debit += parseFloat(line.debit) || 0;
      credit += parseFloat(line.credit) || 0;
    });
    const difference = Math.abs(debit - credit);
    const isBalanced = difference < 0.005 && debit > 0;
    return { debit, credit, difference, isBalanced };
  }, [lines]);

  const validationErrors = useMemo(() => {
    const errors: string[] = [];

    if (lines.length < 2) {
      errors.push(t.createJournal.errMinLines);
    }

    let hasEmptyAccount = false;
    let hasBothDebitAndCredit = false;
    let hasNeitherDebitNorCredit = false;

    lines.forEach((line) => {
      if (!line.account_id) {
        hasEmptyAccount = true;
      }
      const d = parseFloat(line.debit) || 0;
      const c = parseFloat(line.credit) || 0;
      if (d > 0 && c > 0) {
        hasBothDebitAndCredit = true;
      }
      if (d <= 0 && c <= 0) {
        hasNeitherDebitNorCredit = true;
      }
    });

    if (hasEmptyAccount) {
      errors.push(t.createJournal.errAccountRequired);
    }
    if (hasBothDebitAndCredit) {
      errors.push(t.createJournal.errBothSides);
    }
    if (hasNeitherDebitNorCredit) {
      errors.push(t.createJournal.errNoSide);
    }
    if (totals.debit <= 0) {
      errors.push(t.createJournal.errDebitPositive);
    }
    if (Math.abs(totals.debit - totals.credit) >= 0.005) {
      errors.push(`${t.createJournal.errUnbalanced} ${fmtCurrency(totals.difference)}.`);
    }

    return errors;
  }, [lines, totals, t]);

  const isValid = validationErrors.length === 0;

  // ── Form Submission ──
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || isSubmitting || !companyId) return;

    const formattedLines = lines.map((line) => ({
      account_id: line.account_id!,
      debit: parseFloat(line.debit) || 0,
      credit: parseFloat(line.credit) || 0,
      description: line.description || description || 'Manual line entry',
    }));

    const payload = {
      company_id: companyId,
      entry_no: entryNo.trim(),
      entry_date: entryDate,
      description: description.trim() || 'Manual journal entry',
      source_type: sourceType,
      source_id: sourceId,
      lines: formattedLines,
    };

    const result = await createJournalEntry(payload);
    if (result) {
      onSuccess();
    }
  };

  const renderAccountButton = (line: LineState, idx: number) => {
    const selectedAcc = accounts.find((a) => a.id === line.account_id);
    return (
      <button
        type="button"
        onClick={() => setPickerLineIndex(idx)}
        aria-label={`${t.createJournal.chooseAccountForLine} ${idx + 1}`}
        className="input flex items-center justify-between gap-2 text-start text-xs"
      >
        {selectedAcc ? (
          <span className="flex min-w-0 items-center gap-2">
            <span className="numeric font-semibold text-primary">{selectedAcc.code}</span>
            <span className="truncate text-foreground">{selectedAcc.name}</span>
          </span>
        ) : (
          <span className="text-subtle-foreground">{t.common.selectAccountPrompt}</span>
        )}
        <Search aria-hidden className="h-3.5 w-3.5 flex-shrink-0 text-subtle-foreground" />
      </button>
    );
  };

  const amountInputProps = {
    type: 'number' as const,
    step: 'any',
    min: '0',
    placeholder: '0.00',
    className: 'input numeric text-end text-xs',
  };

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={t.createJournal.newJournalEntry}
        description={t.createJournal.newJournalEntryDesc}
        size="2xl"
        error={submitError}
        busy={isSubmitting}
        bodyClassName="flex flex-col overflow-hidden lg:flex-row"
        footer={
          <div className="flex w-full flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <dl className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
              <div className="flex items-center gap-1.5">
                <dt className="overline">{t.createJournal.totalDebit}</dt>
                <dd className="numeric font-semibold text-debit">{fmtCurrency(totals.debit)}</dd>
              </div>
              <div className="flex items-center gap-1.5">
                <dt className="overline">{t.createJournal.totalCredit}</dt>
                <dd className="numeric font-semibold text-credit">{fmtCurrency(totals.credit)}</dd>
              </div>
              <div className="flex items-center gap-1.5">
                <dt className="overline">{t.createJournal.difference}</dt>
                <dd
                  className={`numeric font-semibold ${
                    totals.difference > 0 ? 'text-warning' : 'text-muted-foreground'
                  }`}
                >
                  {fmtCurrency(totals.difference)}
                </dd>
              </div>
              <span className={`badge badge-uppercase ${totals.isBalanced ? 'tone-success' : 'tone-danger'}`}>
                {totals.isBalanced ? (
                  <CheckCircle2 aria-hidden className="h-3 w-3" />
                ) : (
                  <AlertCircle aria-hidden className="h-3 w-3" />
                )}
                {totals.isBalanced ? t.createJournal.balanced : t.createJournal.unbalanced}
              </span>
            </dl>

            <div className="flex items-center justify-end gap-2.5">
              <button type="button" onClick={onClose} disabled={isSubmitting} className="btn btn-ghost btn-sm">
                {t.common.cancel}
              </button>
              <button
                type="submit"
                form={formId}
                disabled={!isValid || isSubmitting}
                className="btn btn-primary btn-sm"
              >
                <Save aria-hidden className="h-3.5 w-3.5" />
                {isSubmitting ? t.createJournal.submitting : t.createJournal.submit}
              </button>
            </div>
          </div>
        }
      >
        <form id={formId} onSubmit={handleSubmit} className="min-h-0 flex-1 space-y-6 overflow-y-auto p-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <label htmlFor={entryNoId} className="field-label">
                {t.createJournal.entryNoLabel}
              </label>
              <input
                id={entryNoId}
                type="text"
                required
                value={entryNo}
                onChange={(e) => setEntryNo(e.target.value)}
                placeholder={t.createJournal.entryNoPlaceholder}
                className="input numeric"
              />
            </div>
            <div>
              <label htmlFor={entryDateId} className="field-label">
                {t.createJournal.dateLabel}
              </label>
              <input
                id={entryDateId}
                type="date"
                required
                value={entryDate}
                onChange={(e) => setEntryDate(e.target.value)}
                className="input numeric"
              />
            </div>
            <div>
              <label htmlFor={descriptionId} className="field-label">
                {t.createJournal.descriptionLabel}
              </label>
              <input
                id={descriptionId}
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t.createJournal.descriptionPlaceholder}
                className="input"
              />
            </div>
          </div>

          <dl className="flex flex-wrap gap-x-6 gap-y-1 rounded-lg border border-border-subtle bg-surface-muted px-3.5 py-2.5 text-xs">
            <div className="flex items-center gap-1.5">
              <dt className="overline">{t.common.sourceType}</dt>
              <dd className="text-muted-foreground">{sourceType}</dd>
            </div>
            <div className="flex items-center gap-1.5">
              <dt className="overline">{t.common.sourceId}</dt>
              <dd className="text-muted-foreground">{sourceId}</dd>
            </div>
          </dl>

          {validationErrors.length > 0 && lines.some((l) => l.account_id) && (
            <div role="status" className="callout tone-warning text-xs">
              <AlertCircle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{t.common.validationWarnings}</p>
                <ul className="mt-1 list-disc space-y-1 ps-4">
                  {validationErrors.map((err) => (
                    <li key={err}>{err}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <section>
            <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-foreground">{t.createJournal.linesTitle}</h3>
                <p className="mt-0.5 text-xs text-subtle-foreground">{t.createJournal.lineRule}</p>
              </div>
              <button
                type="button"
                onClick={addLine}
                className="btn btn-tone tone-primary btn-sm self-start sm:self-auto"
              >
                <Plus aria-hidden className="h-3.5 w-3.5" />
                {t.createJournal.addLine}
              </button>
            </div>

            <div className="rounded-lg border border-border bg-surface-muted">
              {/* Desktop grid */}
              <table className="hidden w-full border-collapse text-start sm:table">
                <caption className="sr-only">{t.createJournal.linesTitle}</caption>
                <thead>
                  <tr className="border-b border-border">
                    <th scope="col" className="overline px-4 py-3 text-start">
                      {t.common.account}
                    </th>
                    <th scope="col" className="overline w-[140px] px-4 py-3 text-end">
                      {t.createJournal.debit}
                    </th>
                    <th scope="col" className="overline w-[140px] px-4 py-3 text-end">
                      {t.createJournal.credit}
                    </th>
                    <th scope="col" className="overline px-4 py-3 text-start">
                      {t.createJournal.lineDescription}
                    </th>
                    <th scope="col" className="overline w-[56px] px-4 py-3 text-center">
                      {t.common.actions}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {lines.map((line, idx) => (
                    <tr key={idx} className="align-top">
                      <td className="min-w-[240px] px-4 py-3">{renderAccountButton(line, idx)}</td>
                      <td className="px-4 py-3">
                        <input
                          {...amountInputProps}
                          aria-label={`${t.createJournal.debit} ${idx + 1}`}
                          value={line.debit}
                          onChange={(e) => handleLineChange(idx, 'debit', e.target.value)}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          {...amountInputProps}
                          aria-label={`${t.createJournal.credit} ${idx + 1}`}
                          value={line.credit}
                          onChange={(e) => handleLineChange(idx, 'credit', e.target.value)}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="text"
                          aria-label={`${t.createJournal.lineDescription} ${idx + 1}`}
                          value={line.description}
                          onChange={(e) => handleLineChange(idx, 'description', e.target.value)}
                          placeholder={t.createJournal.lineDescriptionPlaceholder}
                          className="input text-xs"
                        />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          type="button"
                          disabled={lines.length <= 2}
                          onClick={() => removeLine(idx)}
                          aria-label={`${t.createJournal.removeLine} ${idx + 1}`}
                          className="btn-icon h-9 w-9 hover:bg-danger-soft hover:text-danger"
                        >
                          <Trash2 aria-hidden className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Mobile stacked */}
              <div className="divide-y divide-border-subtle sm:hidden">
                {lines.map((line, idx) => (
                  <div key={idx} className="space-y-3 p-4">
                    <div className="flex items-center justify-between">
                      <span className="overline">
                        {t.common.line} #{idx + 1}
                      </span>
                      <button
                        type="button"
                        disabled={lines.length <= 2}
                        onClick={() => removeLine(idx)}
                        className="btn btn-danger-ghost btn-sm"
                      >
                        <Trash2 aria-hidden className="h-3 w-3" />
                        {t.createJournal.removeLine}
                      </button>
                    </div>

                    <div>
                      <span className="field-label">{t.common.account}</span>
                      {renderAccountButton(line, idx)}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label htmlFor={`${formId}-debit-${idx}`} className="field-label">
                          {t.createJournal.debit}
                        </label>
                        <input
                          {...amountInputProps}
                          id={`${formId}-debit-${idx}`}
                          value={line.debit}
                          onChange={(e) => handleLineChange(idx, 'debit', e.target.value)}
                        />
                      </div>
                      <div>
                        <label htmlFor={`${formId}-credit-${idx}`} className="field-label">
                          {t.createJournal.credit}
                        </label>
                        <input
                          {...amountInputProps}
                          id={`${formId}-credit-${idx}`}
                          value={line.credit}
                          onChange={(e) => handleLineChange(idx, 'credit', e.target.value)}
                        />
                      </div>
                    </div>

                    <div>
                      <label htmlFor={`${formId}-desc-${idx}`} className="field-label">
                        {t.createJournal.lineDescription}
                      </label>
                      <input
                        id={`${formId}-desc-${idx}`}
                        type="text"
                        value={line.description}
                        onChange={(e) => handleLineChange(idx, 'description', e.target.value)}
                        placeholder={t.createJournal.lineDescriptionPlaceholder}
                        className="input text-xs"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </form>

        <aside className="flex w-full flex-col overflow-y-auto border-t border-border bg-surface-muted p-5 lg:w-[360px] lg:flex-shrink-0 lg:border-s lg:border-t-0 xl:w-[400px]">
          <JournalAssistantPanel
            accounts={accounts}
            companyId={companyId ?? 0}
            onApplySuggestion={handleApplySuggestion}
          />
        </aside>
      </Modal>

      <AccountPickerModal
        isOpen={pickerLineIndex !== null}
        accounts={accounts}
        selectedAccountId={pickerLineIndex !== null ? (lines[pickerLineIndex]?.account_id ?? null) : null}
        lineIndex={pickerLineIndex ?? 0}
        onSelect={handleAccountSelect}
        onClose={() => setPickerLineIndex(null)}
      />

      <Modal
        isOpen={showReplaceConfirm}
        onClose={() => {
          setShowReplaceConfirm(false);
          setPendingSuggestion(null);
        }}
        title={t.journals.assistantReplaceExistingLines}
        footer={
          <>
            <button
              type="button"
              onClick={() => {
                setShowReplaceConfirm(false);
                setPendingSuggestion(null);
              }}
              className="btn btn-ghost btn-sm"
            >
              {t.common.cancel}
            </button>
            <button
              type="button"
              onClick={() => {
                if (pendingSuggestion) {
                  applySuggestionDirectly(pendingSuggestion);
                }
                setShowReplaceConfirm(false);
                setPendingSuggestion(null);
              }}
              className="btn btn-danger btn-sm"
            >
              {t.common.confirm}
            </button>
          </>
        }
      >
        <p className="text-sm text-muted-foreground">{t.journals.assistantReplaceConfirm}</p>
      </Modal>
    </>
  );
}
