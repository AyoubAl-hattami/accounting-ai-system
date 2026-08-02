/**
 * useJournalEntries hook — clean version.
 *
 * Does not import from other features.
 */
import { useState, useCallback } from 'react';
import type { JournalEntry } from '../../entities/journal';
import { listJournalEntries, JOURNAL_PAGE_SIZE } from './api';

interface UseJournalEntriesOptions {
  companyId: number | null;
  skip: number;
}

export function useJournalEntries({ companyId, skip }: UseJournalEntriesOptions) {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEntries = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await listJournalEntries({
        companyId,
        skip,
        limit: JOURNAL_PAGE_SIZE,
      });
      setEntries(data.items);
      setTotal(data.total);
    } catch {
      setError('Failed to load journal entries. Please try again.');
      setEntries([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, skip]);

  return { entries, total, isLoading, error, fetchEntries, pageSize: JOURNAL_PAGE_SIZE };
}
