# Accounting Feature Gap Analysis (Phase 69)

Date: 2026-08-02

Methodology: each feature was checked by reading actual backend routes/models
(`backend/app/modules/accounting/routes`, `backend/app/application`,
`backend/app/modules/accounting/models`), frontend features
(`frontend/src/features`, `frontend/src/routes/AppRoutes.tsx`), and by grepping the
whole backend+frontend source tree for domain keywords (`invoice`, `customer`,
`supplier`, `vendor`, `bank`). Status is only marked "present" when there is a route +
model/use-case + (ideally) a test; "partial" when some but not all of that exists.

Legend — Size: S=small (days), M=medium (1-2 weeks), L=large (multi-week).
Risk: relative implementation/data-integrity risk if built carelessly.

---

## Must-have (blocks calling this a real accounting product)

| Feature | Status | Evidence | Business impact | Recommended phase | Size | Risk |
|---|---|---|---|---|---|---|
| Chart of accounts (CRUD, hierarchy, protected accounts) | **Present** | `backend/app/modules/accounting/models/account.py`, `account_routes.py` (protected-field guard at lines 260-278), `frontend/src/features/accounts/AccountsPage.tsx`, `backend/tests/test_protected_accounts.py` | Core requirement — done | n/a | n/a | n/a |
| Journal entries (draft/reviewed/posted/void/reversal, double-entry validation) | **Present** | `backend/app/application/journals/use_cases.py`, `journal_routes.py`, 10+ dedicated test files (`test_journal_*_use_case.py`, `test_sqlalchemy_journal_repository_*.py`) | Core requirement — done | n/a | n/a | n/a |
| Fiscal years/periods | **Present (partial close enforcement)** | `backend/app/application/fiscal/use_cases.py`, `fiscal_routes.py`, `frontend/src/features/settings/FiscalSettingsSection.tsx`, `test_fiscal_year_date_protection.py` | Structure exists; hard period-lock-blocks-posting behavior needs explicit verification | 73 | S (verify) / M (harden) | Medium |
| Opening balances | **Present** | `CreateOpeningBalanceCommand` in `backend/app/application/journals/dto.py`, `OpeningBalanceCreate` schema, `test_journal_opening_balance_use_case.py`, `test_opening_balance_workflow.py` | Core requirement — done | n/a | n/a | n/a |
| Audit trail | **Present** | `prepare_audit_log`/`create_audit_log` calls in `auth_routes.py`, `journal_routes.py`; `AuditLogsPage.tsx`; `test_protected_audit_logs.py`, `test_non_journal_audit_logs.py` | Core requirement — done for existing entities; must be extended to any new subledger entities | 71-74 (extend per feature) | S per feature | Low |
| Trial balance / P&L / balance sheet / general ledger / account ledger reports | **Present** | `backend/app/modules/accounting/routes/report_routes.py`, 5 matching frontend pages under `frontend/src/features/reports/`, `test_reports_smoke.py`, `test_report_use_cases.py` | Core requirement — done | n/a | n/a | n/a |
| CSV export | **Present** | `backend/app/infrastructure/exports/csv_renderer.py`, `report_export_routes.py`, `test_report_csv_exports.py` | Core requirement — done | n/a | n/a | n/a |
| PDF export | **Present** | `backend/app/infrastructure/exports/pdf_renderer.py`, `report_pdf_routes.py`, `test_report_pdf_exports.py` | Core requirement — done | n/a | n/a | n/a |
| Numbering sequences | **Partial** | Journal entries have an entry number (`get_journal_entry_by_no` in `journal_routes.py`), but there is no generic/configurable numbering-sequence framework for future document types (invoices, bills) | Needed before invoices/bills can get sequential numbers | 71 | S | Low |
| Customers (AR master data) | **Missing** | No matches for "customer" in backend or frontend product code (`grep -ril "customer" backend/app frontend/src` → empty except AI-prompt text) | Cannot track who owes the business money | 71 | M | Medium |
| Suppliers/vendors (AP master data) | **Missing** | No matches for "supplier"/"vendor" anywhere in backend/frontend product code | Cannot track who the business owes money to | 71 | M | Medium |
| Sales invoices | **Missing** | No invoice model/route/schema/page exists anywhere | No way to bill customers — the single most expected accounting-app feature | 71 | L | Medium-High (must post correctly to GL) |
| Purchase bills | **Missing** | No bill model/route/schema/page exists anywhere | No way to record supplier obligations | 71 | L | Medium-High |
| Payments (customer receipts / supplier payments) | **Missing** | No payment model/route anywhere | Cannot apply cash against invoices/bills, cannot show AR/AP aging | 72 | L | High (must reconcile against invoices/bills and post correctly) |
| Bank accounts / bank transactions | **Missing** | No matches for "bank" in backend or frontend product code | No cash-position visibility, no reconciliation possible | 72 | M | Medium |
| Bank reconciliation | **Missing** | Depends on bank transactions, which don't exist | Cannot verify books against bank statements — a baseline expectation for any bookkeeping tool | 72 | L | High (data-integrity sensitive) |
| VAT/tax handling | **Missing** | No tax code/tax rate model or calculation logic found anywhere in `backend/app` | Cannot legally invoice in most jurisdictions without tax support | 73 | L | High (compliance-sensitive) |
| Attachments (receipts/documents on transactions) | **Missing** | No file/attachment storage model or route found | No audit-supporting documentation trail (common audit requirement) | 74 | M | Medium |
| Fiscal close / period lock (enforced) | **Partial → needs hardening** | `FiscalPeriodDTO.status` exists (`backend/app/application/fiscal/dto.py`) but a verified "reject posting into closed period" enforcement path was not confirmed in this pass | Prevents backdated tampering with closed books — a core financial-integrity control | 73 | M | High if wrong (must not accidentally block legitimate corrections) |
| Opening balances / multi-currency | **Partial** | `Company.base_currency` is a single string field (`backend/app/modules/accounting/models/company.py:20`); no FX rates, no per-transaction currency, no conversion | Blocks any multi-currency business (imports/exports, foreign suppliers) | Post-73 (own phase or fold into 73) | L | High (affects every report and every posting) |
| Audit trail completeness across future entities | **N/A yet** | Existing audit infra is solid; must be wired into every new entity (invoices, bills, payments, bank txns) as they're built | Compliance requirement | 71-74 (per feature) | S per feature | Low |
| Export/import (data portability) | **Partial** | Export exists (CSV/PDF for reports); **no import** functionality found anywhere (no CSV import route/page) | Onboarding existing customers requires bulk import of COA/opening balances/history | 74 | M | Medium (data validation heavy) |

## Should-have

| Feature | Status | Evidence | Business impact | Recommended phase | Size | Risk |
|---|---|---|---|---|---|---|
| Recurring journal entries | **Missing** | No scheduler/recurrence model found in `backend/app/application/journals` | Manual re-entry of monthly accruals/depreciation is tedious | Post-74 | M | Low |
| Approval workflow (beyond draft/reviewed/posted) | **Partial** | The 3-state journal lifecycle (`review`/`post` use cases) is itself a lightweight approval workflow; no configurable multi-step approval chain exists | Larger orgs may need multi-approver sign-off | Post-74 | M | Low |
| Advanced permissions | **Partial** | Role-based checks exist (`ensure_company_access`, `test_rbac_permission_matrix.py`) but granular per-field or per-report permissions were not evaluated in depth | Larger orgs may need finer-grained access control | Post-74 | M | Medium |
| Dashboard KPIs | **Present (basic)** | `frontend/src/features/dashboard/DashboardPage.tsx` uses `useDashboardData`, `recharts` bar charts, `DashboardMetricCard` | Existing but likely needs AR/AP/cash KPIs once those subledgers exist | 71-72 (extend) | S | Low |
| CSV import | **Missing** | See "Export/import" above | Same as above | 74 | M | Medium |
| Accountant review mode | **Missing** | No distinct "accountant" role/view found beyond standard RBAC roles | Nice differentiator but not core-blocking | Post-74 | M | Low |
| Company settings (broader) | **Partial** | `frontend/src/features/settings/SettingsPage.tsx` + `FiscalSettingsSection.tsx` exist, cover fiscal settings; broader settings (tax defaults, numbering, branding) don't exist yet because their underlying features don't exist | Needed once invoices/tax exist | 71-73 (extend per feature) | S per feature | Low |
| PDF templates (invoices) | **Missing** | PDF rendering infra exists for reports (`pdf_renderer.py`) and could likely be extended, but no invoice template exists because invoices don't exist | Needed once invoices exist | 74 | M | Low |
| Email sending | **Missing** | No email/SMTP integration found anywhere in `backend/app` | Needed for sending invoices, invitations (invitations currently appear link/token based) | 74 | M | Medium (deliverability, secrets) |
| Backup/restore UI | **Missing** | No backup/restore scripts or UI found under `scripts/` or `docs/` | Operational risk for a production financial system | 75 | M | Medium |

## Nice-to-have

| Feature | Status | Evidence | Business impact | Recommended phase | Size | Risk |
|---|---|---|---|---|---|---|
| OCR (receipt/document scanning) | **Missing** | No OCR integration found | Convenience feature, not core | Post-76 | L | Low |
| AI categorization / anomaly detection | **Partial (adjacent)** | AI journal-suggestion (`ai_provider_factory.py`, rules/openai/gemini providers) is a related but distinct capability; no anomaly-detection logic found | Differentiator, not core | 76 | L | Medium |
| Integrations (bank feeds, payment gateways) | **Missing** | No integration code found | Valuable long-term, not core-blocking | Post-76 | L | Medium |
| Mobile polish | **Not assessed** | Responsive risk noted generally for frontend pages but no dedicated mobile audit performed in this pass | Nice-to-have | Post-76 | M | Low |
| Advanced analytics | **Missing** | Dashboard has basic charts only (`DashboardPage.tsx`); no analytics/forecasting layer | Differentiator, not core | Post-76 | L | Low |
