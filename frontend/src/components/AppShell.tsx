import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../auth/AuthContext';
import CompanySelector from './CompanySelector';
import type { Company } from '../api/types';
import {
  LayoutDashboard,
  BookOpen,
  Receipt,
  BarChart3,
  FileText,
  Scale,
  Settings,
  LogOut,
  ChevronLeft,
  Menu,
} from 'lucide-react';

interface AppShellProps {
  children: React.ReactNode;
  companies: Company[];
  selectedCompany: Company | null;
  onSelectCompany: (id: number) => void;
  pageTitle?: string;
  pageSubtitle?: string;
  activePath?: string;
}

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
  { icon: BookOpen, label: 'Journal Entries', path: '/journal-entries' },
  { icon: Receipt, label: 'Accounts', path: '/accounts' },
  { icon: BarChart3, label: 'Trial Balance', path: '/reports/trial-balance' },
  { icon: FileText, label: 'Profit & Loss', path: '/reports/profit-loss' },
  { icon: Scale, label: 'Balance Sheet', path: '/reports/balance-sheet' },
];

export default function AppShell({
  children,
  companies,
  selectedCompany,
  onSelectCompany,
  pageTitle = 'Dashboard',
  pageSubtitle = 'Financial overview',
  activePath = '/dashboard',
}: AppShellProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const sidebarWidth = collapsed ? 'w-[72px]' : 'w-64';

  const handleNav = (path: string) => {
    navigate(path);
    setMobileOpen(false);
  };

  return (
    <div className="min-h-screen bg-surface-900 flex">
      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:sticky top-0 left-0 h-screen z-50
          ${sidebarWidth}
          bg-surface-800/80 backdrop-blur-2xl
          border-r border-white/[0.06]
          flex flex-col
          transition-all duration-300 ease-in-out
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Logo area */}
        <div className="h-16 flex items-center px-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-3 overflow-hidden cursor-pointer" onClick={() => handleNav('/dashboard')}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center flex-shrink-0 shadow-lg shadow-brand-500/20">
              <Scale className="w-5 h-5 text-white" />
            </div>
            <AnimatePresence>
              {!collapsed && (
                <motion.div
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  className="overflow-hidden whitespace-nowrap"
                >
                  <h1 className="text-base font-bold text-white tracking-tight">Accounting</h1>
                  <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">AI System</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Company selector */}
        <CompanySelector
          companies={companies}
          selectedCompany={selectedCompany}
          onSelect={onSelectCompany}
          collapsed={collapsed}
        />

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = item.path === activePath;
            return (
              <button
                key={item.path}
                onClick={() => handleNav(item.path)}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-xl
                  transition-all duration-200 group
                  ${isActive
                    ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/[0.04] border border-transparent'
                  }
                  ${collapsed ? 'justify-center' : ''}
                `}
              >
                <item.icon className={`w-[18px] h-[18px] flex-shrink-0 ${isActive ? 'text-brand-400' : 'group-hover:text-gray-200'}`} />
                {!collapsed && (
                  <span className="text-sm font-medium truncate">{item.label}</span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom area */}
        <div className="px-3 py-3 border-t border-white/[0.06] space-y-1">
          <button className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-gray-200 hover:bg-white/[0.04] transition-all duration-200 ${collapsed ? 'justify-center' : ''}`}>
            <Settings className="w-[18px] h-[18px] flex-shrink-0" />
            {!collapsed && <span className="text-sm font-medium">Settings</span>}
          </button>
          <button
            onClick={logout}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-red-400 hover:bg-red-500/[0.06] transition-all duration-200 ${collapsed ? 'justify-center' : ''}`}
          >
            <LogOut className="w-[18px] h-[18px] flex-shrink-0" />
            {!collapsed && <span className="text-sm font-medium">Sign Out</span>}
          </button>
        </div>

        {/* Collapse button */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden lg:flex absolute -right-3 top-20 w-6 h-6 items-center justify-center rounded-full bg-surface-600 border border-white/[0.1] text-gray-400 hover:text-white hover:bg-surface-500 transition-all duration-200"
        >
          <ChevronLeft className={`w-3.5 h-3.5 transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`} />
        </button>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        {/* Top bar */}
        <header className="h-16 flex items-center justify-between px-4 lg:px-6 border-b border-white/[0.06] bg-surface-800/40 backdrop-blur-xl sticky top-0 z-30">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/[0.06] transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-lg font-semibold text-white">{pageTitle}</h2>
              <p className="text-xs text-gray-500">{pageSubtitle}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {selectedCompany && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-brand-500/[0.06] border border-brand-500/10">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span className="text-xs font-medium text-brand-300">{selectedCompany.name}</span>
              </div>
            )}
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-gray-200">{user?.full_name || user?.email}</p>
              <p className="text-[11px] text-gray-500">{user?.is_superuser ? 'Administrator' : 'User'}</p>
            </div>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-brand-500/20">
              {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
