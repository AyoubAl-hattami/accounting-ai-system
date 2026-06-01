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
  className = 'py-20',
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`flex items-center justify-center ${className}`}
    >
      <div className="glass-panel p-8 max-w-sm text-center">
        {icon && (
          <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto mb-4">
            {icon}
          </div>
        )}
        <h3 className="text-white font-semibold text-lg mb-2">{title}</h3>
        {description && (
          <p className="text-gray-400 text-sm leading-relaxed">{description}</p>
        )}
        {action && <div className="mt-5">{action}</div>}
      </div>
    </motion.div>
  );
}
