import { useCallback, useState } from 'react';
import axios from 'axios';
import apiClient from '../../api/client';
import type {
  CompanySubscription,
  PaginatedResponse,
  SubscriptionStatus,
} from '../../api/types';

const PAGE_SIZE = 20;

const ENDPOINT = '/platform/subscriptions';

interface UsePlatformSubscriptionsOptions {
  search: string;
  status: SubscriptionStatus | '';
  skip: number;
}

export function usePlatformSubscriptions({
  search,
  status,
  skip,
}: UsePlatformSubscriptionsOptions) {
  const [items, setItems] = useState<CompanySubscription[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusCode, setStatusCode] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchSubscriptions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setStatusCode(null);

    const params = new URLSearchParams({
      skip: String(skip),
      limit: String(PAGE_SIZE),
    });
    if (search.trim()) params.set('search', search.trim());
    if (status) params.set('status', status);

    try {
      const response = await apiClient.get<PaginatedResponse<CompanySubscription>>(
        `${ENDPOINT}?${params.toString()}`,
      );
      setItems(response.data.items);
      setTotal(response.data.total);
    } catch (err) {
      setStatusCode(axios.isAxiosError(err) ? (err.response?.status ?? null) : null);
      setError('load-failed');
      setItems([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [search, status, skip]);

  // One request helper for every mutation: the endpoints differ only by URL and
  // body, and all of them answer with the refreshed tenant summary.
  const submit = useCallback(
    async (
      path: string,
      body: Record<string, unknown>,
      method: 'post' | 'patch' = 'post',
    ): Promise<CompanySubscription | null> => {
      setIsSubmitting(true);
      try {
        const response =
          method === 'patch'
            ? await apiClient.patch<CompanySubscription>(path, body)
            : await apiClient.post<CompanySubscription>(path, body);
        return response.data;
      } catch {
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  const activate = useCallback(
    (companyId: number) => submit(`${ENDPOINT}/${companyId}/activate`, {}),
    [submit],
  );

  const suspend = useCallback(
    (companyId: number, reason: string | null) =>
      submit(`${ENDPOINT}/${companyId}/suspend`, { reason }),
    [submit],
  );

  const cancel = useCallback(
    (companyId: number, reason: string | null) =>
      submit(`${ENDPOINT}/${companyId}/cancel`, { reason }),
    [submit],
  );

  const extend = useCallback(
    (companyId: number, period: 'month' | 'year') =>
      submit(`${ENDPOINT}/${companyId}/extend`, { period }),
    [submit],
  );

  const update = useCallback(
    (
      companyId: number,
      payload: {
        status?: SubscriptionStatus;
        plan_code?: string | null;
        expires_at?: string | null;
      },
    ) => submit(`${ENDPOINT}/${companyId}`, payload, 'patch'),
    [submit],
  );

  return {
    items,
    total,
    isLoading,
    error,
    statusCode,
    isSubmitting,
    pageSize: PAGE_SIZE,
    fetchSubscriptions,
    activate,
    suspend,
    cancel,
    extend,
    update,
  };
}
