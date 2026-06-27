import { motion } from 'framer-motion';
import { BarChart3 } from 'lucide-react';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  isEmpty?: boolean;
  emptyMessage?: string;
  delay?: number;
  height?: number;
}

export default function ChartCard({
  title,
  subtitle,
  children,
  isEmpty = false,
  emptyMessage = 'No chart data available',
  delay = 0,
  height = 260,
}: ChartCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="glass-panel p-5"
    >
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-4 h-4 text-brand-400" />
        <div>
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          {subtitle && (
            <p className="text-[11px] text-gray-500 mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>

      {isEmpty ? (
        <div
          className="flex items-center justify-center rounded-xl bg-white/[0.02] border border-white/[0.04]"
          style={{ height }}
        >
          <p className="text-sm text-gray-500">{emptyMessage}</p>
        </div>
      ) : (
        <div style={{ width: '100%', height }}>{children}</div>
      )}
    </motion.div>
  );
}
