import { motion } from 'framer-motion';
import { ShieldOff, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../../i18n';

/**
 * Premium "Access Denied" page shown when a user navigates
 * to a route their role doesn't permit.
 */
export default function AccessDenied() {
  const { t } = useI18n();
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center justify-center py-32 text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-6">
        <ShieldOff className="w-8 h-8 text-red-400" />
      </div>

      <h2 className="text-2xl font-bold text-white mb-2">
        {t.permissions.accessDenied}
      </h2>
      <p className="text-gray-400 text-sm max-w-sm mb-8">
        {t.permissions.noPermissionForPage}
      </p>

      <button
        onClick={() => navigate('/dashboard')}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 text-sm font-medium hover:bg-brand-500/20 transition-all duration-200"
      >
        <ArrowLeft className="w-4 h-4" />
        {t.permissions.backToDashboard}
      </button>
    </motion.div>
  );
}
