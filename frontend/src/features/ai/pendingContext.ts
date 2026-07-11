export interface PendingTransaction {
  company_id: number;
  transaction_type: string;
  amount: number;
  description: string;
  debit_account_hint?: string | null;
  credit_account_hint?: string | null;
  income_or_expense_nature?: string | null;
  counterparty?: string | null;
  payment_source_hint?: string | null;
  receiving_account_hint?: string | null;
  missing_fields: string[];
}

export interface ClarificationOption {
  label: string;
  value: string;
}

export interface PendingContextState {
  pendingTransaction: PendingTransaction;
  token: string;
}

export interface AssistantReplyWithPending {
  suggested_action?: unknown | null;
  pending_transaction?: PendingTransaction | null;
  pending_context_token?: string | null;
}

export function getPendingContextFromReply(
  reply: AssistantReplyWithPending,
): PendingContextState | null {
  if (reply.suggested_action) return null;
  if (!reply.pending_transaction || !reply.pending_context_token) return null;

  return {
    pendingTransaction: reply.pending_transaction,
    token: reply.pending_context_token,
  };
}

export function appendPendingContextToPayload<T extends Record<string, unknown>>(
  payload: T,
  pendingContext: PendingContextState | null,
): T & {
  pending_transaction?: PendingTransaction;
  pending_context_token?: string;
} {
  if (!pendingContext) return payload;

  return {
    ...payload,
    pending_transaction: pendingContext.pendingTransaction,
    pending_context_token: pendingContext.token,
  };
}

export function clearPendingContext(): null {
  return null;
}

export function shouldClearPendingForCompanyChange(
  previousCompanyId: number | null,
  nextCompanyId: number | null,
): boolean {
  return previousCompanyId !== nextCompanyId;
}
