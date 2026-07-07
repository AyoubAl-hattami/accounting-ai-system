import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../api/client';
import type { JournalEntry, PaginatedResponse } from '../../api/types';
import { dataEvents } from '../../lib/dataEvents';

const JE_PAGE_SIZE = 10;

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
      const response = await apiClient.get<PaginatedResponse<JournalEntry>>(
        `/journal-entries?company_id=${companyId}&skip=${skip}&limit=${JE_PAGE_SIZE}`,
      );
      setEntries(response.data.items);
      setTotal(response.data.total);
    } catch {
      setError('Failed to load journal entries. Please try again.');
      setEntries([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, skip]);

  // ── Auto-refetch when Gemini creates a journal entry ──
  useEffect(() => {
    const unsub = dataEvents.on('journal:created', fetchEntries);
    return () => unsub();
  }, [fetchEntries]);

  return { entries, total, isLoading, error, fetchEntries, pageSize: JE_PAGE_SIZE };
}
