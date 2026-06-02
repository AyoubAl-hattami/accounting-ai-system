import { motion } from 'framer-motion';

export default function LoadingState() {
  return (
    <div className="space-y-6">
      {/* Skeleton metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.05 }}
            className="glass-panel p-5"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-white/[0.04] animate-pulse" />
              <div className="w-14 h-4 rounded-full bg-white/[0.04] animate-pulse" />
            </div>
            <div className="w-20 h-3 rounded bg-white/[0.04] animate-pulse mb-2" />
            <div className="w-28 h-6 rounded bg-white/[0.06] animate-pulse" />
          </motion.div>
        ))}
      </div>

      {/* Skeleton module cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 + i * 0.05 }}
            className="glass-panel p-6"
          >
            <div className="w-10 h-10 rounded-xl bg-white/[0.04] animate-pulse mb-4" />
            <div className="w-32 h-4 rounded bg-white/[0.06] animate-pulse mb-2" />
            <div className="w-full h-3 rounded bg-white/[0.04] animate-pulse mb-1" />
            <div className="w-3/4 h-3 rounded bg-white/[0.04] animate-pulse" />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
