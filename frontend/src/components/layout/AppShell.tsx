import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  BarChart3,
  BookMarked,
  BookOpen,
  Building2,
  ChevronLeft,
  FileText,
  Globe,
  LayoutDashboard,
  Library,
  LogOut,
  Menu,
  Receipt,
  Scale,
  Settings,
  Shield,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { canManageSettings, canViewPage } from '../../auth/permissions';
import { useI18n } from '../../i18n';
import { ThemeToggleButton } from '../ui/ThemeToggle';
import CompanySelector from './CompanySelector';
import type { Company, CompanyUserRole } from '../../api/types';
import GlobalGeminiAssistant from '../../features/ai/GlobalGeminiAssistant';

interface AppShellProps {
  children: React.ReactNode;
  companies: Company[];
  selectedCompany: Company | null;
  onSelectCompany: (id: number) => void;
  pageTitle?: string;
  pageSubtitle?: string;
  activePath?: string;
  userRole?: CompanyUserRole | null;
}

interface NavItem {
  icon: LucideIcon;
  label: string;
  path: string;
}

/**
 * Every page renders its own PageLayout, so navigating unmounts this component
 * and mounts a fresh one. Plain `useState` therefore forgets the collapse choice
 * on every route change and the sidebar springs back to full width. Persisting it
 * makes the preference outlive the remount — and a page reload with it.
 */
const SIDEBAR_STORAGE_KEY = 'app-sidebar-collapsed';

function readStoredCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true';
  } catch {
    // localStorage unavailable (private mode, embedded webview)
    return false;
  }
}

export default function AppShell({
  children,
  companies,
  selectedCompany,
  onSelectCompany,
  pageTitle,
  pageSubtitle,
  activePath,
  userRole = null,
}: AppShellProps) {
  const { user, logout } = useAuth();
  const { t, dir, language, setLanguage } = useI18n();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  // The URL is right on the first render; the page's own declaration arrives a
  // beat later from a layout effect. Reading the route here keeps the content
  // transition key stable from the outset — keying it on the late value would
  // tear down and rebuild each page immediately after mounting it, firing every
  // data fetch twice.
  const currentPath = activePath ?? pathname;
  // Lazy initialiser, so the stored width is applied on the first paint of the
  // new route rather than flashing expanded and then snapping shut.
  const [collapsed, setCollapsed] = useState(readStoredCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
      } catch {
        // localStorage unavailable — the choice still holds for this session
      }
      return next;
    });
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  const isRtl = dir === 'rtl';
  const toggleLanguage = () => setLanguage(language === 'en' ? 'ar' : 'en');

  const displayTitle = pageTitle || t.dashboard.pageTitle;
  const displaySubtitle = pageSubtitle || t.dashboard.pageSubtitle;

  // Grouping turns a flat ten-item list into four short scannable blocks.
  const navGroups: { label: string; items: NavItem[] }[] = [
    {
      label: t.nav.groupOverview,
      items: [{ icon: LayoutDashboard, label: t.nav.dashboard, path: '/dashboard' }],
    },
    {
      label: t.nav.groupBookkeeping,
      items: [
        { icon: BookOpen, label: t.nav.journalEntries, path: '/journal-entries' },
        { icon: Receipt, label: t.nav.accounts, path: '/accounts' },
      ],
    },
    {
      label: t.nav.groupReports,
      items: [
        { icon: BarChart3, label: t.nav.trialBalance, path: '/reports/trial-balance' },
        { icon: FileText, label: t.nav.profitAndLoss, path: '/reports/profit-and-loss' },
        { icon: Scale, label: t.nav.balanceSheet, path: '/reports/balance-sheet' },
        { icon: BookMarked, label: t.nav.accountLedger, path: '/reports/account-ledger' },
        { icon: Library, label: t.nav.generalLedger, path: '/reports/general-ledger' },
      ],
    },
    {
      label: t.nav.groupAdministration,
      items: [
        { icon: Users, label: t.nav.companyUsers, path: '/company-users' },
        { icon: Shield, label: t.nav.auditLogs, path: '/audit-logs' },
      ],
    },
  ]
    .map((group) => ({ ...group, items: group.items.filter((i) => canViewPage(userRole, i.path)) }))
    .filter((group) => group.items.length > 0);

  // Appended after the role filter on purpose: canViewPage answers for tenant
  // roles and lets unknown paths through, which would show this group to
  // everyone. Platform pages key off the platform flag instead.
  if (user?.is_superuser) {
    navGroups.push({
      label: t.nav.groupPlatform,
      items: [
        { icon: Building2, label: t.nav.platformSubscriptions, path: '/platform/subscriptions' },
        { icon: UserPlus, label: t.nav.platformOnboarding, path: '/platform/onboarding' },
      ],
    });
  }

  const handleNav = (path: string) => {
    navigate(path);
    setMobileOpen(false);
  };

  const roleLabel = userRole ? userRole.charAt(0).toUpperCase() + userRole.slice(1) : null;

  const renderNavButton = ({ icon: Icon, label, path }: NavItem) => {
    const isActive = path === currentPath;
    return (
      <button
        key={path}
        type="button"
        onClick={() => handleNav(path)}
        aria-current={isActive ? 'page' : undefined}
        title={collapsed ? label : undefined}
        className={`nav-item ${isActive ? 'nav-item-active' : ''} ${collapsed ? 'justify-center' : ''}`}
      >
        <Icon className="nav-icon" />
        {!collapsed && <span className="truncate">{label}</span>}
      </button>
    );
  };

  return (
    <div className="flex min-h-screen">
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-backdrop backdrop-blur-sm lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      <aside
        className={`glass fixed top-0 z-50 flex h-screen flex-col transition-[width,transform] duration-slow ease-emphasized lg:sticky
          ${isRtl ? 'right-0 border-l' : 'left-0 border-r'}
          ${collapsed ? 'w-[76px]' : 'w-64'}
          ${
            mobileOpen
              ? 'translate-x-0'
              : isRtl
                ? 'translate-x-full lg:translate-x-0'
                : '-translate-x-full lg:translate-x-0'
          }`}
      >
        <div className="flex h-16 flex-shrink-0 items-center gap-3 border-b border-border px-4">
          <button
            type="button"
            onClick={() => handleNav('/dashboard')}
            className="group flex min-w-0 flex-1 items-center gap-3 text-start"
          >
            <span className="relative flex h-9 w-9 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg bg-gradient-brand text-white shadow-[0_6px_18px_-6px_var(--primary-glow)] transition-transform duration-fast ease-emphasized group-hover:scale-105">
              <Scale className="nav-icon" />
            </span>
            {!collapsed && (
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold tracking-tight text-foreground">
                  {t.nav.appName}
                </span>
                <span className="overline block truncate">{t.nav.appTagline}</span>
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label={t.nav.closeMenu}
            className="btn-icon lg:hidden"
          >
            <X className="nav-icon" />
          </button>
        </div>

        <CompanySelector
          companies={companies}
          selectedCompany={selectedCompany}
          onSelect={onSelectCompany}
          collapsed={collapsed}
        />

        <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-3">
          {navGroups.map((group, groupIndex) => (
            <div
              key={group.label}
              className="motion-safe:animate-slide-up space-y-1"
              style={{ animationDelay: `${groupIndex * 60}ms` }}
            >
              {!collapsed && <p className="overline px-3 pb-1">{group.label}</p>}
              {group.items.map(renderNavButton)}
            </div>
          ))}
        </nav>

        <div className="flex-shrink-0 space-y-1 border-t border-border px-3 py-3">
          {canManageSettings(userRole) &&
            renderNavButton({ icon: Settings, label: t.nav.settings, path: '/settings' })}
          <button
            type="button"
            onClick={logout}
            title={collapsed ? t.nav.signOut : undefined}
            className={`nav-item hover:bg-danger-soft hover:text-danger ${collapsed ? 'justify-center' : ''}`}
          >
            <LogOut className="nav-icon" />
            {!collapsed && <span className="truncate">{t.nav.signOut}</span>}
          </button>
        </div>

        <button
          type="button"
          onClick={toggleCollapsed}
          aria-label={collapsed ? t.nav.expandSidebar : t.nav.collapseSidebar}
          title={collapsed ? t.nav.expandSidebar : t.nav.collapseSidebar}
          className={`absolute top-[74px] hidden h-6 w-6 items-center justify-center rounded-full border border-border-strong bg-surface-raised text-muted-foreground shadow-sm transition-all duration-fast ease-emphasized hover:scale-110 hover:border-primary-border hover:text-primary lg:flex ${
            isRtl ? '-left-3' : '-right-3'
          }`}
        >
          <ChevronLeft
            className={`h-3.5 w-3.5 transition-transform duration-slow ease-emphasized ${
              collapsed !== isRtl ? 'rotate-180' : ''
            }`}
          />
        </button>
      </aside>

      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <header className="glass sticky top-0 z-30 flex h-[4.5rem] items-center justify-between gap-4 border-b px-4 lg:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label={t.nav.openMenu}
              className="btn-icon lg:hidden"
            >
              <Menu className="nav-icon" />
            </button>
            <div key={pathname} className="motion-safe:animate-fade-in min-w-0">
              <h1 className="truncate text-base font-semibold tracking-tight text-foreground">
                {displayTitle}
              </h1>
              <p className="truncate text-xs text-muted-foreground">{displaySubtitle}</p>
            </div>
          </div>

          <div className="flex flex-shrink-0 items-center gap-2">
            {selectedCompany && (
              <span
                className="badge tone-neutral hidden max-w-[190px] xl:inline-flex"
                title={selectedCompany.name}
              >
                <span aria-hidden className="relative flex h-1.5 w-1.5 flex-shrink-0">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-success opacity-70 motion-safe:animate-ping" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
                </span>
                <span className="truncate">{selectedCompany.name}</span>
              </span>
            )}

            <button
              type="button"
              onClick={toggleLanguage}
              className="btn btn-ghost btn-sm gap-1.5"
              title={language === 'en' ? 'التبديل إلى العربية' : 'Switch to English'}
            >
              <Globe className="nav-icon" />
              <span className="text-[11px] font-semibold uppercase tracking-wide">
                {language === 'en' ? 'EN' : 'AR'}
              </span>
            </button>

            <ThemeToggleButton />

            <div className="mx-1 hidden h-6 w-px bg-border sm:block" />

            <div className="hidden text-end sm:block">
              <p className="max-w-[180px] truncate text-sm font-medium text-foreground">
                {user?.full_name || user?.email}
              </p>
              <p className="text-[11px] text-subtle-foreground">
                {user?.is_superuser ? t.common.administrator : roleLabel || t.common.user}
              </p>
            </div>
            <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-primary text-sm font-semibold text-white shadow-[0_6px_18px_-8px_var(--primary-glow)]">
              {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
            </span>
          </div>
        </header>

        {/* The <main> box itself is never keyed: its padding, flex sizing and
            FAB safe area must stay in the DOM across navigations, or the page
            height collapses for a frame and the scrollbar flicks away. Only the
            inner wrapper is keyed, so the content re-enters while the well it
            sits in holds still. */}
        <main className="pb-safe-fab min-w-0 flex-1 px-4 pt-4 lg:px-6 lg:pt-6">
          <div key={pathname} className="motion-safe:page-enter">
            {children}
          </div>
        </main>
      </div>

      <GlobalGeminiAssistant
        companyId={selectedCompany?.id ?? null}
        userRole={userRole}
        companyName={selectedCompany?.name ?? null}
      />
    </div>
  );
}
