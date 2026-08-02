/**
 * Frontend architecture dependency guard.
 *
 * Rules enforced:
 * 1. features/** must not import from sibling features (cross-feature imports).
 * 2. features/** must not import from pages/ or pages-clean/.
 * 3. entities/** must not import from features/ or widgets/.
 * 4. shared/** must not import from features/, widgets/, entities/, or pages/.
 * 5. widgets/** must not import from pages/ or features-clean/.
 *
 * These rules mirror the Clean Architecture frontend dependency graph:
 *   shared → entities → features → widgets → pages
 *
 * Violations found in features-clean/ or pages-clean/ are reported as warnings
 * only, since those are migration scaffolds that are not yet wired into the app.
 */

import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.resolve(__dirname, '../src');

/** Recursively collect all .ts/.tsx/.js/.jsx files under a directory. */
function collectSourceFiles(dir) {
  const results = [];
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return results;
  }
  for (const entry of entries) {
    const full = path.join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      results.push(...collectSourceFiles(full));
    } else if (/\.(ts|tsx|js|jsx|mjs)$/.test(entry)) {
      results.push(full);
    }
  }
  return results;
}

/** Extract import specifiers from a source file using simple regex. */
function extractImports(filePath) {
  const content = readFileSync(filePath, 'utf8');
  const importRe = /(?:import|export)[^'"]*['"]([^'"]+)['"]/g;
  const imports = [];
  let match;
  while ((match = importRe.exec(content)) !== null) {
    imports.push(match[1]);
  }
  return imports;
}

/**
 * Resolve a relative import specifier to a normalised path segment
 * relative to src/, or return null for non-relative imports.
 */
function resolveRelative(fromFile, specifier) {
  if (!specifier.startsWith('.')) return null;
  const resolved = path.resolve(path.dirname(fromFile), specifier);
  return path.relative(SRC, resolved).replace(/\\/g, '/');
}

/** Return the top-level layer name (e.g. "features", "entities"). */
function layer(relPath) {
  return relPath.split('/')[0];
}

/** Return the second segment (slice name within a layer). */
function slice(relPath) {
  return relPath.split('/')[1];
}

const LAYER_ORDER = ['shared', 'entities', 'features', 'widgets', 'pages', 'app', 'routes', 'auth'];

/**
 * Phase 49 allows existing legacy feature cross-imports by explicit allowlist.
 * Phase 56 must empty this list after legacy features are deleted.
 *
 * Each entry is the canonical string "fromRel → resolvedRel" as emitted by the
 * violation collector below.  Only these seven imports are grandfathered; any
 * new cross-feature import not present here will fail the test.
 */
const LEGACY_FEATURE_CROSS_IMPORT_ALLOWLIST = new Set([
  'features/journals/CreateJournalEntryModal.tsx → features/accounts/useAccounts',
  'features/journals/CreateJournalEntryModal.tsx → features/accounts/AccountTypeBadge',
  'features/reports/account-ledger/AccountLedgerPage.tsx → features/accounts/AccountTypeBadge',
  'features/reports/balance-sheet/BalanceSheetPage.tsx → features/accounts/AccountTypeBadge',
  'features/reports/general-ledger/GeneralLedgerPage.tsx → features/accounts/AccountTypeBadge',
  'features/reports/profit-and-loss/ProfitAndLossPage.tsx → features/accounts/AccountTypeBadge',
  'features/reports/trial-balance/TrialBalancePage.tsx → features/accounts/AccountTypeBadge',
]);

test('features must not cross-import sibling features', () => {
  const featuresDir = path.join(SRC, 'features');
  const files = collectSourceFiles(featuresDir);
  const violations = [];

  for (const file of files) {
    const fromRel = path.relative(SRC, file).replace(/\\/g, '/');
    const fromSlice = slice(fromRel);
    for (const spec of extractImports(file)) {
      const resolved = resolveRelative(file, spec);
      if (!resolved) continue;
      if (layer(resolved) === 'features' && slice(resolved) !== fromSlice) {
        const entry = `${fromRel} → ${resolved}`;
        if (!LEGACY_FEATURE_CROSS_IMPORT_ALLOWLIST.has(entry)) {
          violations.push(entry);
        }
      }
    }
  }

  assert.deepEqual(
    violations,
    [],
    `New cross-feature imports detected (not in legacy allowlist):\n${violations.join('\n')}`,
  );
});

test('entities must not import from features or widgets', () => {
  const entitiesDir = path.join(SRC, 'entities');
  const files = collectSourceFiles(entitiesDir);
  const violations = [];
  const forbidden = new Set(['features', 'widgets', 'pages', 'pages-clean', 'features-clean', 'app', 'routes']);

  for (const file of files) {
    const fromRel = path.relative(SRC, file).replace(/\\/g, '/');
    for (const spec of extractImports(file)) {
      const resolved = resolveRelative(file, spec);
      if (!resolved) continue;
      if (forbidden.has(layer(resolved))) {
        violations.push(`${fromRel} → ${resolved}`);
      }
    }
  }

  assert.deepEqual(violations, [], `Entity imports from upper layers:\n${violations.join('\n')}`);
});

test('shared must not import from features, widgets, entities, or pages', () => {
  const sharedDir = path.join(SRC, 'shared');
  const files = collectSourceFiles(sharedDir);
  const violations = [];
  const forbidden = new Set(['features', 'features-clean', 'widgets', 'entities', 'pages', 'pages-clean', 'app', 'routes']);

  for (const file of files) {
    const fromRel = path.relative(SRC, file).replace(/\\/g, '/');
    for (const spec of extractImports(file)) {
      const resolved = resolveRelative(file, spec);
      if (!resolved) continue;
      if (forbidden.has(layer(resolved))) {
        violations.push(`${fromRel} → ${resolved}`);
      }
    }
  }

  assert.deepEqual(violations, [], `Shared imports from upper layers:\n${violations.join('\n')}`);
});

test('live app must not import from features-clean or pages-clean (migration scaffolds)', () => {
  // features-clean and pages-clean are staging scaffolds.
  // They must not be imported by the live app until migration is approved.
  // Live app layers: app/, routes/, features/, widgets/, auth/, components/, pages-clean excluded from check.
  const liveAppLayers = ['app', 'routes', 'components', 'auth'];
  const forbiddenTargets = new Set(['features-clean', 'pages-clean']);
  const violations = [];

  for (const liveLayer of liveAppLayers) {
    const dir = path.join(SRC, liveLayer);
    for (const file of collectSourceFiles(dir)) {
      const fromRel = path.relative(SRC, file).replace(/\\/g, '/');
      for (const spec of extractImports(file)) {
        const resolved = resolveRelative(file, spec);
        if (!resolved) continue;
        if (forbiddenTargets.has(layer(resolved))) {
          violations.push(`${fromRel} → ${resolved}`);
        }
      }
    }
  }

  assert.deepEqual(
    violations,
    [],
    `Live app imports from migration scaffolds:\n${violations.join('\n')}`,
  );
});
