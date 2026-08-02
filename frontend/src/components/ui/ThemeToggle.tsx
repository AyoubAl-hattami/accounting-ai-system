import { Monitor, Moon, Sun } from 'lucide-react';
import { useI18n } from '../../i18n';
import { useTheme, type ThemePreference } from '../../theme';

/**
 * Compact icon button for the top bar. Flips light ⇄ dark and pins the choice.
 */
export function ThemeToggleButton() {
  const { t } = useI18n();
  const { theme, toggleTheme } = useTheme();
  const goingDark = theme === 'light';
  const label = goingDark ? t.theme.switchToDark : t.theme.switchToLight;

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="btn-icon"
      title={label}
      aria-label={label}
    >
      {goingDark ? <Moon className="h-[18px] w-[18px]" /> : <Sun className="h-[18px] w-[18px]" />}
    </button>
  );
}

const OPTIONS: { value: ThemePreference; icon: typeof Sun }[] = [
  { value: 'light', icon: Sun },
  { value: 'dark', icon: Moon },
  { value: 'system', icon: Monitor },
];

/**
 * Three-way segmented control for Settings, where "follow the system" needs to
 * be selectable explicitly rather than inferred from a toggle.
 */
export function ThemeSegmentedControl() {
  const { t } = useI18n();
  const { preference, setPreference } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label={t.theme.appearance}
      className="inline-flex rounded-lg border border-border bg-surface-muted p-1"
    >
      {OPTIONS.map(({ value, icon: Icon }) => {
        const selected = preference === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => setPreference(value)}
            className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              selected
                ? 'bg-surface text-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {t.theme[value]}
          </button>
        );
      })}
    </div>
  );
}
