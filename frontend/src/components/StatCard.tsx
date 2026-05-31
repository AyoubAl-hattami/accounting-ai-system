import { motion } from 'framer-motion';
import { type LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  index?: number;
  accentColor?: string;
}

export default function StatCard({
  title,
  description,
  icon: Icon,
  index = 0,
  accentColor = 'from-brand-500/20 to-brand-600/5',
}: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1, ease: 'easeOut' }}
      className="glass-panel-hover group cursor-pointer relative overflow-hidden"
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${accentColor} opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
      <div className="relative p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="p-3 rounded-xl bg-white/[0.06] border border-white/[0.06] group-hover:border-brand-500/20 transition-colors duration-300">
            <Icon className="w-5 h-5 text-brand-400" />
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/60" />
            <span>Active</span>
          </div>
        </div>
        <h3 className="text-white font-semibold text-lg mb-1">{title}</h3>
        <p className="text-gray-400 text-sm leading-relaxed">{description}</p>
        <div className="mt-4 flex items-center gap-2 text-brand-400 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <span>Open module</span>
          <svg className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </motion.div>
  );
}
