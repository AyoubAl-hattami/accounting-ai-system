import { useCallback, useEffect, useState } from 'react';
import apiClient from '../../api/client';
import type { PlatformDashboard } from '../../api/types';

export function usePlatformDashboard() {
  const [data, setData] = useState<PlatformDashboard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(false);
    try {
      const response = await apiClient.get<PlatformDashboard>('/platform/dashboard');
      setData(response.data);
    } catch {
      setData(null);
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}
