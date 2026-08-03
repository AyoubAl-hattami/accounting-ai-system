import type { ReactNode } from 'react';

export interface JournalEntryFact {
  label: string;
  value: ReactNode;
}

interface JournalEntryFactsProps {
  /** Overline shown above the list, used when the facts need naming. */
  caption?: string;
  facts: JournalEntryFact[];
}

/**
 * Read-only recap of the entry a confirmation dialog is about to act on, so
 * the reader can check they picked the right row without closing the dialog.
 */
export default function JournalEntryFacts({ caption, facts }: JournalEntryFactsProps) {
  return (
    <div className="rounded-lg border border-border-subtle bg-surface-muted px-3.5 py-3">
      {caption && <p className="overline mb-2">{caption}</p>}
      <dl className="space-y-2 text-xs">
        {facts.map((fact) => (
          <div key={fact.label} className="flex items-start justify-between gap-4">
            <dt className="flex-shrink-0 text-subtle-foreground">{fact.label}</dt>
            <dd className="min-w-0 truncate text-end text-muted-foreground">{fact.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
