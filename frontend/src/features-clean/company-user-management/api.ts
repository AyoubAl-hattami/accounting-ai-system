/**
 * Company management API module (clean pilot).
 *
 * Covers company CRUD and company-user membership.
 * Does not import from other features.
 */
import { apiClient } from '../../shared/api';
import type { PaginatedResponse } from '../../shared/api';
import type { Company } from '../../entities/company';
import type {
  CompanyUser,
  CompanyUserRole,
  CompanyUserInvitationResponse,
  CompanyUserInvitationValidateResponse,
  CompanyUserInvitationRead,
} from '../../entities/user';

// ── Companies ────────────────────────────────────────────────────────────────

export async function listCompanies(params?: {
  skip?: number;
  limit?: number;
}): Promise<PaginatedResponse<Company>> {
  const { skip = 0, limit = 100 } = params ?? {};
  const response = await apiClient.get<PaginatedResponse<Company>>(
    `/companies?skip=${skip}&limit=${limit}`,
  );
  return response.data;
}

export async function getCompany(companyId: number): Promise<Company> {
  const response = await apiClient.get<Company>(`/companies/${companyId}`);
  return response.data;
}

export async function createCompany(payload: {
  name: string;
  description?: string | null;
  legal_name?: string | null;
  registration_no?: string | null;
  tax_no?: string | null;
  base_currency?: string;
  address?: string | null;
}): Promise<Company> {
  const response = await apiClient.post<Company>('/companies', payload);
  return response.data;
}

export async function updateCompany(
  companyId: number,
  payload: Partial<Omit<Company, 'id' | 'created_at' | 'updated_at'>>,
): Promise<Company> {
  const response = await apiClient.patch<Company>(`/companies/${companyId}`, payload);
  return response.data;
}

// ── Company users ─────────────────────────────────────────────────────────────

export async function listCompanyUsers(
  companyId: number,
): Promise<PaginatedResponse<CompanyUser>> {
  const response = await apiClient.get<PaginatedResponse<CompanyUser>>(
    `/company-users?company_id=${companyId}&skip=0&limit=200`,
  );
  return response.data;
}

export async function updateCompanyUserRole(
  companyUserId: number,
  role: CompanyUserRole,
): Promise<CompanyUser> {
  const response = await apiClient.patch<CompanyUser>(`/company-users/${companyUserId}`, { role });
  return response.data;
}

export async function deactivateCompanyUser(companyUserId: number): Promise<CompanyUser> {
  const response = await apiClient.patch<CompanyUser>(`/company-users/${companyUserId}/deactivate`);
  return response.data;
}

// ── Invitations ───────────────────────────────────────────────────────────────

export async function inviteUser(payload: {
  company_id: number;
  email: string;
  role: CompanyUserRole;
}): Promise<CompanyUserInvitationResponse> {
  const response = await apiClient.post<CompanyUserInvitationResponse>(
    '/company-users/invitations',
    payload,
  );
  return response.data;
}

export async function validateInvitation(
  token: string,
): Promise<CompanyUserInvitationValidateResponse> {
  const response = await apiClient.get<CompanyUserInvitationValidateResponse>(
    `/company-users/invitations/validate?token=${encodeURIComponent(token)}`,
  );
  return response.data;
}

export async function acceptInvitation(payload: {
  token: string;
  full_name?: string;
  password?: string;
}): Promise<{ status: string; message: string }> {
  const response = await apiClient.post<{ status: string; message: string }>(
    '/company-users/invitations/accept',
    payload,
  );
  return response.data;
}

export async function listPendingInvitations(
  companyId: number,
): Promise<CompanyUserInvitationRead[]> {
  const response = await apiClient.get<CompanyUserInvitationRead[]>(
    `/company-users/invitations?company_id=${companyId}`,
  );
  return response.data;
}

export async function cancelInvitation(
  invitationId: number,
): Promise<{ status: string; message: string }> {
  const response = await apiClient.delete<{ status: string; message: string }>(
    `/company-users/invitations/${invitationId}`,
  );
  return response.data;
}
