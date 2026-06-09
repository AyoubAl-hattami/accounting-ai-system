import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Building2, ChevronDown, Check } from 'lucide-react';
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
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (collapsed) {
    return (
      <div className="px-3 py-3">
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center justify-center p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-brand-500/20 transition-colors"
        >
          <Building2 className="w-4 h-4 text-brand-400" />
        </button>
      </div>
    );
  }

  return (
    <div className="px-3 py-3 relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2.5 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-brand-500/20 transition-all duration-200 group"
      >
        <Building2 className="w-4 h-4 text-brand-400 flex-shrink-0" />
        <div className="min-w-0 flex-1 text-left">
          <p className="text-xs font-medium text-gray-300 truncate">
            {selectedCompany?.name || t.common.selectCompany}
          </p>
          <p className="text-[10px] text-gray-500">
            {selectedCompany ? t.common.active : t.common.noCompanySelectedText}
          </p>
        </div>
        <ChevronDown className={`w-3.5 h-3.5 text-gray-500 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute left-3 right-3 top-full mt-1 z-50 rounded-xl bg-surface-700 border border-white/[0.08] shadow-2xl shadow-black/40 overflow-hidden"
          >
            <div className="p-1.5 max-h-48 overflow-y-auto">
              {companies.map((c) => (
                <button
                  key={c.id}
                  onClick={() => { onSelect(c.id); setOpen(false); }}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left transition-all duration-150 ${
                    c.id === selectedCompany?.id
                      ? 'bg-brand-500/10 text-brand-400'
                      : 'text-gray-300 hover:bg-white/[0.04] hover:text-white'
                  }`}
                >
                  <Building2 className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="text-xs font-medium truncate flex-1">{c.name}</span>
                  {c.id === selectedCompany?.id && (
                    <Check className="w-3.5 h-3.5 text-brand-400" />
                  )}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
