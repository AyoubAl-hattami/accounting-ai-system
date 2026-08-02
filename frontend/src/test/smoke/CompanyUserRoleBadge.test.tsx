import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CompanyUserRoleBadge from '../../features/company-users/CompanyUserRoleBadge';

describe('CompanyUserRoleBadge', () => {
  it('renders the capitalized role label', () => {
    render(<CompanyUserRoleBadge role="admin" />);
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('renders each known role without throwing', () => {
    const roles: Array<Parameters<typeof CompanyUserRoleBadge>[0]['role']> = [
      'admin',
      'accountant',
      'reviewer',
      'approver',
      'auditor',
      'viewer',
    ];

    for (const role of roles) {
      const { unmount } = render(<CompanyUserRoleBadge role={role} />);
      expect(screen.getByText(role.charAt(0).toUpperCase() + role.slice(1))).toBeInTheDocument();
      unmount();
    }
  });
});
