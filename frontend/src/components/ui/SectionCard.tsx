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
      transition={{ duration: 0.35, delay }}
      className="card overflow-hidden"
    >
      <div className="flex flex-col gap-3 border-b border-border bg-surface-muted px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <span
            aria-hidden
            className={`badge tone-${tone} h-10 w-10 flex-shrink-0 justify-center rounded-lg p-0`}
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
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </motion.section>
  );
}
