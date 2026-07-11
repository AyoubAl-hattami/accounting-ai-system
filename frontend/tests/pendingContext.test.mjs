import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import ts from 'typescript';

function loadPendingContextModule() {
  const source = readFileSync(new URL('../src/features/ai/pendingContext.ts', import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  });
  const module = { exports: {} };
  const fn = new Function('exports', 'module', outputText);
  fn(module.exports, module);
  return module.exports;
}

const pending = {
  company_id: 3,
  transaction_type: 'expense_payment',
  amount: 300,
  description: 'دفعت 300 كهربا',
  debit_account_hint: 'utilities expense',
  credit_account_hint: null,
  income_or_expense_nature: 'utilities',
  counterparty: null,
  payment_source_hint: 'unknown',
  receiving_account_hint: null,
  missing_fields: ['payment_source'],
};

const mod = loadPendingContextModule();

test('stores pending context from a clarification reply', () => {
  const result = mod.getPendingContextFromReply({
    intent: 'clarification',
    pending_transaction: pending,
    pending_context_token: 'signed-token',
  });

  assert.deepEqual(result, {
    pendingTransaction: pending,
    token: 'signed-token',
  });
});

test('does not retain pending context once a preview is returned', () => {
  const result = mod.getPendingContextFromReply({
    intent: 'create_journal_draft',
    suggested_action: { type: 'create_journal_entry_draft' },
    pending_transaction: pending,
    pending_context_token: 'signed-token',
  });

  assert.equal(result, null);
});

test('appends pending context to the next assistant payload', () => {
  const payload = mod.appendPendingContextToPayload(
    { company_id: 3, message: 'الصندوق' },
    { pendingTransaction: pending, token: 'signed-token' },
  );

  assert.equal(payload.company_id, 3);
  assert.equal(payload.message, 'الصندوق');
  assert.deepEqual(payload.pending_transaction, pending);
  assert.equal(payload.pending_context_token, 'signed-token');
});

test('clears pending context for chat deletion and company switch', () => {
  assert.equal(mod.clearPendingContext(), null);
  assert.equal(mod.shouldClearPendingForCompanyChange(3, 4), true);
  assert.equal(mod.shouldClearPendingForCompanyChange(3, 3), false);
});
