import { useState, useCallback } from 'react';
import axios from 'axios';
import apiClient from '../../api/client';
import type { CompanyUser, CompanyUserRole, PaginatedResponse, CompanyUserInvitationResponse, CompanyUserInvitationRead } from '../../api/types';

const USERS_PAGE_SIZE = 20;

interface UseCompanyUsersOptions {
  companyId: number | null;
  skip: number;
}

export function useCompanyUsers({ companyId, skip }: UseCompanyUsersOptions) {
  const [users, setUsers] = useState<CompanyUser[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusCode, setStatusCode] = useState<number | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);
    setStatusCode(null);

    try {
      const usersResponse = await apiClient.get<PaginatedResponse<CompanyUser>>(
        `/company-users?company_id=${companyId}&skip=${skip}&limit=${USERS_PAGE_SIZE}`
      );
      
      let items = [...usersResponse.data.items];
      
      // Also fetch pending invitations if we are on the first page
      if (skip === 0) {
        try {
          const invResponse = await apiClient.get<CompanyUserInvitationRead[]>(
            `/company-users/invitations?company_id=${companyId}`
          );
          
          const pendingUsers: CompanyUser[] = invResponse.data.map(inv => ({
            id: -inv.id, // Negative ID to distinguish from real users
            company_id: inv.company_id,
            user_id: 0,
            role: inv.role,
            is_active: false,
            user_email: inv.email,
            user_full_name: '(Pending Invitation)',
            is_invitation: true,
            expires_at: inv.expires_at,
            created_at: inv.created_at,
            updated_at: inv.created_at,
          }));
          
          items = [...pendingUsers, ...items];
        } catch (invErr) {
          // If invitations fail (e.g., non-admin user), just ignore and show regular users
          console.error("Failed to fetch pending invitations", invErr);
        }
      }

      setUsers(items);
      setTotal(usersResponse.data.total);
    } catch (err) {
      let status: number | undefined;
      if (axios.isAxiosError(err)) {
        status = err.response?.status;
      }
      setStatusCode(status || null);
      if (status === 403) {
        setError('You do not have permission to view company users. Access is restricted to Admin and Auditor roles.');
      } else {
        setError('Failed to load company users. Please try again.');
      }
      setUsers([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, skip]);

  const addCompanyUser = useCallback(async (payload: {
    company_id: number;
    user_id: number;
    role: CompanyUserRole;
    is_active: boolean;
  }): Promise<CompanyUser | null> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await apiClient.post<CompanyUser>('/company-users', payload);
      return response.data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setSubmitError(detail);
        } else if (Array.isArray(detail)) {
          const msg = detail
            .map((d: { loc: (string | number)[]; msg: string }) => `${d.loc.join('.')}: ${d.msg}`)
            .join(', ');
          setSubmitError(msg);
        } else {
          setSubmitError('Failed to add company user. Please check your inputs.');
        }
      } else {
        setSubmitError('Failed to add company user. An unexpected error occurred.');
      }
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const inviteCompanyUser = useCallback(async (payload: {
    company_id: number;
    email: string;
    role: CompanyUserRole;
  }): Promise<CompanyUserInvitationResponse | null> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await apiClient.post<CompanyUserInvitationResponse>('/company-users/invitations', payload);
      return response.data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setSubmitError(detail);
        } else {
          setSubmitError('Failed to invite user. Please check your inputs.');
        }
      } else {
        setSubmitError('Failed to invite user. An unexpected error occurred.');
      }
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const updateCompanyUser = useCallback(async (
    companyUserId: number,
    payload: {
      role?: CompanyUserRole;
      is_active?: boolean;
    }
  ): Promise<CompanyUser | null> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await apiClient.patch<CompanyUser>(`/company-users/${companyUserId}`, payload);
      return response.data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setSubmitError(detail);
        } else {
          setSubmitError('Failed to update company user. Please check your inputs.');
        }
      } else {
        setSubmitError('Failed to update company user. An unexpected error occurred.');
      }
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const removeCompanyAccess = useCallback(async (
    companyUserId: number
  ): Promise<boolean> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await apiClient.patch(`/company-users/${companyUserId}/remove-access`);
      return true;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setSubmitError(detail);
        } else {
          setSubmitError('Failed to remove company access.');
        }
      } else {
        setSubmitError('Failed to remove company access. An unexpected error occurred.');
      }
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const deactivateUserAccount = useCallback(async (
    userId: number,
    companyId: number
  ): Promise<boolean> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await apiClient.patch(`/company-users/users/${userId}/deactivate?company_id=${companyId}`);
      return true;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setSubmitError(detail);
        } else {
          setSubmitError('Failed to deactivate user account.');
        }
      } else {
        setSubmitError('Failed to deactivate user account. An unexpected error occurred.');
      }
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const cancelInvitation = useCallback(async (
    invitationId: number
  ): Promise<boolean> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await apiClient.delete(`/company-users/invitations/${invitationId}`);
      return true;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setSubmitError(detail);
        } else {
          setSubmitError('Failed to cancel invitation.');
        }
      } else {
        setSubmitError('Failed to cancel invitation. An unexpected error occurred.');
      }
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const restoreCompanyAccess = useCallback(async (
    companyUserId: number
  ): Promise<boolean> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await apiClient.patch(`/company-users/${companyUserId}/restore-access`);
      return true;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setSubmitError(detail);
        } else {
          setSubmitError('Failed to restore company access.');
        }
      } else {
        setSubmitError('Failed to restore company access. An unexpected error occurred.');
      }
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const reactivateUserAccount = useCallback(async (
    userId: number,
    companyId: number
  ): Promise<boolean> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await apiClient.patch(`/company-users/users/${userId}/reactivate?company_id=${companyId}`);
      return true;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setSubmitError(detail);
        } else {
          setSubmitError('Failed to reactivate user account.');
        }
      } else {
        setSubmitError('Failed to reactivate user account. An unexpected error occurred.');
      }
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  return {
    users,
    total,
    isLoading,
    error,
    statusCode,
    fetchUsers,
    pageSize: USERS_PAGE_SIZE,
    addCompanyUser,
    inviteCompanyUser,
    updateCompanyUser,
    removeCompanyAccess,
    deactivateUserAccount,
    cancelInvitation,
    restoreCompanyAccess,
    reactivateUserAccount,
    isSubmitting,
    submitError,
    setSubmitError,
  };
}
