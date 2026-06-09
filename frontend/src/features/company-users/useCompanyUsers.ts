import { useState, useCallback } from 'react';
import axios from 'axios';
import apiClient from '../../api/client';
import type { CompanyUser, CompanyUserRole, PaginatedResponse } from '../../api/types';

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
      const response = await apiClient.get<PaginatedResponse<CompanyUser>>(
        `/company-users?company_id=${companyId}&skip=${skip}&limit=${USERS_PAGE_SIZE}`
      );
      setUsers(response.data.items);
      setTotal(response.data.total);
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

  return {
    users,
    total,
    isLoading,
    error,
    statusCode,
    fetchUsers,
    pageSize: USERS_PAGE_SIZE,
    addCompanyUser,
    updateCompanyUser,
    isSubmitting,
    submitError,
    setSubmitError,
  };
}
