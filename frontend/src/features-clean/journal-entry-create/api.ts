/**
 * Journal entry API module (clean pilot).
 *
 * Covers list, create, review, post, void, reverse.
 * Does not import from other features.
 */
import { apiClient } from '../../shared/api';
import type { PaginatedResponse } from '../../shared/api';
import type {
  JournalEntry,
  JournalEntryStatus,
  JournalEntryCreatePayload,
} from '../../entities/journal';

const PAGE_SIZE = 10;

export interface ListJournalEntriesParams {
  companyId: number;
  skip?: number;
  limit?: number;
  status?: JournalEntryStatus | null;
}

export async function listJournalEntries({
  companyId,
  skip = 0,
  limit = PAGE_SIZE,
  status,
}: ListJournalEntriesParams): Promise<PaginatedResponse<JournalEntry>> {
  let url = `/journal-entries?company_id=${companyId}&skip=${skip}&limit=${limit}`;
  if (status) url += `&status=${status}`;
  const response = await apiClient.get<PaginatedResponse<JournalEntry>>(url);
  return response.data;
}

export async function createJournalEntry(
  payload: JournalEntryCreatePayload,
): Promise<JournalEntry> {
  const response = await apiClient.post<JournalEntry>('/journal-entries', payload);
  return response.data;
}

export async function reviewJournalEntry(entryId: number): Promise<JournalEntry> {
  const response = await apiClient.post<JournalEntry>(`/journal-entries/${entryId}/review`);
  return response.data;
}

export async function postJournalEntry(entryId: number): Promise<JournalEntry> {
  const response = await apiClient.post<JournalEntry>(`/journal-entries/${entryId}/post`);
  return response.data;
}

export async function voidJournalEntry(
  entryId: number,
  reason?: string,
): Promise<JournalEntry> {
  const response = await apiClient.post<JournalEntry>(`/journal-entries/${entryId}/void`, {
    reason,
  });
  return response.data;
}

export async function reverseJournalEntry(
  entryId: number,
  payload: { entry_date: string; description?: string },
): Promise<JournalEntry> {
  const response = await apiClient.post<JournalEntry>(
    `/journal-entries/${entryId}/reverse`,
    payload,
  );
  return response.data;
}

export { PAGE_SIZE as JOURNAL_PAGE_SIZE };
