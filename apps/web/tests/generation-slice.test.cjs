'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const component = fs.readFileSync(path.resolve(__dirname, '../app/studio/OutputSelection.tsx'), 'utf8');
const gallery = fs.readFileSync(path.resolve(__dirname, '../app/studio/GenerationGallery.tsx'), 'utf8');
const contract = fs.readFileSync(path.resolve(__dirname, '../app/studio/generation-types.ts'), 'utf8');

test('generation rollout is reversible and uses an idempotency key', () => {
  assert.match(component, /NEXT_PUBLIC_ENABLE_GENERATION_SLICE/);
  assert.match(component, /idempotency_key: key/);
  assert.match(component, /step=generation&run=/);
});

test('generation submission sends every selected product/template pair', () => {
  assert.match(component, /generationSelections = products\.flatMap/);
  assert.match(component, /selections: generationSelections/);
  assert.doesNotMatch(component, /&& total === 1/);
  assert.match(contract, /GenerationSelection/);
});

test('generation run is loaded once as an addressable gallery snapshot', () => {
  assert.match(gallery, /generation-runs\/\$\{encodeURIComponent\(runId\)\}/);
  assert.match(gallery, /run\?\.jobs/);
  assert.match(contract, /GenerationRunDetail/);
});

test('generation gallery includes synchronous review actions', () => {
  assert.match(gallery, /method: 'PUT'/);
  assert.match(gallery, /\/decision/);
  assert.match(gallery, />Reject</);
  assert.match(gallery, /Approve/);
  assert.match(contract, /decision: 'approved' \| 'rejected'/);
});

test('generation gallery exposes per-card loading and run progress', () => {
  assert.doesNotMatch(gallery, /Finding the right light|Adding the final touches/);
  assert.doesNotMatch(gallery, /setInterval\(/);
  assert.match(gallery, /role="progressbar"/);
  assert.match(gallery, /Your image is currently being generated/);
  assert.match(contract, /GenerationProgress/);
});

test('library handoff remains disabled until every generated image is reviewed', () => {
  assert.match(gallery, /counts\.in_progress === 0/);
  assert.match(gallery, /counts\.failed === 0/);
  assert.match(gallery, /counts\.reviewed === counts\.ready/);
  assert.match(gallery, /Proceed to Product Library/);
  assert.match(gallery, /router\.push\('\/products\?view=gallery'\)/);
});
