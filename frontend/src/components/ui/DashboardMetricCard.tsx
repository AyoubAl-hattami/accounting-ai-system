import { motion } from 'framer-motion';
import { type LucideIcon } from 'lucide-react';

export type MetricTone =
  | 'neutral'
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'violet'
  | 'rose'
  | 'teal';

interface DashboardMetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  index?: number;
  /** Drives the icon tile and the chip so a card only ever needs one colour decision. */
  tone?: MetricTone;
  chip?: string;
  chipTone?: MetricTone;
}

export default function DashboardMetricCard({
  label,
  value,
  icon: Icon,
  index = 0,
  tone = 'primary',
  chip,
  chipTone,
}: DashboardMetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05, ease: 'easeOut' }}
      className="card p-5 transition-colors hover:border-border-strong"
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <span
          className={`badge tone-${tone} h-9 w-9 justify-center rounded-lg p-0`}
          aria-hidden
        >
          <Icon className="h-4 w-4" />
        </span>
        {chip && <span className={`badge badge-uppercase tone-${chipTone ?? tone}`}>{chip}</span>}
      </div>
      <p className="overline mb-1.5">{label}</p>
      <p className="numeric text-2xl font-semibold tracking-tight text-foreground">{value}</p>
    </motion.div>
  );
}
