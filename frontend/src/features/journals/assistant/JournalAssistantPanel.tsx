import { useState } from 'react';
import { useI18n } from '../../../i18n';
import { Sparkles, AlertTriangle, CheckCircle2, AlertCircle, Loader2, Info, Server, Cpu, Activity, Zap } from 'lucide-react';
import { useJournalSuggestion } from './useJournalSuggestion';
import { useAiStatus } from './useAiStatus';
import type { Account } from './types';

interface JournalAssistantPanelProps {
  accounts: Account[];
  companyId: number;
  onApplySuggestion: (suggestion: {
    debitAccountId?: number;
    creditAccountId?: number;
    amount?: number;
    description: string;
  }) => void;
}

export default function JournalAssistantPanel({ accounts, companyId, onApplySuggestion }: JournalAssistantPanelProps) {
  const { t, language, dir } = useI18n();
  const [description, setDescription] = useState('');
  const { suggest, suggestion, isLoading, source, clear: clearSuggestion } = useJournalSuggestion();
  const { status: aiStatus, error: aiStatusError } = useAiStatus();

  const handleSuggest = () => {
    if (!description.trim()) return;
    suggest(description, accounts, language, companyId);
  };

  const handleClear = () => {
    setDescription('');
    clearSuggestion();
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

  const getConfidenceTone = (confidence: 'high' | 'medium' | 'low') => {
    switch (confidence) {
      case 'high':
        return 'tone-success';
      case 'medium':
        return 'tone-warning';
      case 'low':
      default:
        return 'tone-danger';
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
    <div className="card flex h-full flex-col gap-4 p-5">
      {/* Title */}
      <div className="flex items-center gap-2.5">
        <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border border-primary-border bg-primary-soft">
          <Sparkles aria-hidden className="h-4 w-4 text-primary" />
        </span>
        <div className="min-w-0">
          <h4 className="text-sm font-semibold leading-tight text-foreground">
            {t.journals.assistantTitle || 'AI Journal Assistant'}
          </h4>
          <p className="mt-0.5 text-[11px] text-subtle-foreground">
            {t.journals.assistantSubtitle || 'Describe the transaction and get a suggested debit/credit entry.'}
          </p>
        </div>
      </div>

      {/* AI Mode Badge */}
      <div className="flex items-center gap-1.5 rounded-lg border border-border-subtle bg-surface-muted px-3 py-1.5">
        <Activity aria-hidden className="h-3 w-3 flex-shrink-0 text-subtle-foreground" />
        <span className="text-[10px] text-subtle-foreground">
          {t.journals.aiMode || 'AI mode'}:
        </span>
        {aiStatusError ? (
          <span className="text-[10px] text-subtle-foreground italic">
            {t.journals.aiStatusUnavailable || 'AI status unavailable'}
          </span>
        ) : aiStatus ? (
          <span className={`text-[10px] font-semibold ${aiStatus.llm_enabled ? 'text-violet' : 'text-teal'}`}>
            {aiStatus.journal_provider === 'rules'
              ? (t.journals.backendRules || 'Backend rules')
              : aiStatus.journal_provider === 'openai'
                ? (aiStatus.llm_enabled
                  ? (t.journals.openaiActive || 'OpenAI')
                  : (t.journals.openaiRulesFallback || 'OpenAI fallback'))
                : aiStatus.journal_provider === 'gemini'
                  ? (aiStatus.llm_enabled
                    ? (t.journals.geminiActive || 'Gemini')
                    : (t.journals.geminiRulesFallback || 'Gemini fallback'))
                  : aiStatus.journal_provider === 'llm_placeholder'
                    ? (t.journals.rulesFallback || 'Rules fallback')
                    : aiStatus.journal_provider}
          </span>
        ) : (
          <span className="text-[10px] text-subtle-foreground animate-pulse">...</span>
        )}
      </div>

      {/* Example Prompt Chips */}
      {!suggestion && (
        <div className="flex flex-wrap gap-1.5">
          {(language === 'ar'
            ? [
                'تم دفع الإيجار من البنك بمبلغ 1000',
                'تم استلام إيراد مبيعات 2500 في البنك',
                'استثمر المالك 5000 في البنك',
                'تم شراء معدات من البنك بمبلغ 1200',
              ]
            : [
                'Paid rent from bank for 1000',
                'Received sales income 2500 into bank',
                'Owner invested 5000 into bank',
                'Bought equipment from bank for 1200',
              ]
          ).map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setDescription(example)}
              className="btn btn-secondary btn-sm max-w-[200px] truncate text-[10px]"
              title={example}
            >
              {example}
            </button>
          ))}
        </div>
      )}

      {/* Input Textarea */}
      <div className="flex flex-col gap-1.5">
        <textarea
          dir={dir}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t.journals.assistantPlaceholder || 'Example: Paid rent from bank for 1000'}
          rows={3}
          className="input resize-none text-xs leading-relaxed"
        />
        <div className="flex items-center justify-end gap-2">
          {description && (
            <button type="button" onClick={handleClear} className="btn btn-ghost btn-sm">
              {t.journals.assistantClear || 'Clear'}
            </button>
          )}
          <button
            type="button"
            disabled={!description.trim() || isLoading}
            onClick={handleSuggest}
            className="btn btn-tone tone-primary btn-sm"
          >
            {isLoading ? (
              <>
                <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" />
                <span>{t.journals.assistantLoading || 'Analyzing...'}</span>
              </>
            ) : (
              <>
                <Sparkles aria-hidden className="h-3.5 w-3.5" />
                <span>{t.journals.assistantSuggest || 'Suggest Entry'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Suggestion Result Box */}
      {suggestion && (
        <div className="flex-1 flex flex-col gap-3.5 border-t border-border pt-4 overflow-y-auto">
          {/* Header with confidence and source */}
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground font-medium">
              {t.journals.assistantConfidence || 'Confidence'}:
            </span>
            <div className="flex items-center gap-2">
              {/* Source Badge */}
              {source === 'backend_rules' && (
                <span className="badge tone-teal">
                  <Server aria-hidden className="h-2.5 w-2.5" />
                  {t.journals.assistantSourceBackend || 'Backend rules'}
                </span>
              )}
              {source === 'local_fallback' && (
                <span className="badge tone-warning">
                  <Cpu aria-hidden className="h-2.5 w-2.5" />
                  {t.journals.assistantSourceLocal || 'Local fallback'}
                </span>
              )}
              {source === 'openai' && (
                <span className="badge tone-violet">
                  <Zap aria-hidden className="h-2.5 w-2.5" />
                  {t.journals.openaiActive || 'OpenAI'}
                </span>
              )}
              {source === 'openai_fallback_rules' && (
                <span className="badge tone-warning">
                  <Zap aria-hidden className="h-2.5 w-2.5" />
                  {t.journals.openaiRulesFallback || 'OpenAI fallback'}
                </span>
              )}
              {source === 'gemini' && (
                <span className="badge tone-violet">
                  <Zap aria-hidden className="h-2.5 w-2.5" />
                  {t.journals.geminiActive || 'Gemini'}
                </span>
              )}
              {source === 'gemini_fallback_rules' && (
                <span className="badge tone-warning">
                  <Zap aria-hidden className="h-2.5 w-2.5" />
                  {t.journals.geminiRulesFallback || 'Gemini fallback'}
                </span>
              )}
              {/* Confidence Badge */}
              <span className={`badge ${getConfidenceTone(suggestion.confidence)}`}>
                {getConfidenceLabel(suggestion.confidence)}
              </span>
            </div>
          </div>

          {/* Local fallback warning */}
          {source === 'local_fallback' && (
            <div className="callout tone-warning text-[11px]">
              <Info aria-hidden className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
              <span className="min-w-0 flex-1">{t.journals.assistantFallbackWarning || 'Using local fallback suggestions.'}</span>
            </div>
          )}
          {(source === 'gemini_fallback_rules' || source === 'openai_fallback_rules') && (
            <div className="callout tone-warning text-[11px]">
              <Info aria-hidden className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
              <span className="min-w-0 flex-1">{t.journals.assistantBackendFallbackWarning || 'AI provider unavailable. Using backend rules fallback.'}</span>
            </div>
          )}

          {suggestion.detectedIntent === 'unknown' ? (
            <div className="flex items-start gap-2 rounded-lg border border-border-subtle bg-surface-muted p-3">
              <AlertCircle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0 text-subtle-foreground" />
              <p className="text-xs leading-normal text-muted-foreground">
                {t.journals.assistantNoSuggestion || 'Could not generate a suggestion. Try describing the transaction with keywords like "paid", "received", "bought", etc.'}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {/* Debit/Credit details */}
              <div className="grid grid-cols-2 gap-2.5">
                {/* Debit suggestion */}
                <div className="flex min-w-0 flex-col gap-1 rounded-lg border border-border-subtle bg-surface-muted p-3 border-s-2 border-s-debit">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-debit">
                    {t.journals.assistantDebit || 'Suggested Debit'}
                  </span>
                  {debitAccount ? (
                    <div className="truncate text-xs font-medium text-foreground" title={`${debitAccount.code} - ${debitAccount.name}`}>
                      <span className="numeric me-1 block font-semibold text-primary sm:inline">{debitAccount.code}</span>
                      {debitAccount.name}
                    </div>
                  ) : (
                    <span className="text-xs italic text-danger">
                      {t.common.error || 'Error'}
                    </span>
                  )}
                </div>

                {/* Credit suggestion */}
                <div className="flex min-w-0 flex-col gap-1 rounded-lg border border-border-subtle bg-surface-muted p-3 border-s-2 border-s-credit">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-credit">
                    {t.journals.assistantCredit || 'Suggested Credit'}
                  </span>
                  {creditAccount ? (
                    <div className="truncate text-xs font-medium text-foreground" title={`${creditAccount.code} - ${creditAccount.name}`}>
                      <span className="numeric me-1 block font-semibold text-primary sm:inline">{creditAccount.code}</span>
                      {creditAccount.name}
                    </div>
                  ) : (
                    <span className="text-xs italic text-danger">
                      {t.common.error || 'Error'}
                    </span>
                  )}
                </div>
              </div>

              {/* Amount display */}
              {suggestion.amount !== undefined && (
                <div className="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-muted px-3 py-2.5 text-xs">
                  <span className="text-muted-foreground">{t.journals.assistantAmount || 'Amount'}:</span>
                  <span className="numeric text-sm font-semibold text-foreground">
                    {suggestion.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              )}

              {/* Accounting Explanation */}
              <div className="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-muted p-3">
                <span className="overline">
                  {t.journals.assistantExplanation || 'Explanation'}
                </span>
                <p className="text-xs leading-normal text-muted-foreground">
                  {suggestion.explanation}
                </p>
              </div>

              {/* Warnings display */}
              {suggestion.warnings.length > 0 && (
                <div className="callout tone-warning flex-col items-stretch gap-1.5 text-xs">
                  <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider">
                    <AlertTriangle aria-hidden className="h-3.5 w-3.5 flex-shrink-0" />
                    <span>{t.journals.assistantWarnings || 'Warnings'}</span>
                  </div>
                  <ul className="list-disc space-y-0.5 leading-normal ps-4">
                    {suggestion.warnings.map((warn, index) => (
                      <li key={index}>{warn}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Disclaimer */}
              <p className="text-center text-[10px] leading-normal text-subtle-foreground">
                {t.journals.assistantReviewDisclaimer || 'Review all suggestions before creating the entry.'}
              </p>

              {/* Apply Button */}
              <button
                type="button"
                onClick={handleApply}
                disabled={!suggestion.debitAccountId || !suggestion.creditAccountId}
                className="btn btn-primary btn-block mt-1"
              >
                <CheckCircle2 aria-hidden className="h-4 w-4" />
                <span>{t.journals.assistantApply || 'Apply Suggestion'}</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Provider Footer */}
      {aiStatus && (
        <div className="flex items-center justify-center gap-1 border-t border-border-subtle pt-2">
          <span className="text-[9px] text-subtle-foreground">
            {t.journals.providerLabel || 'Provider'}: {aiStatus.journal_provider}
          </span>
          <span className="text-[9px] text-subtle-foreground">·</span>
          <span className="text-[9px] text-subtle-foreground">
            {t.journals.fallbackLabel || 'Fallback'}: {t.journals.backendRules || 'Backend rules'}
          </span>
        </div>
      )}
    </div>
  );
}
