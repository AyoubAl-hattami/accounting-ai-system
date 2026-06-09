import { useState, useCallback } from 'react';
import axios from 'axios';
import apiClient from '../../api/client';
import type { AuditLog, PaginatedResponse } from '../../api/types';

const AUDIT_LOGS_PAGE_SIZE = 20;

interface UseAuditLogsOptions {
  companyId: number | null;
  skip: number;
  entityType?: string | null;
}

export function useAuditLogs({ companyId, skip, entityType }: UseAuditLogsOptions) {
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
      let url = `/audit-logs?company_id=${companyId}&skip=${skip}&limit=${AUDIT_LOGS_PAGE_SIZE}`;
      if (entityType) {
        url += `&entity_type=${encodeURIComponent(entityType)}`;
      }
      
      const response = await apiClient.get<PaginatedResponse<AuditLog>>(url);
      setLogs(response.data.items);
      setTotal(response.data.total);
    } catch (err) {
      let status: number | undefined;
      if (axios.isAxiosError(err)) {
        status = err.response?.status;
      }
      setStatusCode(status || null);
      if (status === 403) {
        setError('You do not have permission to view audit logs. Access is restricted to Admin and Auditor roles.');
      } else {
        setError('Failed to load audit logs. Please try again.');
      }
      setLogs([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, skip, entityType]);

  return { 
    logs, 
    total, 
    isLoading, 
    error, 
    statusCode, 
    fetchLogs, 
    pageSize: AUDIT_LOGS_PAGE_SIZE 
  };
}
