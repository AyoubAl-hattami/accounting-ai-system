import { useState, useCallback } from 'react';
import axios from 'axios';
import apiClient from '../../api/client';
import type { JournalEntry } from '../../api/types';

export function useVoidJournalEntry() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const voidJournalEntry = useCallback(async (journalEntryId: number): Promise<JournalEntry | null> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await apiClient.post<JournalEntry>(`/journal-entries/${journalEntryId}/void`);
      return response.data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setSubmitError(detail);
        } else if (Array.isArray(detail)) {
          const msg = detail
              .map((d: { loc: (string | number)[]; msg: string }) => `${d.loc.join('.')}: ${d.msg}`)
              .join(', ');
          setSubmitError(msg);
        } else {
          setSubmitError('Failed to void journal entry. Please try again.');
        }
      } else {
        setSubmitError('Failed to void journal entry. An unexpected error occurred.');
      }
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  return { voidJournalEntry, isSubmitting, submitError, setSubmitError };
}
