import { useId } from 'react';
import { useI18n } from '../../../i18n';

interface ReportDateFieldProps {
  label: string;
  value: string | null;
  onChange: (value: string | null) => void;
  min?: string;
  max?: string;
}

/**
 * Date filter used by the report toolbars. The clear affordance sits beside the
 * label rather than inside the field, because browsers already render their own
 * picker indicator inside `input[type=date]`.
 */
export default function ReportDateField({ label, value, onChange, min, max }: ReportDateFieldProps) {
  const { t } = useI18n();
  const id = useId();

  return (
    <div className="min-w-[11rem] flex-1 sm:flex-none">
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <label htmlFor={id} className="field-label mb-0">
          {label}
        </label>
        {value && (
          <button
            type="button"
            onClick={() => onChange(null)}
            className="text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            {t.common.clear}
          </button>
        )}
      </div>
      <input
        id={id}
        type="date"
        value={value ?? ''}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value || null)}
        className="input"
      />
    </div>
  );
}
