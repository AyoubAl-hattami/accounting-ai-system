import { useId } from 'react';
import { Search, X } from 'lucide-react';
import { useI18n } from '../../../i18n';

interface ReportSearchFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

/** Account/entry search box shared by the report toolbars. */
export default function ReportSearchField({
  label,
  value,
  onChange,
  placeholder,
}: ReportSearchFieldProps) {
  const { t } = useI18n();
  const id = useId();

  return (
    <div className="min-w-[14rem] flex-1">
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      <div className="relative">
        <Search
          aria-hidden
          className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle-foreground"
        />
        <input
          id={id}
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="input ps-10 pe-9"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange('')}
            aria-label={t.common.clearSearch}
            className="absolute end-2 top-1/2 -translate-y-1/2 rounded p-1 text-subtle-foreground transition-colors hover:text-foreground"
          >
            <X aria-hidden className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
