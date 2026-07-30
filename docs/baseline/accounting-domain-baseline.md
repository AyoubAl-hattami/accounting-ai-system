# Accounting Domain Baseline

This document records the Phase 0 accounting expectations, not a proposed
redesign. The legacy service filenames from that baseline have since been
removed. Current implementation seams are the accounting routes,
`backend/app/application` use cases and ports, and SQLAlchemy repositories under
`backend/app/infrastructure/database/sqlalchemy/repositories`.

## Journal balance and lines

- A journal entry must satisfy the current debit/credit balancing rules before
  it can proceed through its lifecycle.
- Referenced accounts must exist, be active where required, and belong to the
  selected company.
- Debit and credit values retain their current non-negative/positive validation,
  precision, and serialization behavior.
- Entry totals are derived consistently from journal lines.
- A refactor must not silently round, change decimal handling, swap sign
  conventions, or allow cross-company accounts.

Relevant evidence includes `test_journal_lifecycle_policy.py`,
`test_protected_journal_entries.py`, `test_fiscal_accounting_controls.py`, and
`test_opening_balance_workflow.py`.

## Journal lifecycle

Current status vocabulary:

- `draft`
- `reviewed`
- `posted`
- `reversed`
- `void`

Baseline behavior:

- New ordinary and opening-balance entries are created through their dedicated
  endpoints.
- Only drafts may be updated.
- Review is an explicit lifecycle action.
- Posting follows the current review/post policy; direct invalid transitions are
  rejected.
- Void and reverse are distinct actions with distinct eligibility rules.
- Duplicate reversal is rejected.
- Lifecycle errors preserve their current conflict/bad-request behavior.

`test_journal_lifecycle_policy.py` explicitly covers draft/review/post,
disallowed direct posting, void restrictions, reversal line swapping, duplicate
reversal, and unauthenticated mutation denial.

## Posted-entry immutability

Posted entries are authoritative ledger facts. They must not be edited as drafts.
Corrections follow the current reversal/void policy rather than mutating posted
history. Refactoring persistence or domain entities must not weaken this
invariant.

## Reversal behavior

- Reversal is permitted only for entries currently eligible under the lifecycle
  policy.
- Reversal lines swap debit and credit amounts.
- The reversal retains the existing relationship to its original entry.
- An original entry cannot receive multiple successful reversals.
- Reversal and audit persistence are atomic.

Evidence: `test_journal_lifecycle_policy.py` and
`test_journal_transaction_atomicity.py`.

## Opening balances

- Opening balances use `POST /journal-entries/opening-balance`.
- The company, account, fiscal year, and fiscal period must be eligible.
- The entry date must resolve to an open fiscal year and open fiscal period.
- The period must belong to the resolved fiscal year.
- Opening entries follow the documented review/post workflow rather than
  bypassing lifecycle safety.
- Creation and required audit persistence are atomic.

Evidence: `test_opening_balance_workflow.py`,
`test_non_journal_transaction_atomicity.py`, and fiscal control tests.

## Fiscal years and periods

For journal creation, opening balance, and relevant updates:

- A fiscal year must exist for the entry date.
- The fiscal year must be open.
- A fiscal period must exist for the entry date.
- The fiscal period must be open.
- The fiscal period must belong to the resolved fiscal year.

Current errors such as "No fiscal year found", "Fiscal year is not open",
"No fiscal period found", "Fiscal period is not open", and period/year mismatch
must retain their API behavior unless explicitly approved.

Fiscal ownership, date ranges, overlap constraints, and status transitions are
covered by `test_protected_fiscal.py`, `test_fiscal_accounting_controls.py`, and
`test_fiscal_lifecycle_controls.py` where present.

## Account and company isolation

- Accounts, journals, fiscal records, and reports are scoped to a company.
- A request must not reference or reveal an account, creator, entry, fiscal
  record, or report fact from another company.
- Platform-superuser access still passes through explicit company context.
- Historical journal creator fallback must not expose a creator across company
  boundaries.

Evidence: `test_protected_accounts.py`,
`test_protected_journal_entries.py`, `test_protected_reports.py`, and
`test_rbac_permission_matrix.py`.

## Report population

Official financial reports use the current official-entry filter. Draft entries
do not affect official reports; posted entries do. Reversed/void handling must
remain consistent with current service logic.

`test_gemini_assistant.py` includes explicit evidence that an assistant-created
draft does not affect profit and loss and that a posted journal affects trial
balance.

## Trial balance

- Includes the current company/date-scoped official entries.
- Debit and credit totals use current account and line semantics.
- Total debit and total credit are expected to balance for valid posted data.
- Per-account debit/credit totals and balance columns retain their current sign
  convention and response fields.

Evidence: `test_protected_reports.py`, `test_reports_smoke.py`, and trial-balance
CSV/PDF tests. Exact numeric fixtures should be recorded from the suite/reference
database rather than invented here.

## Profit and loss

- Uses the current income/revenue and expense classification.
- Draft entries do not affect official profit-and-loss results.
- Date filtering and fiscal-year requirements retain current behavior.
- Revenue, expenses, and net result retain current sign and aggregation
  conventions.

Evidence: `test_reports_smoke.py`, export tests,
`test_gemini_assistant_profit.py`, and profit/explanation assistant tests.

## Balance sheet

- Uses current asset, liability, and equity classifications.
- Uses official entries and the current as-of/date behavior.
- Totals and the accounting-equation presentation retain current semantics.
- Assistant explanations must be grounded in the same report data.

Evidence: `test_reports_smoke.py`, balance-sheet export tests, and
`TestExplainBalanceSheet` in `test_gemini_assistant_explain.py`.

## Account ledger

- Requires a company-owned account.
- Preserves opening balance, movement ordering, debit/credit totals, running or
  closing balance behavior, and date filters.
- Must not expose entries from other companies.

Evidence: account-ledger CSV/PDF tests and report smoke tests.

## General ledger

- Preserves account ordering/grouping, official-entry selection, movement
  details, totals, and date filters.
- Company isolation and authentication remain mandatory.

Evidence: general-ledger CSV/PDF tests and report smoke tests.

## Numeric-fixture policy

No new exact values are defined in this document. Before report or journal
refactoring, capture representative test fixture outputs and reconcile them
exactly after the change. Existing tests and their data setup remain the source
for numeric examples.
