import { motion } from 'framer-motion';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { useI18n } from '../../i18n';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  const { t } = useI18n();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex items-center justify-center py-20"
      role="alert"
    >
      <div className="card max-w-sm p-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg border border-danger-border bg-danger-soft">
          <AlertTriangle className="h-6 w-6 text-danger" />
        </div>
        <h3 className="mb-1.5 text-base font-semibold text-foreground">
          {t.common.connectionError}
        </h3>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {message || t.common.somethingWentWrong}
        </p>
        {onRetry && (
          <button type="button" onClick={onRetry} className="btn btn-secondary mt-6">
            <RefreshCw className="h-4 w-4" />
            {t.common.tryAgain}
          </button>
        )}
      </div>
    </motion.div>
  );
}
