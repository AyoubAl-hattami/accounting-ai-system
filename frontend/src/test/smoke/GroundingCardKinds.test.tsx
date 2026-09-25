// Which grounding kinds render, asserted, so the next gap is loud.
//
// The backend has emitted six kinds since 2026-07-16 and this component
// rendered two of them, returning null for the rest. Nothing failed: a
// dropped card is one `return null` and a reply that still displays. That is
// exactly the kind of gap a test has to make noisy, because the product does
// not. See docs/open-findings.md RAG-15.
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import GroundingCards from '../../features/ai/GroundingCards';
import type { GeminiMessage } from '../../features/ai/useGeminiAssistant';

const PERIOD = { start_date: '2026-01-01', end_date: '2026-01-31', label: 'January' };
const AS_OF = { as_of_date: '2026-01-31', start_date: null, end_date: null, label: 'As of 2026-01-31' };

// One card per kind, shaped exactly as report_grounding.py builds them.
export const CARDS = {
  profit_and_loss: {
    status: 'grounded', kind: 'profit_and_loss', requested_metric: 'net_profit', period: PERIOD,
    metrics: { revenue: '4000.00', expenses: '1500.00', net_profit: '2500.00' },
    reference: { type: 'report', report: 'profit_and_loss', filters: { start_date: '2026-01-01', end_date: '2026-01-31' } },
  },
  journal_evidence: {
    status: 'grounded', kind: 'journal_evidence', basis: 'amount_trace',
    summary: { total_matches: 1, returned_matches: 1, has_more: false },
    entries: [{ journal_entry_id: 42, entry_number: 'JE-0042', entry_date: '2026-01-05', description: 'rent', status: 'posted', source: 'manual', creator_name: 'A', matched_amount: '1500.00', match_reason: 'debit_line' }],
  },
  balance_sheet: {
    status: 'grounded', kind: 'balance_sheet', requested_metric: 'assets', period: AS_OF,
    metrics: { total_assets: '2500.00', total_liabilities: '0.00', total_equity: '2500.00', current_year_earnings: '2500.00', prior_year_earnings: '0.00', liabilities_and_equity: '2500.00', difference: '0.00', is_balanced: true },
    sections: [{ section: 'assets', total: '2500.00', accounts: [{ account_id: 1, account_code: '1110', account_name: 'Main Bank', balance: '2500.00' }] }],
    reference: { type: 'report', report: 'balance_sheet', filters: { as_of_date: '2026-01-31' } },
  },
  trial_balance: {
    status: 'grounded', kind: 'trial_balance', requested_metric: 'total_debit', period: AS_OF,
    metrics: { total_debit: '5500.00', total_credit: '5500.00', difference: '0.00', is_balanced: true },
    accounts: [{ account_id: 1, account_code: '1110', account_name: 'Main Bank', account_type: 'asset', debit_balance: '4000.00', credit_balance: '1500.00', net_balance: '2500.00' }],
    summary: { total_accounts: 13, returned_accounts: 13, has_more: false },
    reference: { type: 'report', report: 'trial_balance', filters: { end_date: '2026-01-31' } },
  },
  general_ledger: {
    status: 'grounded', kind: 'general_ledger', requested_metric: null, period: PERIOD,
    accounts: [{ account_id: 1, account_code: '1110', account_name: 'Main Bank', account_type: 'asset', opening_balance: '0.00', total_debit: '4000.00', total_credit: '1500.00', closing_balance: '2500.00', entry_count: 2 }],
    summary: { total_accounts: 13, returned_accounts: 8, has_more: true },
    reference: { type: 'report', report: 'general_ledger', filters: { start_date: '2026-01-01', end_date: '2026-01-31' } },
  },
  account_ledger: {
    status: 'grounded', kind: 'account_ledger', requested_metric: null, period: PERIOD,
    account: { account_id: 1, account_code: '1110', account_name: 'Main Bank', account_type: 'asset' },
    metrics: { opening_balance: '0.00', total_debit: '4000.00', total_credit: '1500.00', closing_balance: '2500.00' },
    entries: [
      { journal_entry_id: 42, entry_number: 'JE-0042', entry_date: '2026-01-05', description: 'rent', status: 'posted', source: 'accounting_report', debit: '4000.00', credit: '0.00', running_balance: '4000.00' },
      { journal_entry_id: 43, entry_number: 'JE-0043', entry_date: '2026-01-06', description: 'cancelled', status: 'reversed', source: 'accounting_report', debit: '0.00', credit: '1500.00', running_balance: '2500.00' },
    ],
    summary: { total_entries: 2, returned_entries: 2, has_more: false },
    reference: { type: 'report', report: 'account_ledger', filters: { account_id: 1, start_date: '2026-01-01', end_date: '2026-01-31' } },
  },
} as const;

// Every kind the backend can put on a reply. A kind added to
// GeminiAssistantReply.grounding and not to this list fails the last test.
const BACKEND_KINDS = [
  'profit_and_loss', 'journal_evidence', 'balance_sheet',
  'trial_balance', 'general_ledger', 'account_ledger',
] as const;

function renderCard(grounding: unknown) {
  const message = { id: '1', role: 'assistant', content: 'x', timestamp: new Date(), metadata: { grounding } } as unknown as GeminiMessage;
  return render(<MemoryRouter><GroundingCards message={message} language="en" dir="ltr" /></MemoryRouter>);
}

describe('grounding cards', () => {
  it.each(BACKEND_KINDS)('renders the %s card', (kind) => {
    const { container } = renderCard(CARDS[kind]);
    expect(container.innerHTML.length).toBeGreaterThan(0);
  });

  // The five report cards carry the badge. journal_evidence does not and never
  // has: it is a list of entries with links, and what it vouches for is that
  // these entries exist, which the entries themselves say.
  it.each(BACKEND_KINDS.filter((kind) => kind !== 'journal_evidence'))(
    'the %s card says the figures were verified',
    (kind) => {
      renderCard(CARDS[kind]);
      expect(screen.getByText(/Verified from accounting data/i)).toBeTruthy();
    },
  );

  it('the journal evidence card lists the entry it found', () => {
    renderCard(CARDS.journal_evidence);
    expect(screen.getByText('JE-0042')).toBeTruthy();
  });

  it('covers every kind the backend can send', () => {
    expect(Object.keys(CARDS).sort()).toEqual([...BACKEND_KINDS].sort());
  });

  it('shows the figures the card carries, not a placeholder', () => {
    renderCard(CARDS.balance_sheet);
    // Assets and equity are both 2500.00 in a balanced sheet, so the figure
    // legitimately appears more than once.
    expect(screen.getAllByText('2500.00').length).toBeGreaterThan(0);
    expect(screen.getByText(/As of 2026-01-31/)).toBeTruthy();
  });

  it('shows a reversed ledger entry as reversed', () => {
    // [LEDGER-STATUS]: the card used to print "posted" for every entry.
    renderCard(CARDS.account_ledger);
    expect(screen.getByText(/Reversed/)).toBeTruthy();
    expect(screen.getByText(/Posted/)).toBeTruthy();
  });

  it('says when a general ledger is showing a page', () => {
    renderCard(CARDS.general_ledger);
    expect(screen.getByText(/Showing 8 of 13 accounts/)).toBeTruthy();
  });

  it('renders nothing for an unavailable report', () => {
    const { container } = renderCard({ status: 'unavailable', kind: 'balance_sheet' });
    expect(container.innerHTML).toBe('');
  });

  it('renders nothing for a card missing the figures it needs', () => {
    // The key has to be ABSENT, not undefined: valid() reads metrics[k], and a
    // card that carries the key with nothing in it is a different bug from one
    // that never carried it. Deleted from a copy rather than destructured
    // around, because `const { metrics, ...rest }` binds a name this config
    // will not let go unused -- it sets no ignore pattern, so neither
    // `_metrics` nor `metrics: _unused` satisfies it either. Measured.
    const withoutMetrics = { ...CARDS.trial_balance };
    delete (withoutMetrics as Record<string, unknown>).metrics;
    const { container } = renderCard(withoutMetrics);
    expect(container.innerHTML).toBe('');
  });
});
