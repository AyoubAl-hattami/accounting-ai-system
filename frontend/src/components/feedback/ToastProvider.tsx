import React, { useState, useCallback, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useI18n } from '../../i18n';
import { ToastContext, type Toast, type ToastType } from './useToast';

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const { dir } = useI18n();

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((message: string, type: ToastType, duration = 4000) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: Toast = { id, message, type, duration };
    setToasts((prev) => [...prev, newToast]);

    if (duration > 0) {
      setTimeout(() => {
        dismiss(id);
      }, duration);
    }
  }, [dismiss]);

  const success = useCallback((message: string, duration?: number) => show(message, 'success', duration), [show]);
  const error = useCallback((message: string, duration?: number) => show(message, 'error', duration), [show]);
  const warning = useCallback((message: string, duration?: number) => show(message, 'warning', duration), [show]);
  const info = useCallback((message: string, duration?: number) => show(message, 'info', duration), [show]);

  const contextValue = useMemo(() => ({
    show,
    success,
    error,
    warning,
    info,
    dismiss
  }), [show, success, error, warning, info, dismiss]);

  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />,
    error: <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />,
    info: <Info className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
  };

  const toastStyles = {
    success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 shadow-emerald-500/5',
    error: 'bg-red-500/10 border-red-500/20 text-red-400 shadow-red-500/5',
    warning: 'bg-amber-500/10 border-amber-500/20 text-amber-400 shadow-amber-500/5',
    info: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400 shadow-indigo-500/5'
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div
        className={`fixed z-[100] flex flex-col gap-2.5 max-w-sm w-full p-4 pointer-events-none ${
          dir === 'rtl' ? 'left-4 bottom-4' : 'right-4 bottom-4'
        }`}
      >
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 30, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.85, transition: { duration: 0.15 } }}
              className={`flex items-start gap-3 p-4 rounded-xl border backdrop-blur-md shadow-xl pointer-events-auto w-full select-none ${toastStyles[toast.type]}`}
            >
              {icons[toast.type]}
              <div className="flex-1 text-sm font-medium leading-5 text-gray-200">
                {toast.message}
              </div>
              <button
                onClick={() => dismiss(toast.id)}
                className="text-gray-400 hover:text-white transition-colors p-0.5 rounded-lg hover:bg-white/[0.04] flex-shrink-0 mt-0.5"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
