import { useState, useCallback } from 'react';
import axios from 'axios';
import apiClient from '../../api/client';
import type { Company } from '../../api/types';

export function useCompanySettings() {
  const [company, setCompany] = useState<Company | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusCode, setStatusCode] = useState<number | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const fetchCompany = useCallback(async (companyId: number) => {
    setIsLoading(true);
    setError(null);
    setStatusCode(null);

    try {
      const response = await apiClient.get<Company>(`/companies/${companyId}`);
      setCompany(response.data);
    } catch (err) {
      let status: number | undefined;
      if (axios.isAxiosError(err)) {
        status = err.response?.status;
      }
      setStatusCode(status || null);
      if (status === 403) {
        setError('You do not have permission to view this company settings.');
      } else {
        setError('Failed to load company settings. Please try again.');
      }
      setCompany(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateCompany = useCallback(async (
    companyId: number,
    payload: {
      name?: string;
      legal_name?: string | null;
      registration_no?: string | null;
      tax_no?: string | null;
      base_currency?: string;
      address?: string | null;
    }
  ): Promise<Company | null> => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await apiClient.patch<Company>(`/companies/${companyId}`, payload);
      setCompany(response.data);
      return response.data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        if (status === 403) {
          setSubmitError('You do not have permission to update company settings. Only administrators can perform this action.');
        } else {
          const detail = err.response?.data?.detail;
          if (typeof detail === 'string') {
            setSubmitError(detail);
          } else {
            setSubmitError('Failed to update company settings. Please check your inputs.');
          }
        }
      } else {
        setSubmitError('Failed to update company settings. An unexpected error occurred.');
      }
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  return {
    company,
    isLoading,
    error,
    statusCode,
    fetchCompany,
    updateCompany,
    isSubmitting,
    submitError,
    setSubmitError,
  };
}
