import { motion } from 'framer-motion';
import { type ReactNode } from 'react';
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
  /** A node so signed figures can bring their own positive/negative colour. */
  value: ReactNode;
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
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.36, delay: index * 0.06, ease: [0.16, 1, 0.3, 1] }}
      className={`card card-lift tone-${tone} group min-w-0 overflow-hidden p-4 sm:p-5`}
    >
      {/* Hairline of tone colour along the top edge — enough to identify the
          metric at a glance without tinting the whole card. */}
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-px opacity-70"
        style={{ background: 'linear-gradient(90deg, transparent, var(--tone-fg), transparent)' }}
      />

      <div className="mb-3 flex items-start justify-between gap-3 sm:mb-4">
        <span
          aria-hidden
          className={`badge tone-${tone} h-10 w-10 justify-center rounded-xl p-0 transition-transform duration-normal ease-emphasized group-hover:scale-110`}
        >
          <Icon className="h-[18px] w-[18px]" />
        </span>
        {chip && <span className={`badge badge-uppercase tone-${chipTone ?? tone}`}>{chip}</span>}
      </div>
      <p className="overline mb-1.5">{label}</p>
      <p className="numeric min-w-0 overflow-hidden text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
        {value}
      </p>
    </motion.div>
  );
}
