/**
 * Audit log API module (clean pilot).
 */
import { apiClient } from '../../shared/api';
import type { PaginatedResponse } from '../../shared/api';
import type { AuditLog } from '../../entities/audit-event';

export interface ListAuditLogsParams {
  companyId: number;
  skip?: number;
  limit?: number;
  entityType?: string | null;
  action?: string | null;
}

export async function listAuditLogs({
  companyId,
  skip = 0,
  limit = 20,
  entityType,
  action,
}: ListAuditLogsParams): Promise<PaginatedResponse<AuditLog>> {
  let url = `/audit-logs?company_id=${companyId}&skip=${skip}&limit=${limit}`;
  if (entityType) url += `&entity_type=${encodeURIComponent(entityType)}`;
  if (action) url += `&action=${encodeURIComponent(action)}`;
  const response = await apiClient.get<PaginatedResponse<AuditLog>>(url);
  return response.data;
}
