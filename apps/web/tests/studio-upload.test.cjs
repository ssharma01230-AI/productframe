'use strict';

// Run with: node --test apps/web/tests/studio-upload.test.cjs
// Exercise the real validation and Server Action with isolated auth/network mocks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');

function loadModule(filename, globals = {}) {
  const sourcePath = path.resolve(__dirname, '../app/studio', filename);
  const compiled = ts.transpileModule(fs.readFileSync(sourcePath, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const loaded = { exports: {} };
  vm.runInNewContext(compiled, { module: loaded, exports: loaded.exports, ...globals }, { filename: sourcePath });
  return loaded.exports;
}

const { validateUploadImages, MAX_UPLOAD_BYTES, MAX_UPLOAD_IMAGES } = loadModule('upload-constraints.ts');
const image = (overrides = {}) => ({ name: 'front.jpg', type: 'image/jpeg', size: 100, ...overrides });

test('upload validation accepts supported image types and the 50-image boundary', () => {
  assert.equal(validateUploadImages(['image/jpeg', 'image/png', 'image/webp'].map(type => image({ type }))), null);
  assert.equal(validateUploadImages(Array.from({ length: MAX_UPLOAD_IMAGES }, () => image())), null);
});

test('upload validation requires files and rejects over-capacity batches', () => {
  assert.match(validateUploadImages([]), /at least one image/);
  assert.match(validateUploadImages(Array.from({ length: MAX_UPLOAD_IMAGES + 1 }, () => image())), /up to 50 images/);
});

test('upload validation rejects unsupported and empty files', () => {
  for (const type of ['image/svg+xml', 'image/gif', 'application/pdf', '']) {
    assert.match(validateUploadImages([image(), image({ type })]), /JPG, PNG or WebP/);
  }
  assert.match(validateUploadImages([image({ size: 0 })]), /empty/);
});

test('upload validation checks the combined size without allocating large files', () => {
  assert.equal(validateUploadImages([image({ size: MAX_UPLOAD_BYTES / 2 }), image({ size: MAX_UPLOAD_BYTES / 2 })]), null);
  assert.match(validateUploadImages([image({ size: MAX_UPLOAD_BYTES }), image({ size: 1 })]), /500 MB/);
});

function actionFixture({ token = 'fixture-token', failAt } = {}) {
  const calls = [];
  let assetCount = 0;
  const action = loadModule('actions.ts', {
    File,
    process: { env: { NEXT_PUBLIC_API_URL: 'https://api.example.invalid' } },
    require(name) {
      if (name === './upload-constraints') return { validateUploadImages };
      if (name === '@clerk/nextjs/server') return { auth: async () => ({ getToken: async () => token }) };
      if (name === 'next/navigation') return { redirect(location) { throw Object.assign(new Error('Fixture redirect'), { location }); } };
      throw new Error('Unexpected import: ' + name);
    },
    async fetch(url, options) {
      calls.push({ url, ...options });
      if (calls.length === failAt) return { ok: false, status: 503 };
      if (url === 'https://api.example.invalid/products') return { ok: true, json: async () => ({ id: 'upload-product' }) };
      if (url === 'https://api.example.invalid/products/upload-product/source-assets/upload-url') {
        assetCount += 1;
        return { ok: true, json: async () => ({ asset_id: 'asset-' + assetCount, upload_url: 'https://storage.example.invalid/' + assetCount }) };
      }
      if (url.startsWith('https://storage.example.invalid/')) return { ok: true };
      if (url === 'https://api.example.invalid/analysis-jobs') return { ok: true, json: async () => ({ id: 'analysis-fixture' }) };
      throw new Error('Unexpected fetch: ' + url);
    },
  });
  return { calls, action: action.createProductAnalysisJob };
}

function uploadData(files = [new File(['front bytes'], 'front.jpg', { type: 'image/jpeg' })], name) {
  const data = new FormData();
  if (name !== undefined) data.set('name', name);
  files.forEach(file => data.append('images', file));
  return data;
}

async function submit(fixture, data) {
  try { await fixture.action(data); } catch (error) {
    if (!error.location) throw error;
    return new URL(error.location, 'https://productframe.example.invalid');
  }
  assert.fail('The existing Server Action must redirect after submission.');
}

test('Continue preserves product creation, signed uploads, image bytes and the analysis-job redirect', async () => {
  const fixture = actionFixture();
  const files = [new File(['front bytes'], 'front.jpg', { type: 'image/jpeg' }), new File(['back bytes'], 'back.png', { type: 'image/png' })];
  const destination = await submit(fixture, uploadData(files, '  September edit  '));
  assert.equal(fixture.calls.length, 6);
  const [product, firstUpload, firstPut, secondUpload, secondPut, job] = fixture.calls;
  assert.equal(product.method, 'POST');
  assert.deepEqual(JSON.parse(product.body), { name: 'September edit' });
  assert.equal(product.headers.Authorization, 'Bearer fixture-token');
  assert.deepEqual(JSON.parse(firstUpload.body), { filename: 'front.jpg', content_type: 'image/jpeg' });
  assert.deepEqual(JSON.parse(secondUpload.body), { filename: 'back.png', content_type: 'image/png' });
  for (const [put, file] of [[firstPut, files[0]], [secondPut, files[1]]]) {
    assert.equal(put.method, 'PUT');
    assert.equal(put.headers['Content-Type'], file.type);
    assert.equal(put.headers.Authorization, undefined, 'Do not forward auth to signed storage URLs.');
    assert.equal(Buffer.from(put.body).toString(), await file.text());
  }
  assert.equal(job.url, 'https://api.example.invalid/analysis-jobs');
  assert.equal(job.method, 'POST');
  assert.deepEqual(JSON.parse(job.body), { source_asset_ids: ['asset-1', 'asset-2'] });
  assert.equal(destination.pathname, '/studio');
  assert.equal(destination.searchParams.get('job_id'), 'analysis-fixture');
  assert.equal(destination.searchParams.get('image_count'), '2');
  assert.match(destination.searchParams.get('message'), /2 images uploaded/);
});

test('optional internal names retain the original default', async () => {
  const fixture = actionFixture();
  await submit(fixture, uploadData(undefined, '   '));
  assert.equal(JSON.parse(fixture.calls[0].body).name, 'Unconfirmed product upload');
});

test('an expired session never creates products or uploads', async () => {
  const fixture = actionFixture({ token: null });
  const destination = await submit(fixture, uploadData());
  assert.equal(fixture.calls.length, 0);
  assert.match(destination.searchParams.get('message'), /sign-in session has expired/);
});

test('invalid file sets are rejected server-side before any product is created', async () => {
  const batches = [[], [new File(['not an image'], 'notes.pdf', { type: 'application/pdf' })], [new File([], 'empty.png', { type: 'image/png' })], Array.from({ length: 51 }, () => new File(['x'], 'photo.jpg', { type: 'image/jpeg' }))];
  for (const files of batches) {
    const fixture = actionFixture();
    const destination = await submit(fixture, uploadData(files));
    assert.equal(fixture.calls.length, 0);
    assert.ok(destination.searchParams.get('message'));
    assert.equal(destination.searchParams.has('job_id'), false);
  }
});

test('an upload failure never proceeds to image analysis', async () => {
  const fixture = actionFixture({ failAt: 3 });
  const destination = await submit(fixture, uploadData());
  assert.equal(fixture.calls.length, 3);
  assert.equal(fixture.calls.some(call => call.url.endsWith('/analysis-jobs')), false);
  assert.match(destination.searchParams.get('message'), /Could not upload front.jpg/);
});

test('analysis-start failures preserve the existing actionable status', async () => {
  const fixture = actionFixture({ failAt: 4 });
  const destination = await submit(fixture, uploadData());
  assert.match(destination.searchParams.get('message'), /Images saved, but analysis could not be started/);
  assert.equal(destination.searchParams.has('job_id'), false);
});
