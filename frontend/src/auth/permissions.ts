// ── Role-Based Permission Utilities ──
// Maps exactly to backend ensure_company_access allowed_roles

import type { CompanyUserRole } from '../api/types';
export type { CompanyUserRole };


/** Check if the user's role is in the allowed set */
export function hasRole(role: CompanyUserRole | null, allowed: readonly CompanyUserRole[]): boolean {
  if (!role) return false;
  return allowed.includes(role);
}

// ── Journal Entry Actions ──

/** Create / Update draft journal entry: admin, accountant */
export function canCreateJournal(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin', 'accountant']);
}

/** Review draft → reviewed: admin, accountant, reviewer */
export function canReviewJournal(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin', 'accountant', 'reviewer']);
}

/** Post reviewed → posted: admin, approver */
export function canPostJournal(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin', 'approver']);
}

/** Void entry: admin, accountant, approver */
export function canVoidJournal(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin', 'accountant']);
}

/** Reverse posted entry: admin, accountant */
export function canReverseJournal(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin', 'accountant', 'approver']);
}

// ── Account Actions ──

/** Create / update / seed accounts: admin, accountant */
export function canManageAccounts(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin', 'accountant']);
}

// ── Admin Pages ──

/** View audit logs: admin, auditor */
export function canViewAuditLogs(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin', 'auditor']);
}

/** View company users list: admin, auditor */
export function canViewCompanyUsers(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin', 'auditor']);
}

/** Create / update company users: admin only */
export function canManageCompanyUsers(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin']);
}

/** Company settings / fiscal config: admin only */
export function canManageSettings(role: CompanyUserRole | null): boolean {
  return hasRole(role, ['admin']);
}

// ── Page Visibility ──

/** Pages visible per role. Dashboard and reports are visible to all roles. */
const PAGE_ROLES: Record<string, readonly CompanyUserRole[]> = {
  '/dashboard':               ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'],
  '/journal-entries':         ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'],
  '/accounts':                ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'],
  '/audit-logs':              ['admin', 'auditor'],
  '/company-users':           ['admin', 'auditor'],
  '/reports/trial-balance':   ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'],
  '/reports/profit-and-loss': ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'],
  '/reports/balance-sheet':   ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'],
  '/reports/account-ledger':  ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'],
  '/reports/general-ledger':  ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'],
  '/settings':                ['admin'],
};

/** Check if a user can view a specific page */
export function canViewPage(role: CompanyUserRole | null, path: string): boolean {
  const allowed = PAGE_ROLES[path];
  if (!allowed) return true; // unknown pages default to visible
  return hasRole(role, allowed);
}

// ── Platform Pages ──

/**
 * Routes owned by the SaaS platform operator rather than by any tenant. They are
 * gated on `user.is_superuser`, never on a company role: the platform owner is
 * deliberately not a member of the companies it administers, so `canViewPage`
 * (which defaults unknown paths to visible) must not be consulted for them.
 */
const PLATFORM_PAGES: readonly string[] = [
  '/platform/dashboard',
  '/platform/subscriptions',
  '/platform/onboarding',
];

export function isPlatformPage(path: string): boolean {
  return PLATFORM_PAGES.includes(path);
}
