import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { useAuth } from './AuthContext';
import type { CompanyUser, CompanyUserRole, PaginatedResponse } from '../api/types';

interface UseCompanyRoleResult {
  role: CompanyUserRole | null;
  isLoading: boolean;
}

/**
 * Fetches the current user's role in the selected company.
 * Superusers automatically resolve to 'admin'.
 * Returns null if no company selected or user has no access.
 */
export function useCompanyRole(companyId: number | null): UseCompanyRoleResult {
  const { user } = useAuth();
  const [role, setRole] = useState<CompanyUserRole | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Superuser → admin, no API call needed
    if (user?.is_superuser) {
      setRole('admin');
      setIsLoading(false);
      return;
    }

    if (!companyId || !user) {
      setRole(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    apiClient
      .get<PaginatedResponse<CompanyUser>>(`/company-users?company_id=${companyId}&skip=0&limit=200`)
      .then((res) => {
        if (cancelled) return;
        const match = res.data.items.find((cu) => cu.user_id === user.id && cu.is_active);
        setRole(match ? match.role : null);
      })
      .catch(() => {
        if (!cancelled) setRole(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [companyId, user]);

  return { role, isLoading };
}
