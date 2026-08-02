import { motion } from 'framer-motion';

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
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="card p-5"
    >
      <div className="mb-5">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
      </div>

      {isEmpty ? (
        <div
          className="flex items-center justify-center rounded-lg border border-dashed border-border bg-surface-muted"
          style={{ height }}
        >
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        </div>
      ) : (
        <div style={{ width: '100%', height }}>{children}</div>
      )}
    </motion.div>
  );
}
