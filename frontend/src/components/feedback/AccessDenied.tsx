import { motion } from 'framer-motion';
import { ArrowLeft, ShieldOff } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../../i18n';

/**
 * Shown when a user navigates to a route their role doesn't permit.
 */
export default function AccessDenied() {
  const { t } = useI18n();
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex items-center justify-center py-24"
      role="alert"
    >
      <div className="card max-w-md p-10 text-center">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-lg border border-danger-border bg-danger-soft">
          <ShieldOff className="h-6 w-6 text-danger" />
        </div>

        <h2 className="mb-2 text-xl font-semibold text-foreground">
          {t.permissions.accessDenied}
        </h2>
        <p className="mx-auto max-w-sm text-sm leading-relaxed text-muted-foreground">
          {t.permissions.noPermissionForPage}
        </p>

        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          className="btn btn-secondary mt-7"
        >
          <ArrowLeft className="h-4 w-4 rtl:rotate-180" />
          {t.permissions.backToDashboard}
        </button>
      </div>
    </motion.div>
  );
}
