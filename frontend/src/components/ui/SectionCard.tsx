import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

interface SectionCardProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  /** Tints the icon tile; matches the `.tone-*` scale used by badges. */
  tone?: 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'violet' | 'teal';
  actions?: ReactNode;
  children: ReactNode;
  delay?: number;
}

/**
 * Titled panel used for the settings-style sections: a muted header strip with
 * an icon, a title/description pair and optional actions, over a plain body.
 */
export default function SectionCard({
  icon: Icon,
  title,
  description,
  tone = 'primary',
  actions,
  children,
  delay = 0,
}: SectionCardProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: [0.16, 1, 0.3, 1] }}
      className="card group overflow-hidden"
    >
      <div className="relative flex flex-col gap-3 overflow-hidden border-b border-border bg-surface-muted px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <span
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-px opacity-60"
          style={{ background: 'var(--gradient-brand)' }}
        />
        <div className="relative flex min-w-0 items-center gap-3">
          <span
            aria-hidden
            className={`badge tone-${tone} h-10 w-10 flex-shrink-0 justify-center rounded-xl p-0 transition-transform duration-normal ease-emphasized group-hover:scale-105`}
          >
            <Icon className="h-[18px] w-[18px]" />
          </span>
          <div className="min-w-0">
            <h2 className="section-title truncate">{title}</h2>
            {description && (
              <p className="truncate text-xs text-muted-foreground">{description}</p>
            )}
          </div>
        </div>
        {actions && <div className="relative flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </motion.section>
  );
}
