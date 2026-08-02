import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Building2, Check, ChevronDown } from 'lucide-react';
import type { Company } from '../../api/types';
import { useI18n } from '../../i18n';

interface CompanySelectorProps {
  companies: Company[];
  selectedCompany: Company | null;
  onSelect: (id: number) => void;
  collapsed?: boolean;
}

export default function CompanySelector({
  companies,
  selectedCompany,
  onSelect,
  collapsed = false,
}: CompanySelectorProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onPointerDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, []);

  const label = selectedCompany?.name || t.common.selectCompany;

  return (
    <div className="relative px-3 py-3" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={collapsed ? label : undefined}
        className={`flex w-full items-center gap-2.5 rounded-lg border border-border bg-surface-muted p-2.5 text-start transition-colors hover:border-border-strong hover:bg-surface-overlay ${
          collapsed ? 'justify-center' : ''
        }`}
      >
        <Building2 className="h-4 w-4 flex-shrink-0 text-primary" />
        {!collapsed && (
          <>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-xs font-semibold text-foreground">{label}</span>
              <span className="block text-[10px] text-subtle-foreground">
                {selectedCompany ? t.common.active : t.common.noCompanySelectedText}
              </span>
            </span>
            <ChevronDown
              className={`h-3.5 w-3.5 flex-shrink-0 text-subtle-foreground transition-transform duration-200 ${
                open ? 'rotate-180' : ''
              }`}
            />
          </>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="listbox"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.14 }}
            className={`absolute top-full z-50 mt-1 overflow-hidden rounded-lg border border-border bg-surface-raised shadow-lg ${
              collapsed ? 'start-3 w-56' : 'start-3 end-3'
            }`}
          >
            <div className="max-h-60 overflow-y-auto p-1.5">
              {companies.map((c) => {
                const isSelected = c.id === selectedCompany?.id;
                return (
                  <button
                    key={c.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      onSelect(c.id);
                      setOpen(false);
                    }}
                    className={`flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-start transition-colors ${
                      isSelected
                        ? 'bg-primary-soft text-primary'
                        : 'text-muted-foreground hover:bg-surface-muted hover:text-foreground'
                    }`}
                  >
                    <Building2 className="h-3.5 w-3.5 flex-shrink-0" />
                    <span className="flex-1 truncate text-xs font-medium">{c.name}</span>
                    {isSelected && <Check className="h-3.5 w-3.5 flex-shrink-0" />}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
