import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { CompaniesProvider } from '../../features/companies/CompaniesProvider';
import { useCompanies } from '../../features/companies/useCompanies';

const authState = {
  user: {
    id: 1,
    email: 'platform@example.com',
    full_name: 'Platform Admin',
    is_active: true,
    is_superuser: true,
    must_change_password: false,
  },
};

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => authState }));
vi.mock('../../api/client', () => ({ default: { get: vi.fn() } }));

import apiClient from '../../api/client';

function Probe() {
  const { selectedCompanyId, companies, isLoading } = useCompanies();
  return <p>{`${selectedCompanyId ?? 'none'}:${companies.length}:${isLoading}`}</p>;
}

describe('CompaniesProvider platform isolation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('clears stale tenant selection and does not request companies for a platform admin', async () => {
    localStorage.setItem('selected_company_id', '3');

    render(
      <CompaniesProvider>
        <Probe />
      </CompaniesProvider>,
    );

    await waitFor(() => expect(screen.getByText('none:0:false')).toBeInTheDocument());
    expect(localStorage.getItem('selected_company_id')).toBeNull();
    expect(apiClient.get).not.toHaveBeenCalled();
  });
});
