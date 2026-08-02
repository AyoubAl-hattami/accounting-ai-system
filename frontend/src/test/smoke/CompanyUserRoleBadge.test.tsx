import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CompanyUserRoleBadge from '../../features/company-users/CompanyUserRoleBadge';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';

const renderBadge = (role: Parameters<typeof CompanyUserRoleBadge>[0]['role']) =>
  render(
    <I18nProvider>
      <CompanyUserRoleBadge role={role} />
    </I18nProvider>,
  );

describe('CompanyUserRoleBadge', () => {
  it('renders the translated role label', () => {
    renderBadge('admin');
    expect(screen.getByText(en.companyUsersPage.roles.admin)).toBeInTheDocument();
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
      const { unmount } = renderBadge(role);
      expect(screen.getByText(en.companyUsersPage.roles[role])).toBeInTheDocument();
      unmount();
    }
  });
});
