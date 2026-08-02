import { describe, it, expect } from 'vitest';
import { getActionLabel } from '../../features/audit/auditActionLabels';

describe('getActionLabel', () => {
  it('resolves a snake_case action to its i18n label when present', () => {
    const auditT = { createJournalEntry: 'Create Journal Entry' };
    expect(getActionLabel('create_journal_entry', auditT)).toBe('Create Journal Entry');
  });

  it('falls back to title case when no i18n label matches', () => {
    expect(getActionLabel('delete_account', {})).toBe('Delete Account');
  });

  it('title-cases fallback across hyphen and space separators', () => {
    expect(getActionLabel('re-open review', {})).toBe('Re Open Review');
  });

  it('handles a single-word action with no i18n match', () => {
    expect(getActionLabel('login', {})).toBe('Login');
  });
});
