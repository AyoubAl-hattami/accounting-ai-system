import { useId } from 'react';
import { useI18n } from '../../../i18n';

interface ReportCurrencyFieldProps {
  value: string | null;
  options: string[];
  onChange: (value: string) => void;
}

/**
 * Currency picker for the report toolbars.
 *
 * A report is always in exactly one currency, so this is a choice between
 * reports rather than a filter over one: there is no "all" option, because a
 * total across currencies is the number this whole feature exists to prevent.
 */
export default function ReportCurrencyField({ value, options, onChange }: ReportCurrencyFieldProps) {
  const { t } = useI18n();
  const id = useId();

  return (
    <div className="min-w-[8rem] flex-none">
      <label htmlFor={id} className="field-label">
        {t.reports.shared.currency}
      </label>
      <select
        id={id}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        className="select numeric"
      >
        {options.map((code) => (
          <option key={code} value={code}>
            {code}
          </option>
        ))}
      </select>
    </div>
  );
}
