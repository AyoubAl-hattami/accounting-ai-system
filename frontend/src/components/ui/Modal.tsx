import { useEffect, useId, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, X } from 'lucide-react';
import { useI18n } from '../../i18n';

type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl';

const sizeClass: Record<ModalSize, string> = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  '2xl': 'max-w-6xl',
};

// Dialogs can stack (a picker opened from inside a form dialog). Escape must
// only dismiss the one on top, so every open dialog registers itself here.
const openStack: string[] = [];

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  /** Short line under the title explaining what the dialog will do. */
  description?: string;
  size?: ModalSize;
  /** Action row pinned to the bottom of the panel. */
  footer?: ReactNode;
  /** Submission failure, shown next to the actions rather than scrolled away. */
  error?: string | null;
  /** While true the backdrop and Escape key will not dismiss the dialog. */
  busy?: boolean;
  /** Replaces the default padded scroll area, for dialogs with their own layout. */
  bodyClassName?: string;
  children: ReactNode;
}

/**
 * Dialog shell shared by every modal in the app: backdrop, panel, labelled
 * header and a sticky footer. Rendered in a portal so a modal opened from
 * inside a transformed or scrolled container still covers the viewport.
 */
export default function Modal({
  isOpen,
  onClose,
  title,
  description,
  size = 'sm',
  footer,
  error,
  busy = false,
  bodyClassName,
  children,
}: ModalProps) {
  const { t } = useI18n();
  const instanceId = useId();
  const titleId = `${instanceId}-title`;
  const descriptionId = `${instanceId}-description`;

  useEffect(() => {
    if (!isOpen) return;

    openStack.push(instanceId);

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || busy) return;
      if (openStack[openStack.length - 1] !== instanceId) return;
      onClose();
    };
    document.addEventListener('keydown', onKeyDown);

    // Prevent the page behind the dialog from scrolling with it.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      openStack.splice(openStack.indexOf(instanceId), 1);
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen, busy, onClose, instanceId]);

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => !busy && onClose()}
            className="modal-backdrop"
          />

          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={description ? descriptionId : undefined}
            initial={{ opacity: 0, scale: 0.96, y: 14 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: 8 }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            className={`modal-panel flex max-h-[90vh] flex-col ${sizeClass[size]}`}
          >
            <div className="modal-header">
              <div className="min-w-0">
                <h2 id={titleId} className="text-base font-semibold text-foreground">
                  {title}
                </h2>
                {description && (
                  <p id={descriptionId} className="mt-1 text-xs text-muted-foreground">
                    {description}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={onClose}
                disabled={busy}
                aria-label={t.common.close}
                className="btn-icon -me-2 -mt-1 h-8 w-8 flex-shrink-0"
              >
                <X aria-hidden className="h-4 w-4" />
              </button>
            </div>

            <div className={`min-h-0 flex-1 ${bodyClassName ?? 'overflow-y-auto px-6 py-5'}`}>
              {children}
            </div>

            {error && (
              <div role="alert" className="callout tone-danger mx-6 mb-4 text-xs">
                <AlertCircle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <p className="min-w-0 flex-1">
                  <span className="font-semibold">{t.common.errorLabel}</span> {error}
                </p>
              </div>
            )}

            {footer && <div className="modal-footer">{footer}</div>}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
