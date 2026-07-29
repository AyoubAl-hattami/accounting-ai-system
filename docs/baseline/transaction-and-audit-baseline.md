# Transaction and Audit Baseline

## Expected guarantee

For a business operation requiring an audit record:

```text
business mutation + required audit record = one atomic transaction
```

A successful response must not be returned for a mutation that was not committed.
An audit failure must fail and roll back the business mutation. A failed business
mutation must not leave a success audit record.

## Current ownership

The present implementation is transitional:

- Routes obtain the SQLAlchemy session.
- Services query and mutate ORM records and commonly flush.
- `core/database.py` provides flush/rollback support.
- `audit_service.py` stages and/or commits audit records, including an atomic
  audit helper.
- Routes frequently call the audit helper after the service mutation.

This division is current behavior, not the target architecture. Future
unit-of-work migration must map every caller before moving commit ownership.
Globally replacing `commit()` with `flush()` or moving commits without caller
analysis is unsafe.

## Journal atomicity

Rollback-sensitive journal operations include:

- Draft creation and update.
- Opening-balance creation.
- Review.
- Post.
- Reverse.
- Void.

`backend/tests/test_journal_transaction_atomicity.py` covers:

- Creation rollback when audit insertion fails.
- Lifecycle mutation rollback when audit insertion fails.
- Reversal rollback when audit insertion fails.
- Successful mutation committing with exactly one audit event.

These tests are mandatory evidence during journal or transaction refactoring.

## Non-journal atomicity

`backend/tests/test_non_journal_transaction_atomicity.py` covers:

- Account creation rollback on audit failure.
- Fiscal-year creation rollback on audit failure.
- Direct company-user add rollback on audit failure.
- Company and initial membership rollback on audit failure.
- Opening-balance rollback on audit failure.

`test_non_journal_audit_logs.py` verifies successful audit creation for
registration, company creation/update, and default-account seeding.

## Global user and membership mutations

`test_global_user_admin_authorization.py` verifies:

- Global deactivation/reactivation audit scope.
- Company membership removal/restoration isolation.
- Rollback of global and company-access mutations when audit insertion fails.

Global user status and company membership must remain separate transaction
targets.

## Invitation atomicity

`test_invitation_lifecycle_integrity.py` verifies:

- Audit failure rolls back creation, acceptance, and cancellation.
- Acceptance does not duplicate membership or audit records.
- Concurrent duplicate creation has one winner.
- Concurrent double acceptance has one successful terminal outcome.
- Concurrent acceptance and cancellation cannot both win.

Invitation uniqueness, row locking, lifecycle state, and audit persistence must
be evaluated as one consistency boundary.

## Audit log behavior

Required audit records preserve:

- Actor identity.
- Company scope or explicit global scope.
- Action and entity metadata.
- Old/new values where currently recorded.
- Existing descriptions and timestamps.
- No raw invitation token, token hash, passwords, JWTs, provider keys, or secrets.

Audit listing preserves company isolation, filters, ordering, and pagination.
Relevant evidence includes `test_protected_audit_logs.py`,
`test_non_journal_audit_logs.py`, and invitation/security tests.

## Unit-of-work migration acceptance criteria

A future application-owned unit of work is acceptable only when:

- Routes no longer need to commit, without losing any write.
- Repositories do not commit independently.
- Necessary flushes still provide generated IDs and constraint detection.
- Every mutation and required audit record commit exactly once together.
- Any exception rolls back the complete operation.
- Returned ORM/result objects still contain required response fields.
- Existing status codes and integrity-error translations remain unchanged.
- Concurrency behavior remains correct.

## Verification set

At minimum, transaction-related changes require:

- `test_journal_transaction_atomicity.py`
- `test_non_journal_transaction_atomicity.py`
- `test_global_user_admin_authorization.py`
- `test_invitation_lifecycle_integrity.py`
- `test_non_journal_audit_logs.py`
- `test_protected_audit_logs.py`
- The affected feature's normal success and authorization tests
- The full backend suite

No result for these tests was produced while writing this baseline.
