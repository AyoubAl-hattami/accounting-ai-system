import { motion } from 'framer-motion';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { useI18n } from '../../i18n';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({
  message,
  onRetry,
}: ErrorStateProps) {
  const { t } = useI18n();
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex items-center justify-center py-20"
    >
      <div className="glass-panel p-8 max-w-sm text-center">
        <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-7 h-7 text-red-400" />
        </div>
        <h3 className="text-white font-semibold text-lg mb-2">{t.common.connectionError}</h3>
        <p className="text-gray-400 text-sm leading-relaxed mb-5">{message || t.common.somethingWentWrong}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/[0.06] border border-white/[0.08] text-gray-200 text-sm font-medium hover:bg-white/[0.1] hover:border-white/[0.12] transition-all duration-200"
          >
            <RefreshCw className="w-4 h-4" />
            {t.common.tryAgain}
          </button>
        )}
      </div>
    </motion.div>
  );
}
