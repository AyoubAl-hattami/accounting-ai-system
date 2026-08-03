import { Check } from 'lucide-react';

interface OnboardingStepperProps {
  steps: readonly string[];
  /** Zero-based index of the step being edited. */
  current: number;
  /** Progress caption, already interpolated. */
  progressLabel: string;
  /** Jumping back is allowed; jumping ahead is not, so unvisited steps are inert. */
  onSelect: (index: number) => void;
}

export default function OnboardingStepper({
  steps,
  current,
  progressLabel,
  onSelect,
}: OnboardingStepperProps) {
  return (
    <nav aria-label={progressLabel} className="card p-4 sm:p-5">
      <p className="overline mb-3">{progressLabel}</p>

      <ol className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-1">
        {steps.map((label, index) => {
          const isDone = index < current;
          const isCurrent = index === current;
          const isReachable = index <= current;

          return (
            <li key={label} className="flex flex-1 items-center gap-2 min-w-0">
              <button
                type="button"
                onClick={() => isReachable && onSelect(index)}
                disabled={!isReachable}
                aria-current={isCurrent ? 'step' : undefined}
                className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-start transition-colors duration-fast ${
                  isReachable
                    ? 'cursor-pointer hover:bg-surface-overlay'
                    : 'cursor-not-allowed'
                }`}
              >
                <span
                  aria-hidden
                  className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold ${
                    isDone
                      ? 'border-transparent bg-primary-solid text-primary-foreground'
                      : isCurrent
                        ? 'border-primary-solid text-primary'
                        : 'border-border text-subtle-foreground'
                  }`}
                >
                  {isDone ? <Check className="h-3.5 w-3.5" /> : index + 1}
                </span>
                <span
                  className={`truncate text-xs font-medium ${
                    isCurrent
                      ? 'text-foreground'
                      : isDone
                        ? 'text-muted-foreground'
                        : 'text-subtle-foreground'
                  }`}
                >
                  {label}
                </span>
              </button>

              {index < steps.length - 1 && (
                <span
                  aria-hidden
                  className={`hidden h-px flex-1 sm:block ${
                    isDone ? 'bg-primary-solid' : 'bg-border-subtle'
                  }`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
