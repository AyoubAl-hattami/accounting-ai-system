/**
 * useAuditLogs hook — clean version.
 *
 * Does not import from other features.
 */
import { useState, useCallback } from 'react';
import axios from 'axios';
import type { AuditLog } from '../../entities/audit-event';
import { listAuditLogs } from './api';

const PAGE_SIZE = 20;

interface UseAuditLogsOptions {
  companyId: number | null;
  skip: number;
  entityType?: string | null;
  action?: string | null;
}

export function useAuditLogs({ companyId, skip, entityType, action }: UseAuditLogsOptions) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusCode, setStatusCode] = useState<number | null>(null);

  const fetchLogs = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);
    setStatusCode(null);

    try {
      const data = await listAuditLogs({
        companyId,
        skip,
        limit: PAGE_SIZE,
        entityType,
        action,
      });
      setLogs(data.items);
      setTotal(data.total);
    } catch (err) {
      let status: number | undefined;
      if (axios.isAxiosError(err)) {
        status = err.response?.status;
      }
      setStatusCode(status ?? null);
      if (status === 403) {
        setError(
          'You do not have permission to view audit logs. ' +
          'Access is restricted to Admin and Auditor roles.',
        );
      } else {
        setError('Failed to load audit logs. Please try again.');
      }
      setLogs([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, skip, entityType, action]);

  return { logs, total, isLoading, error, statusCode, fetchLogs, pageSize: PAGE_SIZE };
}
