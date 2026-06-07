import { useState, useCallback } from 'react';
import apiClient from '../../../api/client';
import type { GeneralLedgerRead } from '../../../api/types';

interface UseGeneralLedgerOptions {
  companyId: number | null;
  startDate: string | null;
  endDate: string | null;
}

export function useGeneralLedger({ companyId, startDate, endDate }: UseGeneralLedgerOptions) {
  const [data, setData] = useState<GeneralLedgerRead | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      let url = `/reports/general-ledger?company_id=${companyId}`;
      if (startDate) url += `&start_date=${startDate}`;
      if (endDate) url += `&end_date=${endDate}`;
      const response = await apiClient.get<GeneralLedgerRead>(url);
      setData(response.data);
    } catch {
      setError('Failed to load General Ledger report. Please try again.');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, startDate, endDate]);

  return { data, isLoading, error, fetchReport };
}
