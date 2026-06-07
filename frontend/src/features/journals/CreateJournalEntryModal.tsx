import { useState, useEffect, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, Trash2, CheckCircle2, AlertCircle, ChevronDown, Search, Save } from 'lucide-react';
import { useAccounts } from '../accounts/useAccounts';
import { useCreateJournalEntry } from './useCreateJournalEntry';
import { formatCurrency as fmtCurrency } from '../../lib/format';
import AccountTypeBadge from '../accounts/AccountTypeBadge';

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

export default function CreateJournalEntryModal({ isOpen, onClose, onSuccess, companyId }: CreateJournalEntryModalProps) {
  // ── Hooks ──
  const { accounts, fetchAccounts } = useAccounts({ companyId, skip: 0, limit: 500 });
  const { createJournalEntry, isSubmitting, submitError, setSubmitError } = useCreateJournalEntry();

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
  const [entryDate, setEntryDate] = useState('2026-01-15');
  const [description, setDescription] = useState('');
  const [sourceType] = useState('manual');
  const [sourceId] = useState('FRONTEND');

  // Initialize entry no when modal opens
  useEffect(() => {
    if (isOpen) {
      setEntryNo(generateDefaultEntryNo());
      setEntryDate('2026-01-15');
      setDescription('');
      setLines([
        { account_id: null, debit: '', credit: '', description: '' },
        { account_id: null, debit: '', credit: '', description: '' },
      ]);
      setSubmitError(null);
      setDropdownCoords(null);
    }
  }, [isOpen, setSubmitError]);

  // ── Lines State ──
  const [lines, setLines] = useState<LineState[]>([
    { account_id: null, debit: '', credit: '', description: '' },
    { account_id: null, debit: '', credit: '', description: '' },
  ]);

  // Dropdown controls for rows
  const [activeRowDropdown, setActiveRowDropdown] = useState<number | null>(null);
  const [accountSearchQuery, setAccountSearchQuery] = useState('');
  const [dropdownCoords, setDropdownCoords] = useState<{ top: number; left: number; width: number } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const handleDropdownToggle = (index: number, event: React.MouseEvent<HTMLButtonElement>) => {
    if (activeRowDropdown === index) {
      setActiveRowDropdown(null);
      setDropdownCoords(null);
    } else {
      setActiveRowDropdown(index);
      const rect = event.currentTarget.getBoundingClientRect();
      setDropdownCoords({
        top: rect.bottom,
        left: rect.left,
        width: rect.width,
      });
    }
  };



  // Load accounts when modal opens or company changes
  useEffect(() => {
    if (isOpen && companyId) {
      fetchAccounts();
    }
  }, [isOpen, companyId, fetchAccounts]);

  // Click outside to close active dropdown selector
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as HTMLElement;
      if (target.closest('[data-portal-dropdown="true"]')) {
        return;
      }
      if (target.closest('.account-select-trigger')) {
        return;
      }
      setActiveRowDropdown(null);
      setDropdownCoords(null);
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Window resize & Escape key listener
  useEffect(() => {
    const handleClose = () => {
      setActiveRowDropdown(null);
      setDropdownCoords(null);
    };

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        handleClose();
      }
    }

    if (activeRowDropdown !== null) {
      window.addEventListener('resize', handleClose);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      window.removeEventListener('resize', handleClose);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeRowDropdown]);

  // Clear search on switching active row dropdown
  useEffect(() => {
    setAccountSearchQuery('');
    if (activeRowDropdown === null) {
      setDropdownCoords(null);
    }
  }, [activeRowDropdown]);

  // ── Filtered accounts for searchable combobox ──
  const filteredAccounts = useMemo(() => {
    const q = accountSearchQuery.toLowerCase().trim();
    // Filter out inactive accounts
    const activeAccounts = accounts.filter((a) => a.is_active);
    if (!q) return activeAccounts;
    return activeAccounts.filter(
      (a) =>
        a.code.toLowerCase().includes(q) ||
        a.name.toLowerCase().includes(q) ||
        a.account_type.toLowerCase().includes(q),
    );
  }, [accounts, accountSearchQuery]);

  // ── Handlers ──
  const addLine = () => {
    setLines([...lines, { account_id: null, debit: '', credit: '', description: '' }]);
  };

  const removeLine = (index: number) => {
    if (lines.length <= 2) return;
    setLines(lines.filter((_, i) => i !== index));
    if (activeRowDropdown === index) {
      setActiveRowDropdown(null);
    }
  };

  const handleLineChange = (index: number, field: keyof LineState, value: string | number | null) => {
    setLines(
      lines.map((line, i) => {
        if (i !== index) return line;
        const updated = { ...line, [field]: value };
        
        // If debit is typed, clear credit, and vice-versa
        if (field === 'debit' && value !== '') {
          updated.credit = '';
        } else if (field === 'credit' && value !== '') {
          updated.debit = '';
        }
        
        return updated;
      }),
    );
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
      errors.push('At least 2 lines are required.');
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
      errors.push('All lines must have an account selected.');
    }
    if (hasBothDebitAndCredit) {
      errors.push('A line cannot contain both debit and credit.');
    }
    if (hasNeitherDebitNorCredit) {
      errors.push('Every line must contain either a debit or credit.');
    }
    if (totals.debit <= 0) {
      errors.push('Total debited amount must be greater than 0.');
    }
    if (Math.abs(totals.debit - totals.credit) >= 0.005) {
      errors.push(`Debits and Credits are unbalanced (Diff: ${fmtCurrency(totals.difference)}).`);
    }

    return errors;
  }, [lines, totals]);

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

  const renderDropdownPortal = (idx: number) => {
    if (activeRowDropdown !== idx || !dropdownCoords) return null;

    const style: React.CSSProperties = {
      position: 'fixed',
      top: `${dropdownCoords.top + 4}px`,
      left: `${dropdownCoords.left}px`,
      width: `${dropdownCoords.width}px`,
      zIndex: 9999,
    };

    return createPortal(
      <AnimatePresence>
        <motion.div
          data-portal-dropdown="true"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.15 }}
          style={style}
          className="rounded-xl bg-surface-800 border border-white/[0.08] shadow-2xl shadow-black/80 flex flex-col overflow-hidden max-h-[220px]"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="relative p-2 bg-surface-900 border-b border-white/[0.06]">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
            <input
              type="text"
              placeholder="Search accounts..."
              value={accountSearchQuery}
              onChange={(e) => setAccountSearchQuery(e.target.value)}
              className="w-full pl-7 pr-3 py-1 bg-white/[0.03] border border-white/[0.06] rounded-lg text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-brand-500/50"
              autoFocus
            />
          </div>
          <div className="flex-1 overflow-y-auto py-1 divide-y divide-white/[0.02] max-h-[160px]">
            {filteredAccounts.length === 0 ? (
              <div className="px-3 py-4 text-center text-xs text-gray-500">No active accounts matched</div>
            ) : (
              filteredAccounts.map((acc) => (
                <button
                  key={acc.id}
                  type="button"
                  onClick={() => {
                    handleLineChange(idx, 'account_id', acc.id);
                    setActiveRowDropdown(null);
                    setDropdownCoords(null);
                  }}
                  className="w-full flex items-center justify-between gap-3 px-3 py-2 text-left text-xs transition-colors hover:bg-white/[0.04]"
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className="font-mono text-brand-400 font-semibold">{acc.code}</span>
                    <span className="text-gray-200 truncate">{acc.name}</span>
                  </div>
                  <AccountTypeBadge type={acc.account_type} />
                </button>
              ))
            )}
          </div>
        </motion.div>
      </AnimatePresence>,
      document.body
    );
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Overlay backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 15 }}
            transition={{ duration: 0.3 }}
            className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl bg-surface-900 border border-white/[0.08] shadow-2xl overflow-hidden z-10"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] bg-surface-800/40">
              <div>
                <h3 className="text-lg font-bold text-white">New Journal Entry</h3>
                <p className="text-xs text-gray-400">Create a new draft journal entry. Double-entry balances are verified on submit.</p>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/[0.06] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable Form Body */}
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Top fields */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1.5">Entry No</label>
                  <input
                    type="text"
                    required
                    value={entryNo}
                    onChange={(e) => setEntryNo(e.target.value)}
                    className="input-field text-sm"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1.5">Entry Date</label>
                  <input
                    type="date"
                    required
                    value={entryDate}
                    onChange={(e) => setEntryDate(e.target.value)}
                    className="input-field text-sm"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1.5">Description</label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Enter journal description..."
                    className="input-field text-sm"
                  />
                </div>
              </div>

              {/* Source (Subtle hidden / metadata values display) */}
              <div className="flex gap-4 p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="text-[11px] text-gray-500">
                  <span className="font-semibold text-gray-400 uppercase tracking-wider">Source Type:</span> {sourceType}
                </div>
                <div className="text-[11px] text-gray-500 border-l border-white/[0.06] pl-4">
                  <span className="font-semibold text-gray-400 uppercase tracking-wider">Source ID:</span> {sourceId}
                </div>
              </div>

              {/* Error messages */}
              {(submitError || (validationErrors.length > 0 && lines.some((l) => l.account_id))) && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs space-y-1">
                  {submitError && (
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold">Submission Error:</span> {submitError}
                      </div>
                    </div>
                  )}
                  {!submitError && validationErrors.length > 0 && (
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold">Validation Warnings:</span>
                        <ul className="list-disc pl-4 mt-1 space-y-1">
                          {validationErrors.map((err, idx) => (
                            <li key={idx}>{err}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Lines table / form */}
              <div ref={dropdownRef}>
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2.5">
                    <h4 className="text-xs uppercase tracking-wider text-gray-400 font-bold">Journal Lines</h4>
                    <span className="hidden md:inline-flex items-center gap-1 text-[10px] text-gray-500">
                      <AlertCircle className="w-3 h-3 text-gray-500" />
                      Each line can contain either a debit or a credit amount, not both.
                    </span>
                  </div>
                  
                  {/* Mobile-only note */}
                  <span className="md:hidden flex items-center gap-1 text-[10px] text-gray-500">
                    <AlertCircle className="w-3 h-3 text-gray-500" />
                    Each line can contain either a debit or a credit, not both.
                  </span>

                  <button
                    type="button"
                    onClick={addLine}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-brand-400 hover:text-brand-300 border border-brand-500/20 hover:border-brand-500/40 bg-brand-500/5 transition-all self-start sm:self-auto"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add Line
                  </button>
                </div>

                <div className="border border-white/[0.06] rounded-xl bg-white/[0.01] overflow-visible">
                  {/* Desktop view */}
                  <table className="w-full text-left border-collapse hidden sm:table">
                    <thead>
                      <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                        <th className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Account</th>
                        <th className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3 w-[140px] text-right">Debit</th>
                        <th className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3 w-[140px] text-right">Credit</th>
                        <th className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3">Line Description</th>
                        <th className="text-center text-[10px] uppercase tracking-wider font-semibold text-gray-500 px-4 py-3 w-[50px]">Delete</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {lines.map((line, idx) => {
                        const selectedAcc = accounts.find((a) => a.id === line.account_id);
                        const isDropdownOpen = activeRowDropdown === idx;

                        return (
                          <tr key={idx} className="hover:bg-white/[0.01] transition-colors align-top">
                            {/* Account Select Cell */}
                            <td className={`px-4 py-3 relative min-w-[240px] ${isDropdownOpen ? 'z-50' : 'z-0'}`}>
                              <button
                                type="button"
                                onClick={(e) => handleDropdownToggle(idx, e)}
                                className="account-select-trigger w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-surface-800/60 border border-white/[0.08] hover:border-white/[0.12] text-left transition-all h-[38px] text-xs"
                              >
                                {selectedAcc ? (
                                  <div className="flex items-center gap-2 truncate">
                                    <span className="font-mono text-brand-400 font-semibold">{selectedAcc.code}</span>
                                    <span className="text-gray-200 truncate">{selectedAcc.name}</span>
                                  </div>
                                ) : (
                                  <span className="text-gray-500">Select account...</span>
                                )}
                                <ChevronDown className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                              </button>

                              {renderDropdownPortal(idx)}
                            </td>

                            {/* Debit input */}
                            <td className="px-4 py-3">
                              <input
                                type="number"
                                step="any"
                                min="0"
                                value={line.debit}
                                onChange={(e) => handleLineChange(idx, 'debit', e.target.value)}
                                placeholder="0.00"
                                className="input-field text-right text-xs py-2 px-3 h-[38px] font-mono"
                              />
                            </td>

                            {/* Credit input */}
                            <td className="px-4 py-3">
                              <input
                                type="number"
                                step="any"
                                min="0"
                                value={line.credit}
                                onChange={(e) => handleLineChange(idx, 'credit', e.target.value)}
                                placeholder="0.00"
                                className="input-field text-right text-xs py-2 px-3 h-[38px] font-mono"
                              />
                            </td>

                            {/* Line Description input */}
                            <td className="px-4 py-3">
                              <input
                                type="text"
                                value={line.description}
                                onChange={(e) => handleLineChange(idx, 'description', e.target.value)}
                                placeholder="Line explanation (optional)"
                                className="input-field text-xs py-2 px-3 h-[38px]"
                              />
                            </td>

                            {/* Action delete */}
                            <td className="px-4 py-3 text-center">
                              <button
                                type="button"
                                disabled={lines.length <= 2}
                                onClick={() => removeLine(idx)}
                                className="p-2 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/[0.06] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-colors mt-0.5"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  {/* Mobile stacked view */}
                  <div className="sm:hidden divide-y divide-white/[0.06] p-4 space-y-4">
                    {lines.map((line, idx) => {
                      const selectedAcc = accounts.find((a) => a.id === line.account_id);
                      const isDropdownOpen = activeRowDropdown === idx;

                      return (
                        <div key={idx} className="space-y-3 pt-4 first:pt-0">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Line #{idx + 1}</span>
                            <button
                              type="button"
                              disabled={lines.length <= 2}
                              onClick={() => removeLine(idx)}
                              className="inline-flex items-center gap-1 text-[10px] text-red-500 uppercase tracking-wider font-semibold disabled:opacity-40"
                            >
                              <Trash2 className="w-3 h-3" />
                              Remove
                            </button>
                          </div>

                          {/* Account */}
                          <div className={`relative ${isDropdownOpen ? 'z-50' : 'z-0'}`}>
                            <label className="block text-[9px] uppercase tracking-wider text-gray-500 mb-1">Account</label>
                            <button
                              type="button"
                              onClick={(e) => handleDropdownToggle(idx, e)}
                              className="account-select-trigger w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-surface-800/60 border border-white/[0.08] hover:border-white/[0.12] text-left transition-all h-[38px] text-xs"
                            >
                              {selectedAcc ? (
                                <div className="flex items-center gap-2 truncate">
                                  <span className="font-mono text-brand-400 font-semibold">{selectedAcc.code}</span>
                                  <span className="text-gray-200 truncate">{selectedAcc.name}</span>
                                </div>
                              ) : (
                                <span className="text-gray-500">Select account...</span>
                              )}
                              <ChevronDown className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                            </button>

                            {renderDropdownPortal(idx)}
                          </div>

                          {/* Debit / Credit Row */}
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-[9px] uppercase tracking-wider text-gray-500 mb-1">Debit</label>
                              <input
                                type="number"
                                step="any"
                                min="0"
                                value={line.debit}
                                onChange={(e) => handleLineChange(idx, 'debit', e.target.value)}
                                placeholder="0.00"
                                className="input-field text-right text-xs py-2 px-3 h-[38px] font-mono"
                              />
                            </div>
                            <div>
                              <label className="block text-[9px] uppercase tracking-wider text-gray-500 mb-1">Credit</label>
                              <input
                                type="number"
                                step="any"
                                min="0"
                                value={line.credit}
                                onChange={(e) => handleLineChange(idx, 'credit', e.target.value)}
                                placeholder="0.00"
                                className="input-field text-right text-xs py-2 px-3 h-[38px] font-mono"
                              />
                            </div>
                          </div>

                          {/* Line Description */}
                          <div>
                            <label className="block text-[9px] uppercase tracking-wider text-gray-500 mb-1">Line Description</label>
                            <input
                              type="text"
                              value={line.description}
                              onChange={(e) => handleLineChange(idx, 'description', e.target.value)}
                              placeholder="Description..."
                              className="input-field text-xs py-2 px-3 h-[38px]"
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </form>

            {/* Sticky Bottom Footer: Metrics and Save Action */}
            <div className="px-6 py-4 border-t border-white/[0.06] bg-surface-800/40 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              {/* Summary panel */}
              <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
                <div>
                  <span className="text-gray-500 uppercase tracking-wider font-semibold text-[10px]">Total Dr:</span>
                  <span className="text-emerald-400 font-bold ml-1.5">{fmtCurrency(totals.debit)}</span>
                </div>
                <div className="border-l border-white/[0.06] pl-4">
                  <span className="text-gray-500 uppercase tracking-wider font-semibold text-[10px]">Total Cr:</span>
                  <span className="text-red-400 font-bold ml-1.5">{fmtCurrency(totals.credit)}</span>
                </div>
                <div className="border-l border-white/[0.06] pl-4">
                  <span className="text-gray-500 uppercase tracking-wider font-semibold text-[10px]">Diff:</span>
                  <span className={`font-bold ml-1.5 ${totals.difference > 0 ? 'text-amber-400' : 'text-gray-400'}`}>
                    {fmtCurrency(totals.difference)}
                  </span>
                </div>
                <div className="border-l border-white/[0.06] pl-4">
                  {totals.isBalanced ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-semibold uppercase tracking-wider">
                      <CheckCircle2 className="w-3 h-3" />
                      Balanced
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-[10px] font-semibold uppercase tracking-wider">
                      <AlertCircle className="w-3 h-3" />
                      Unbalanced
                    </span>
                  )}
                </div>
              </div>

              {/* Submit actions */}
              <div className="flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-sm font-medium text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!isValid || isSubmitting}
                  onClick={handleSubmit}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-brand-500/20 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none transition-all active:scale-[0.98]"
                >
                  {isSubmitting ? (
                    <span>Saving...</span>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      <span>Save Draft</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
