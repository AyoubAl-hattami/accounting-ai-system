import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../../api/client';

interface AiStatus {
  journal_provider: string;
  llm_enabled: boolean;
  fallback_enabled: boolean;
  source: string;
  message: string;
}

interface UseAiStatusResult {
  status: AiStatus | null;
  isLoading: boolean;
  error: boolean;
  refresh: () => void;
}

export function useAiStatus(): UseAiStatusResult {
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(false);

  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    setError(false);

    try {
      const response = await apiClient.get<AiStatus>('/ai/status');
      setStatus(response.data);
    } catch {
      setError(true);
      setStatus(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  return { status, isLoading, error, refresh: fetchStatus };
}
