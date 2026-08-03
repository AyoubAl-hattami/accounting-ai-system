import React, { useState, useCallback, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useI18n } from '../../i18n';
import { ToastContext, type Toast, type ToastType } from './useToast';

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const { dir, t } = useI18n();

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

  // A neutral raised surface keeps the message text at full contrast; the tone
  // is carried by the leading rule and the icon instead of the whole panel.
  const icons: Record<ToastType, React.ReactNode> = {
    success: <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-success" />,
    error: <AlertCircle className="h-5 w-5 flex-shrink-0 text-danger" />,
    warning: <AlertTriangle className="h-5 w-5 flex-shrink-0 text-warning" />,
    info: <Info className="h-5 w-5 flex-shrink-0 text-info" />,
  };

  const accents: Record<ToastType, string> = {
    success: 'bg-success',
    error: 'bg-danger',
    warning: 'bg-warning',
    info: 'bg-info',
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className={`pointer-events-none fixed bottom-4 z-[100] flex w-full max-w-sm flex-col gap-2.5 p-4 ${
          dir === 'rtl' ? 'left-4' : 'right-4'
        }`}
      >
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              layout
              role={toast.type === 'error' ? 'alert' : 'status'}
              initial={{ opacity: 0, y: 24, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.92, transition: { duration: 0.15 } }}
              transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
              className="glass pointer-events-auto flex w-full select-none items-start gap-3 overflow-hidden rounded-xl border p-3.5 shadow-floating"
            >
              <span
                aria-hidden
                className={`-my-3.5 -ms-3.5 w-1 self-stretch ${accents[toast.type]}`}
              />
              {icons[toast.type]}
              <div className="flex-1 pt-px text-sm font-medium leading-5 text-foreground">
                {toast.message}
              </div>
              <button
                type="button"
                onClick={() => dismiss(toast.id)}
                aria-label={t.common.close}
                className="-m-1 flex-shrink-0 rounded-md p-1 text-subtle-foreground transition-[color,background-color,transform] duration-fast ease-standard hover:bg-surface-overlay hover:text-foreground active:scale-90"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
