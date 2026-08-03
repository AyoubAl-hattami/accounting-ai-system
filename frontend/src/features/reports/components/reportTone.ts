export type ReportTone =
  | 'neutral'
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'violet'
  | 'teal'
  /** The cool accounting pair — a debit is not good news and a credit is not bad. */
  | 'debit'
  | 'credit';

/** Text colour for a figure carrying the given tone. */
export const reportToneText: Record<ReportTone, string> = {
  neutral: 'text-foreground',
  primary: 'text-primary',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
  info: 'text-info',
  violet: 'text-violet',
  teal: 'text-teal',
  debit: 'text-debit',
  credit: 'text-credit',
};
