import { useEffect, useState } from 'react';
import apiClient from '../../api/client';
import type { CompanySubscriptionStatus } from '../../api/types';

interface UseCompanySubscriptionStatusResult {
  status: CompanySubscriptionStatus | null;
  isLoading: boolean;
}

/**
 * Reads whether the selected company may still transact.
 *
 * The endpoint is deliberately exempt from the subscription gate, so a locked
 * out member can load it and be shown why rather than a wall of failed
 * requests. A failed read resolves to null and the caller lets the user
 * through — the server still refuses anything it should refuse.
 */
export function useCompanySubscriptionStatus(
  companyId: number | null,
): UseCompanySubscriptionStatusResult {
  const [status, setStatus] = useState<CompanySubscriptionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!companyId) {
      setStatus(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    apiClient
      .get<CompanySubscriptionStatus>(`/companies/${companyId}/subscription`)
      .then((res) => {
        if (!cancelled) setStatus(res.data);
      })
      .catch(() => {
        if (!cancelled) setStatus(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [companyId]);

  return { status, isLoading };
}
