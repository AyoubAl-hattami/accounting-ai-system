import { Ban, CheckCircle2, FileEdit, RotateCcw, ShieldCheck } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { JournalEntryStatus } from '../../api/types';
import { useI18n } from '../../i18n';

interface JournalStatusBadgeProps {
  status: JournalEntryStatus;
}

// Each status carries an icon so the state is legible without colour vision.
const statusTones: Record<JournalEntryStatus, { tone: string; icon: LucideIcon }> = {
  draft: { tone: 'tone-neutral', icon: FileEdit },
  reviewed: { tone: 'tone-warning', icon: ShieldCheck },
  posted: { tone: 'tone-success', icon: CheckCircle2 },
  void: { tone: 'tone-danger', icon: Ban },
  reversed: { tone: 'tone-violet', icon: RotateCcw },
};

export default function JournalStatusBadge({ status }: JournalStatusBadgeProps) {
  const { t } = useI18n();
  const { tone, icon: Icon } = statusTones[status] ?? { tone: 'tone-neutral', icon: FileEdit };
  const label = {
    draft: t.journals.draft,
    reviewed: t.journals.reviewed,
    posted: t.journals.posted,
    void: t.journals.voided,
    reversed: t.journals.reversed,
  }[status];

  return (
    <span className={`badge badge-uppercase ${tone}`}>
      <Icon aria-hidden className="h-3 w-3" />
      {label ?? status}
    </span>
  );
}
