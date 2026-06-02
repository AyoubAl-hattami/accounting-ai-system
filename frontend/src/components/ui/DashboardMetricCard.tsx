import { motion } from 'framer-motion';
import { type LucideIcon } from 'lucide-react';

interface DashboardMetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  index?: number;
  trend?: 'up' | 'down' | 'neutral';
  chip?: string;
  chipColor?: string;
  iconColor?: string;
}

export default function DashboardMetricCard({
  label,
  value,
  icon: Icon,
  index = 0,
  trend = 'neutral',
  chip,
  chipColor = 'bg-gray-500/10 text-gray-400',
  iconColor = 'text-brand-400',
}: DashboardMetricCardProps) {
  const trendGlow = trend === 'up'
    ? 'from-emerald-500/10 to-transparent'
    : trend === 'down'
      ? 'from-red-500/10 to-transparent'
      : 'from-brand-500/5 to-transparent';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.07, ease: 'easeOut' }}
      className="glass-panel relative overflow-hidden group hover:border-white/[0.1] transition-all duration-300"
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${trendGlow} opacity-60`} />
      <div className="relative p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="p-2.5 rounded-xl bg-white/[0.05] border border-white/[0.06]">
            <Icon className={`w-4 h-4 ${iconColor}`} />
          </div>
          {chip && (
            <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${chipColor}`}>
              {chip}
            </span>
          )}
        </div>
        <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider mb-1">{label}</p>
        <p className="text-xl font-bold text-white tracking-tight">{value}</p>
      </div>
    </motion.div>
  );
}
