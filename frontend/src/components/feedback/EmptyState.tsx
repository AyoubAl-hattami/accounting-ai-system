import { type ReactNode } from 'react';
import { motion } from 'framer-motion';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
  className = 'py-16',
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`flex items-center justify-center ${className}`}
    >
      <div className="card max-w-sm p-8 text-center">
        {icon && (
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-primary-border bg-primary-soft text-primary shadow-[0_10px_28px_-14px_var(--primary-glow)]">
            {icon}
          </div>
        )}
        <h3 className="mb-1.5 text-base font-semibold text-foreground">{title}</h3>
        {description && (
          <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
        )}
        {action && <div className="mt-6">{action}</div>}
      </div>
    </motion.div>
  );
}
