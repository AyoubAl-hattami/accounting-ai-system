import { useState, useCallback } from 'react';
import apiClient from '../../../api/client';
import { suggestJournalEntry } from './journalAssistantRules';
import type { Account, JournalAssistantSuggestion } from './types';

export type SuggestionSource = 'backend_rules' | 'openai' | 'openai_fallback_rules' | 'gemini' | 'gemini_fallback_rules' | 'llm_placeholder_fallback' | 'local_fallback' | null;

interface UseSuggestionResult {
  suggest: (description: string, accounts: Account[], language: 'en' | 'ar', companyId: number) => Promise<void>;
  suggestion: JournalAssistantSuggestion | null;
  isLoading: boolean;
  source: SuggestionSource;
  clear: () => void;
}

interface BackendSuggestionResponse {
  debit_account_id: number | null;
  credit_account_id: number | null;
  amount: number | null;
  confidence: 'high' | 'medium' | 'low';
  explanation: string;
  warnings: string[];
  detected_intent: string;
  source: string;
}

export function useJournalSuggestion(): UseSuggestionResult {
  const [suggestion, setSuggestion] = useState<JournalAssistantSuggestion | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [source, setSource] = useState<SuggestionSource>(null);

  const clear = useCallback(() => {
    setSuggestion(null);
    setSource(null);
  }, []);

  const suggest = useCallback(
    async (
      description: string,
      accounts: Account[],
      language: 'en' | 'ar',
      companyId: number,
    ) => {
      if (!description.trim()) return;

      setIsLoading(true);

      try {
        // Attempt backend call first
        const response = await apiClient.post<BackendSuggestionResponse>(
          '/ai/journal-suggestions',
          {
            company_id: companyId,
            description,
            accounts: accounts.map((a) => ({
              id: a.id,
              code: a.code,
              name: a.name,
              account_type: a.account_type,
              is_active: a.is_active,
            })),
            language,
          },
        );

        const data = response.data;

        // Map snake_case backend response to camelCase frontend type
        const mapped: JournalAssistantSuggestion = {
          debitAccountId: data.debit_account_id ?? undefined,
          creditAccountId: data.credit_account_id ?? undefined,
          amount: data.amount ?? undefined,
          confidence: data.confidence,
          explanation: data.explanation,
          warnings: data.warnings,
          detectedIntent: data.detected_intent,
          source: (data.source as SuggestionSource) || 'backend_rules',
        };

        setSuggestion(mapped);
        setSource((data.source as SuggestionSource) || 'backend_rules');
      } catch {
        // Fallback to local rule engine on any error
        const localResult = suggestJournalEntry({
          description,
          accounts,
          language,
        });

        const mapped: JournalAssistantSuggestion = {
          ...localResult,
          source: 'local_fallback',
        };

        setSuggestion(mapped);
        setSource('local_fallback');
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { suggest, suggestion, isLoading, source, clear };
}
