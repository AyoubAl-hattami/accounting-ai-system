import type { Account } from '../../../api/types';

export interface JournalAssistantSuggestion {
  debitAccountId?: number;
  creditAccountId?: number;
  amount?: number;
  confidence: 'high' | 'medium' | 'low';
  explanation: string;
  warnings: string[];
  detectedIntent: string;
}

export interface JournalAssistantInput {
  description: string;
  accounts: Account[];
  language: 'en' | 'ar';
}
export type { Account };
