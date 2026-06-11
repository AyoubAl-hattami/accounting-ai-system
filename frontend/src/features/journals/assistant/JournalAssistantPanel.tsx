import { useState } from 'react';
import { useI18n } from '../../../i18n';
import { Sparkles, AlertTriangle, CheckCircle2, AlertCircle } from 'lucide-react';
import { suggestJournalEntry } from './journalAssistantRules';
import type { Account, JournalAssistantSuggestion } from './types';

interface JournalAssistantPanelProps {
  accounts: Account[];
  onApplySuggestion: (suggestion: {
    debitAccountId?: number;
    creditAccountId?: number;
    amount?: number;
    description: string;
  }) => void;
}

export default function JournalAssistantPanel({ accounts, onApplySuggestion }: JournalAssistantPanelProps) {
  const { t, language, dir } = useI18n();
  const [description, setDescription] = useState('');
  const [suggestion, setSuggestion] = useState<JournalAssistantSuggestion | null>(null);

  const handleSuggest = () => {
    if (!description.trim()) return;
    const result = suggestJournalEntry({
      description,
      accounts,
      language,
    });
    setSuggestion(result);
  };

  const handleClear = () => {
    setDescription('');
    setSuggestion(null);
  };

  const handleApply = () => {
    if (!suggestion) return;
    onApplySuggestion({
      debitAccountId: suggestion.debitAccountId,
      creditAccountId: suggestion.creditAccountId,
      amount: suggestion.amount,
      description: description.trim(),
    });
  };

  const getConfidenceBadgeColor = (confidence: 'high' | 'medium' | 'low') => {
    switch (confidence) {
      case 'high':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'medium':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'low':
      default:
        return 'bg-red-500/10 text-red-400 border-red-500/20';
    }
  };

  const getConfidenceLabel = (confidence: 'high' | 'medium' | 'low') => {
    switch (confidence) {
      case 'high':
        return t.journals.assistantHigh || 'High';
      case 'medium':
        return t.journals.assistantMedium || 'Medium';
      case 'low':
      default:
        return t.journals.assistantLow || 'Low';
    }
  };

  // Find account name and code for display
  const debitAccount = suggestion?.debitAccountId
    ? accounts.find((a) => a.id === suggestion.debitAccountId)
    : null;
  const creditAccount = suggestion?.creditAccountId
    ? accounts.find((a) => a.id === suggestion.creditAccountId)
    : null;

  return (
    <div className="glass-panel border border-white/[0.08] rounded-2xl bg-surface-900/60 backdrop-blur-md p-5 flex flex-col gap-4 h-full">
      {/* Title */}
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded-lg bg-brand-500/10 border border-brand-500/20">
          <Sparkles className="w-4 h-4 text-brand-400" />
        </div>
        <div>
          <h4 className="text-sm font-bold text-white leading-tight">
            {t.journals.assistantTitle || 'AI Journal Assistant'}
          </h4>
          <p className="text-[11px] text-gray-500 mt-0.5">
            {t.journals.assistantSubtitle || 'Describe the transaction and get a suggested debit/credit entry.'}
          </p>
        </div>
      </div>

      {/* Input Textarea */}
      <div className="flex flex-col gap-1.5">
        <textarea
          dir={dir}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t.journals.assistantPlaceholder || 'Example: Paid rent from bank for 1000'}
          rows={3}
          className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-xl text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-brand-500/50 transition-colors resize-none leading-relaxed"
        />
        <div className="flex items-center justify-end gap-2">
          {description && (
            <button
              type="button"
              onClick={handleClear}
              className="px-2.5 py-1.5 rounded-lg text-[11px] font-semibold text-gray-400 hover:text-gray-200 hover:bg-white/[0.04] transition-colors"
            >
              {t.journals.assistantClear || 'Clear'}
            </button>
          )}
          <button
            type="button"
            disabled={!description.trim()}
            onClick={handleSuggest}
            className="inline-flex items-center gap-1 px-3 py-1.5 bg-brand-500/10 hover:bg-brand-500/20 disabled:hover:bg-brand-500/5 disabled:opacity-40 border border-brand-500/20 hover:border-brand-500/30 text-brand-400 hover:text-brand-300 text-xs font-semibold rounded-lg transition-all active:scale-[0.98]"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{t.journals.assistantSuggest || 'Suggest Entry'}</span>
          </button>
        </div>
      </div>

      {/* Suggestion Result Box */}
      {suggestion && (
        <div className="flex-1 flex flex-col gap-3.5 border-t border-white/[0.06] pt-4 overflow-y-auto">
          {/* Header with intent and confidence */}
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400 font-medium">
              {t.journals.assistantConfidence || 'Confidence'}:
            </span>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${getConfidenceBadgeColor(suggestion.confidence)}`}>
              {getConfidenceLabel(suggestion.confidence)}
            </span>
          </div>

          {suggestion.detectedIntent === 'unknown' ? (
            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-gray-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-gray-400 leading-normal">
                {t.journals.assistantNoSuggestion || 'Could not generate a suggestion. Try describing the transaction with keywords like "paid", "received", "bought", etc.'}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {/* Debit/Credit details */}
              <div className="grid grid-cols-2 gap-2.5">
                {/* Debit suggestion */}
                <div className="p-3 rounded-xl bg-emerald-500/[0.03] border border-emerald-500/10 flex flex-col gap-1 min-w-0">
                  <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                    {t.journals.assistantDebit || 'Suggested Debit'}
                  </span>
                  {debitAccount ? (
                    <div className="truncate text-xs font-medium text-gray-200" title={`${debitAccount.code} - ${debitAccount.name}`}>
                      <span className="font-mono text-brand-400 font-semibold block sm:inline mr-1">{debitAccount.code}</span>
                      {debitAccount.name}
                    </div>
                  ) : (
                    <span className="text-xs text-red-400 italic">
                      {t.common.error || 'Error'}
                    </span>
                  )}
                </div>

                {/* Credit suggestion */}
                <div className="p-3 rounded-xl bg-red-500/[0.03] border border-red-500/10 flex flex-col gap-1 min-w-0">
                  <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">
                    {t.journals.assistantCredit || 'Suggested Credit'}
                  </span>
                  {creditAccount ? (
                    <div className="truncate text-xs font-medium text-gray-200" title={`${creditAccount.code} - ${creditAccount.name}`}>
                      <span className="font-mono text-brand-400 font-semibold block sm:inline mr-1">{creditAccount.code}</span>
                      {creditAccount.name}
                    </div>
                  ) : (
                    <span className="text-xs text-red-400 italic">
                      {t.common.error || 'Error'}
                    </span>
                  )}
                </div>
              </div>

              {/* Amount display */}
              {suggestion.amount !== undefined && (
                <div className="px-3 py-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between text-xs">
                  <span className="text-gray-400">{t.journals.assistantAmount || 'Amount'}:</span>
                  <span className="font-mono font-bold text-white text-sm">
                    {suggestion.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              )}

              {/* Accounting Explanation */}
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold tracking-wider text-gray-500">
                  {t.journals.assistantExplanation || 'Explanation'}
                </span>
                <p className="text-xs text-gray-300 leading-normal">
                  {suggestion.explanation}
                </p>
              </div>

              {/* Warnings display */}
              {suggestion.warnings.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs space-y-1.5">
                  <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[10px]">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                    <span>{t.journals.assistantWarnings || 'Warnings'}</span>
                  </div>
                  <ul className="list-disc pl-4 space-y-0.5 leading-normal">
                    {suggestion.warnings.map((warn, index) => (
                      <li key={index}>{warn}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Disclaimer */}
              <p className="text-[10px] text-gray-500 italic text-center leading-normal">
                {t.journals.assistantReviewDisclaimer || 'Review all suggestions before creating the entry.'}
              </p>

              {/* Apply Button */}
              <button
                type="button"
                onClick={handleApply}
                disabled={!suggestion.debitAccountId || !suggestion.creditAccountId}
                className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-xs font-semibold rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-[0.98] mt-1"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{t.journals.assistantApply || 'Apply Suggestion'}</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
