import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CompanyUsersPage from '../../features/company-users/CompanyUsersPage';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';

vi.mock('../../components/layout/PageLayout', () => ({
  default: ({ children }: { children: (v: unknown) => React.ReactNode }) =>
    children({ selectedCompanyId: 7, companiesLoading: false, userRole: 'admin' }),
}));
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, is_superuser: false } }),
}));
vi.mock('../../components/feedback/useToast', () => ({
  useToast: () => ({
    success: vi.fn(), error: vi.fn(), info: vi.fn(),
    warning: vi.fn(), show: vi.fn(), dismiss: vi.fn(),
  }),
}));
vi.mock('../../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import apiClient from '../../api/client';
const mockGet = vi.mocked(apiClient.get);

const PAGE_SIZE = 20;

function members(count: number, adminIndexes: number[]) {
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    company_id: 7,
    user_id: i + 1,
    role: adminIndexes.includes(i) ? 'admin' : 'viewer',
    is_active: true,
    user_email: `m${i}@t.test`,
    user_full_name: `Member ${i}`,
    is_invitation: false,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }));
}

function serve(all: ReturnType<typeof members>, invitationCount: number) {
  mockGet.mockImplementation((url: string) => {
    if (url.includes('/company-users/invitations')) {
      return Promise.resolve({
        data: Array.from({ length: invitationCount }, (_, i) => ({
          id: 900 + i,
          company_id: 7,
          email: `inv${i}@t.test`,
          role: 'viewer',
          expires_at: '2026-02-01T00:00:00Z',
          created_at: '2026-01-01T00:00:00Z',
        })),
      });
    }
    const skip = Number(/skip=(\d+)/.exec(url)?.[1] ?? 0);
    return Promise.resolve({
      data: {
        items: all.slice(skip, skip + PAGE_SIZE),
        total: all.length,
        skip,
        limit: PAGE_SIZE,
      },
    });
  });
}

const rows = (container: HTMLElement) => {
  const table = container.querySelector('table');
  return table ? within(table as HTMLElement).getAllByRole('row').length - 1 : 0;
};

const disabledRemoveButtons = (container: HTMLElement) =>
  Array.from(container.querySelectorAll('table button')).filter(
    (b) =>
      b.textContent?.includes(en.companyUsersPage.removeAccess) &&
      (b as HTMLButtonElement).disabled,
  ).length;

async function goToPageTwo(user: ReturnType<typeof userEvent.setup>, container: HTMLElement) {
  const next = Array.from(container.querySelectorAll('button')).find((b) =>
    b.textContent?.includes(en.common.next),
  );
  await user.click(next as HTMLButtonElement);
}

describe('company users paging', () => {
  beforeEach(() => vi.clearAllMocks());

  // [N7] The Pending tab is a company-wide view. It used to be rendered from
  // the member page, and invitations were only fetched when skip === 0, so it
  // was empty on every page but the first.
  it('shows pending invitations on page two as well as page one', async () => {
    const user = userEvent.setup();
    serve(members(25, [0]), 3);
    const { container } = render(<I18nProvider><CompanyUsersPage /></I18nProvider>);
    await waitFor(() => expect(rows(container)).toBeGreaterThan(0));

    await user.click(screen.getByRole('tab', { name: en.companyUsersPage.pendingInvitations }));
    expect(rows(container)).toBe(3);

    await user.click(screen.getByRole('tab', { name: en.companyUsersPage.activeUsers }));
    await goToPageTwo(user, container);
    await waitFor(() => expect(rows(container)).toBe(5));

    await user.click(screen.getByRole('tab', { name: en.companyUsersPage.pendingInvitations }));
    expect(rows(container)).toBe(3);
  });

  it('fetches invitations on every page, not only the first', async () => {
    const user = userEvent.setup();
    serve(members(25, [0]), 2);
    const { container } = render(<I18nProvider><CompanyUsersPage /></I18nProvider>);
    await waitFor(() => expect(rows(container)).toBeGreaterThan(0));

    const afterFirstPage = mockGet.mock.calls.filter(([u]) =>
      String(u).includes('/invitations'),
    ).length;
    await goToPageTwo(user, container);
    await waitFor(() => expect(rows(container)).toBe(5));

    const afterSecondPage = mockGet.mock.calls.filter(([u]) =>
      String(u).includes('/invitations'),
    ).length;
    expect(afterSecondPage).toBeGreaterThan(afterFirstPage);
  });

  // [N9] The last-admin lock counted admins on the current page. Two admins on
  // different pages read as one, and the control was disabled while a second
  // admin plainly existed.
  it('does not lock the last-admin control when the count cannot be complete', async () => {
    const user = userEvent.setup();
    serve(members(25, [0, 22]), 0); // one admin on each page
    const { container } = render(<I18nProvider><CompanyUsersPage /></I18nProvider>);
    await waitFor(() => expect(rows(container)).toBe(20));

    expect(disabledRemoveButtons(container)).toBe(0);

    await goToPageTwo(user, container);
    await waitFor(() => expect(rows(container)).toBe(5));
    expect(disabledRemoveButtons(container)).toBe(0);
  });

  // The control: when the page really is the whole company, the count is
  // trustworthy and the lock must still engage.
  it('still locks the last admin when the page holds the whole company', async () => {
    serve(members(3, [0]), 0);
    const { container } = render(<I18nProvider><CompanyUsersPage /></I18nProvider>);
    await waitFor(() => expect(rows(container)).toBe(3));

    expect(disabledRemoveButtons(container)).toBe(1);
  });
});
