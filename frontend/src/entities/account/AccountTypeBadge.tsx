/**
 * AccountTypeBadge — entity-layer presentational component.
 *
 * Lives in entities/account/ so that report pages and journal pages can render
 * account-type labels without creating cross-feature imports.
 */
interface AccountTypeBadgeProps {
  type: string;
}

// The letter mark keeps the type distinguishable without relying on colour.
const typeTones: Record<string, { tone: string; mark: string }> = {
  asset: { tone: 'tone-info', mark: 'A' },
  liability: { tone: 'tone-warning', mark: 'L' },
  equity: { tone: 'tone-violet', mark: 'E' },
  income: { tone: 'tone-success', mark: 'I' },
  expense: { tone: 'tone-rose', mark: 'X' },
};

export function AccountTypeBadge({ type }: AccountTypeBadgeProps) {
  const { tone, mark } = typeTones[type] ?? { tone: 'tone-neutral', mark: '?' };

  return (
    <span className={`badge badge-uppercase ${tone}`}>
      <span aria-hidden className="font-bold opacity-70">
        {mark}
      </span>
      {type}
    </span>
  );
}
