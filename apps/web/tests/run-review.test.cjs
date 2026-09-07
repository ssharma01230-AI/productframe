'use strict';

// Run with: node --test apps/web/tests/run-review.test.cjs
// Markup contracts plus isolated handler/state tests; no real auth or network IO.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const test = require('node:test');
const vm = require('node:vm');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const ts = require('typescript');

const componentPath = path.resolve(__dirname, '../app/studio/RunReview.tsx');
const requireFromComponent = createRequire(componentPath);
const source = fs.readFileSync(componentPath, 'utf8');
const compiled = ts.transpileModule(
  source + '\nexport const __test__ = { ProductEditor, Summary };\n',
  { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020, esModuleInterop: true } },
).outputText;
const componentModule = { exports: {} };
const unexpected = () => { throw new Error('Markup tests must not request tokens, navigate, or make API calls.'); };

function MockImage({ fill, unoptimized, priority, onError, style, ...props }) {
  // Match next/image's fill positioning; object-fit remains the stylesheet's concern.
  return React.createElement('img', {
    ...props,
    style: fill ? { position: 'absolute', height: '100%', width: '100%', left: 0, top: 0, ...style } : style,
  });
}

vm.runInNewContext(compiled, {
  module: componentModule,
  exports: componentModule.exports,
  process: { env: { NEXT_PUBLIC_API_URL: 'https://api.example.invalid' } },
  fetch: unexpected,
  require(name) {
    if (name.endsWith('.css')) return {};
    if (name === '@clerk/nextjs') return { useAuth: () => ({ getToken: unexpected }) };
    if (name === 'next/navigation') return { useRouter: () => ({ push: unexpected }) };
    if (name === 'next/image') return { __esModule: true, default: MockImage };
    return requireFromComponent(name);
  },
}, { filename: componentPath });

const RunReview = componentModule.exports.default;
const { ProductEditor, Summary } = componentModule.exports.__test__;
const noop = () => {};

function fixture(statuses = ['suggested', 'suggested', 'suggested']) {
  const products = statuses.map((confirmation_status, index) => ({
    id: 'product-' + (index + 1), final_product_id: null, product_number: index + 1,
    product_name: ['Pleated skirt', 'Navy crew-neck tee', 'Rose shirt'][index],
    category: ['bottoms', 'tops', 'tops'][index], product_type: 'Cotton garment',
    colours: 'Navy blue', materials: 'Cotton', features: ['Crew neck', 'Short sleeves'],
    description: 'A soft cotton garment with a considered silhouette.', confidence: 0.98,
    confirmation_status,
  }));
  const images = [4, 5, 4].flatMap((count, group) => Array.from({ length: count }, (_, index) => ({
    id: 'image-' + group + '-' + index, image_number: [0, 4, 9][group] + index + 1,
    filename: 'product-' + (group + 1) + '-' + (index + 1) + '.jpg',
    image_url: 'https://assets.example.test/group-' + (group + 1) + '-' + (index + 1) + '.jpg',
    passed: true, product_number: group + 1, rejection_reason: null, status: 'processed',
  })));
  for (let number = 14; number <= 15; number += 1) images.push({
    id: 'rejected-' + number, image_number: number, filename: 'rejected-' + number + '.jpg',
    image_url: 'https://assets.example.test/rejected-' + number + '.jpg', passed: false,
    product_number: null, rejection_reason: 'Not a wearable fashion product.', status: 'processed',
  });
  return { id: 'analysis-fixture', status: 'awaiting_confirmation', total_images: 15, processed_images: 15, unique_product_count: 3, images, products };
}

function render(initial) {
  return renderToStaticMarkup(React.createElement(RunReview, { jobId: 'analysis-fixture', imageCount: 15, initial }));
}

function renderEditor(initial = fixture(), overrides = {}) {
  return renderToStaticMarkup(React.createElement(ProductEditor, {
    product: initial.products[1], totalProducts: initial.products.length,
    images: initial.images.filter(image => image.product_number === 2 && image.passed === true), imageIndex: 2,
    setImageIndex: noop, update: noop, onCancel: noop, onApprove: noop, saving: false,
    cancelOpen: false, onKeep: noop, onConfirmCancel: noop, onEdit: noop, ...overrides,
  }));
}

function block(html, tag, className) {
  const opening = new RegExp('<' + tag + '\\b[^>]*class="[^"]*\\b' + className + '\\b[^"]*"[^>]*>').exec(html);
  assert.ok(opening, 'Expected .' + className + ' markup');
  const tags = new RegExp('</?' + tag + '\\b[^>]*>', 'g');
  tags.lastIndex = opening.index;
  let depth = 0;
  for (let match; (match = tags.exec(html));) {
    depth += match[0].startsWith('</') ? -1 : 1;
    if (depth === 0) return html.slice(opening.index, tags.lastIndex);
  }
  assert.fail('Unclosed .' + className + ' markup');
}

function textContent(node) {
  if (node == null || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textContent).join('');
  return textContent(node.props?.children);
}

function interactive(initial, { fetch: fetchResponse = unexpected, getToken = async () => 'test-token' } = {}) {
  // Execute the actual component's handlers with persistent hook state. Effects
  // stay disabled so polling/focus timers cannot perform unrelated work. Children
  // remain React elements; the separate SSR cases cover their rendered markup.
  const slots = [];
  let cursor = 0;
  const hooks = {
    ...React,
    useState(initialValue) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = typeof initialValue === 'function' ? initialValue() : initialValue;
      return [slots[index], value => { slots[index] = typeof value === 'function' ? value(slots[index]) : value; }];
    },
    useRef(value) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = { current:value };
      return slots[index];
    },
    useMemo: factory => factory(),
    useEffect: noop,
  };
  const module = { exports:{} };
  vm.runInNewContext(compiled, {
    module, exports:module.exports,
    process:{env:{NEXT_PUBLIC_API_URL:'https://api.example.invalid'}},
    fetch:fetchResponse,
    require(name) {
      if (name === 'react') return hooks;
      if (name.endsWith('.css')) return {};
      if (name === '@clerk/nextjs') return {useAuth:() => ({getToken})};
      if (name === 'next/navigation') return {useRouter:() => ({push:unexpected})};
      if (name === 'next/image') return {__esModule:true,default:MockImage};
      return requireFromComponent(name);
    },
  }, {filename:componentPath});
  let tree;
  function rerender() {
    cursor = 0;
    tree = module.exports.default({jobId:'analysis-fixture',imageCount:15,initial});
    return tree;
  }
  function nodes(predicate) {
    const found = [];
    function visit(node) {
      if (Array.isArray(node)) { node.forEach(visit); return; }
      if (!node || typeof node !== 'object' || !node.props) return;
      if (predicate(node)) found.push(node);
      visit(node.props.children);
    }
    visit(tree);
    return found;
  }
  function button(label) {
    const found = nodes(node => node.type === 'button' && textContent(node).trim() === label)[0];
    assert.ok(found, 'Missing button: ' + label);
    return found;
  }
  function component(name) {
    const found = nodes(node => typeof node.type === 'function' && node.type.name === name)[0];
    assert.ok(found, 'Missing component: ' + name);
    return found;
  }
  rerender();
  return {rerender,nodes,button,component,text:() => textContent(tree)};
}

function approvedRecords(products) {
  return products.map(product => ({...product,confirmation_status:'approved',status:'approved',final_product_id:'catalogue-' + product.product_number}));
}

test('editable fields match the reference full-width and paired layout', () => {
  const editor = renderEditor();
  const labels = Array.from(editor.matchAll(/<label\b([^>]*)>([\s\S]*?)<\/label>/g));
  assert.equal(labels.length, 6);
  for (const field of ['product_name', 'product_type', 'features', 'description']) {
    const label = labels.find(match => match[1].includes('for="pf-field-' + field + '"'));
    assert.ok(label, 'Missing ' + field);
    assert.match(label[1], /\bpf-full\b/);
  }
  for (const field of ['colours', 'materials']) {
    const label = labels.find(match => match[1].includes('for="pf-field-' + field + '"'));
    assert.ok(label, 'Missing ' + field);
    assert.doesNotMatch(label[1], /\bpf-full\b/);
  }
  assert.match(editor, /<input(?=[^>]*name="product_name")(?=[^>]*required="")[^>]*>/);
  assert.equal((editor.match(/<textarea\b/g) || []).length, 2);
  assert.match(editor, /Suggested details can be changed as you see fit\./);
});

test('category is locked text beneath the gallery thumbnails, outside the form', () => {
  const editor = renderEditor();
  const gallery = block(editor, 'div', 'pf-gallery');
  const category = block(gallery, 'section', 'pf-category');
  assert.ok(gallery.indexOf('pf-category') > gallery.indexOf('pf-thumbnails'));
  assert.match(category, /aria-label="Read-only category"/);
  assert.match(category, /<dt><span>Category<\/span><svg/);
  assert.match(category, /<dd>tops<\/dd>/);
  assert.match(category, /Read-only classification/);
  assert.doesNotMatch(category, /<(input|select|textarea)\b/);
  assert.doesNotMatch(block(editor, 'form', 'pf-product-form'), /Category|name="category"/);
});

test('completed header omits the badge and keeps all four metric icons with real counts', () => {
  const html = render(fixture());
  assert.match(html, /3 products identified/);
  assert.doesNotMatch(html, /4 products identified/);
  assert.match(html, /Confirm we’ve got it right\./);
  assert.doesNotMatch(block(html, 'header', 'pf-heading'), /pf-state-badge|Analysis complete/);
  const metrics = block(html, 'section', 'pf-metrics');
  assert.equal((metrics.match(/<svg\b/g) || []).length, 4);
  for (const [value, label] of [[15, 'images uploaded'], [13, 'passed validation'], [3, 'unique products'], [2, 'rejected images']]) {
    assert.ok(metrics.includes('<strong>' + value + '</strong><span>' + label + '</span>'));
  }
  assert.doesNotMatch(html, /AI suggestion|98% confidence|PRODUCTFRAME \/ CONTENT STUDIO|ANALYSIS RUN|images grouped as one product/);
});

test('Approve product stays in the footer and submits its associated editor form', () => {
  const html = render(fixture());
  const editor = block(html, 'section', 'pf-editor');
  const footer = block(html, 'footer', 'pf-footer');
  assert.match(editor, /<form id="pf-product-form"/);
  assert.doesNotMatch(editor, /Approve product/);
  assert.match(footer, /<button type="submit" form="pf-product-form"[^>]*>[\s\S]*Approve product/);
  assert.doesNotMatch(footer, /Done reviewing/);
  assert.ok(html.indexOf(footer) > html.indexOf(editor) + editor.length - 1);
});

test('gallery has the dynamic product position, overlay image count and accessible image controls', () => {
  const editor = renderEditor();
  assert.match(editor, /Product 02 \/ 03/);
  const hero = block(editor, 'div', 'pf-hero-image');
  assert.match(hero, /class="pf-image-label">Image 3 of 5<\/span>/);
  assert.match(hero, /aria-label="Previous image"/);
  assert.match(hero, /aria-label="Next image"/);
  assert.match(hero, /<img[^>]*style="position:absolute;height:100%;width:100%;left:0;top:0"/);
  const thumbnails = block(editor, 'div', 'pf-thumbnails');
  assert.equal((thumbnails.match(/<button\b/g) || []).length, 5);
  assert.equal((thumbnails.match(/aria-pressed="true"/g) || []).length, 1);
  assert.match(thumbnails, /aria-pressed="true" aria-label="View image 3 of Navy crew-neck tee"/);
  const rail = block(render(fixture()), 'aside', 'pf-rail');
  assert.doesNotMatch(rail, /pf-tab-number|pf-tab-meta|images · To review|PRODUCT 0/);
  assert.equal((rail.match(/class="pf-tab-name"/g) || []).length, 3);
  assert.equal((rail.match(/class="pf-tab-image"/g) || []).length, 3);
});

test('loading, no-product and failed states never show review decisions or a review footer', () => {
  const empty = { ...fixture(), products: [], unique_product_count: 0 };
  for (const initial of [null, { ...empty, status: 'queued' }, empty, { ...empty, status: 'failed' }, { ...fixture(), status: 'failed' }]) {
    const html = render(initial);
    assert.doesNotMatch(html, /<footer\b/);
    assert.doesNotMatch(html, /All products cancelled|0 approved|Done reviewing|Approve product/);
  }
  const loading = render(null);
  assert.equal((loading.match(/class="pf-loading-image"/g) || []).length, 3);
  assert.match(loading, /class="pf-loading-copy"/);
  assert.match(loading, /Processing/);
  assert.doesNotMatch(loading, /Analysis complete/);
});

test('loading keeps the centered title and presents a truthful waiting status until progress arrives', () => {
  const loading = render(null);
  const copy = block(loading, 'div', 'pf-loading-copy');
  const title = block(copy, 'div', 'pf-loading-title');
  const messages = block(copy, 'div', 'pf-loading-messages');
  assert.match(title, /class="pf-spinner"[^>]*aria-hidden="true"/);
  assert.match(title, /<strong>Reviewing your products<\/strong>/);
  assert.match(messages, /aria-hidden="true"/);
  assert.match(messages, /class="pf-loading-message entering"[^>]*>Waiting for a progress update<\//);
  assert.doesNotMatch(messages, /role="status"|aria-live=/);
  const status = loading.match(/<([a-z]+)\b[^>]*role="status"[^>]*>([\s\S]*?)<\/\1>/);
  assert.ok(status, 'A stable screen-reader loading status is present');
  assert.match(status[0], /\bpf-sr-only\b/);
  assert.doesNotMatch(status[0], /aria-hidden="true"/);
  assert.ok(status[2].replace(/<[^>]+>/g, '').trim().length > 0);
  assert.ok(!messages.includes(status[0]), 'The loading status is outside decorative captions');
  assert.equal((loading.match(/class="pf-loading-image"/g) || []).length, 3);
  const progress = block(loading, 'div', 'pf-progress');
  assert.match(progress, /indeterminate/);
  assert.doesNotMatch(progress, /aria-valuenow/);
});

test('image phase progress uses completed images rather than weighted or processed-image percentages', () => {
  for (const stage of ['validation', 'screening', 'analysis']) {
    for (const percent of [36, 100, NaN, undefined]) {
      const html = render({ ...fixture(), status: 'analysing', processed_images: 0, products: [], progress: {stage, message:'Checking submitted images', completed:11, total:15, percent} });
      const progress = block(html, 'div', 'pf-progress');
      assert.match(progress, /aria-label="Analysis progress"/);
      assert.match(progress, /aria-valuemax="100" aria-valuenow="73"/);
      assert.match(progress, /width:73%/);
      assert.match(progress, /Checking submitted images · 11 of 15 images · 73%/);
      assert.match(block(html, 'div', 'pf-live-progress'), /11 of 15 images/);
      assert.doesNotMatch(progress, /indeterminate|overall/);
    }
  }
  const analysing = render({ ...fixture(), status:'analysing', products:[], progress:{stage:'analysis', message:'Working', completed:11, total:15, percent:36} });
  assert.match(block(analysing, 'div', 'pf-loading-title'), /Analysing your images/);
});

test('product-detail synthesis reports products rather than incorrectly calling them images', () => {
  const html = render({ ...fixture(), status:'analysing', products:[], progress:{stage:'synthesis', message:'Preparing product details', completed:2, total:4, percent:88} });
  assert.match(block(html, 'div', 'pf-live-progress'), /2 of 4 products/);
  assert.match(block(html, 'div', 'pf-loading-messages'), /Preparing product details/);
  assert.match(block(html, 'div', 'pf-loading-title'), /Preparing product details/);
  const progress = block(html, 'div', 'pf-progress');
  assert.match(progress, /aria-valuenow="50"/);
  assert.match(progress, /width:50%/);
  assert.match(progress, /Preparing product details · 2 of 4 products · 50%/);
  assert.doesNotMatch(progress, /88%|overall|2 of 4 images/);
});

test('grouping and missing stage counts remain indeterminate instead of implying completion', () => {
  const legacy = render({ ...fixture(), status:'grouping', processed_images:15, products:[] });
  assert.match(block(legacy, 'div', 'pf-progress'), /indeterminate/);
  assert.doesNotMatch(block(legacy, 'div', 'pf-progress'), /aria-valuenow/);
  assert.match(block(legacy, 'div', 'pf-loading-messages'), /Grouping matching images/);
  assert.match(block(legacy, 'div', 'pf-loading-title'), /Grouping your products/);
  for (const overrides of [
    {stage:'grouping'}, {stage:'unrecognised'}, {stage:''}, {completed:undefined}, {total:undefined},
    {completed:NaN}, {completed:Infinity}, {completed:-Infinity}, {completed:'11'},
    {total:NaN}, {total:Infinity}, {total:'15'}, {total:0}, {total:-1},
  ]) {
    const html = render({ ...fixture(), status:'analysing', processed_images:15, products:[], progress:{stage:'analysis', message:'Working on this phase', completed:15, total:15, percent:100, ...overrides} });
    const progress = block(html, 'div', 'pf-progress');
    assert.match(progress, /indeterminate/);
    assert.doesNotMatch(progress, /aria-valuenow|width:|\d+%|\d+ of \d+/);
    assert.doesNotMatch(block(html, 'div', 'pf-live-progress'), /\d+%|\d+ of \d+/);
  }
});

test('finite phase counts clamp within the total before calculating the percentage', () => {
  for (const [completed, expectedCount, expectedPercent] of [[-10, 0, 0], [0, 0, 0], [18, 15, 100], [15, 15, 100]]) {
    const html = render({ ...fixture(), status:'screening', products:[], progress:{stage:'screening', message:'Checking images', completed, total:15, percent:36} });
    const progress = block(html, 'div', 'pf-progress');
    assert.ok(progress.includes('aria-valuenow="' + expectedPercent + '"'));
    assert.ok(progress.includes('width:' + expectedPercent + '%'));
    assert.ok(progress.includes(expectedCount + ' of 15 images'));
    assert.doesNotMatch(progress, /indeterminate/);
  }
});

test('failed or empty finished analyses stop loading animations and remain dismissible', () => {
  for (const status of ['failed','awaiting_confirmation','completed']) {
    const html = render({ ...fixture(), status, products:[] });
    assert.match(html, /pf-loading-stopped/);
    assert.doesNotMatch(html, /class="pf-spinner"|class="pf-loading-image"|role="progressbar"/);
    assert.match(html, /aria-label="Close run review"/);
  }
});

test('run review cannot be closed before analysis reaches a terminal status', () => {
  const closeControl = /aria-label="Close run review"/;
  assert.doesNotMatch(render(null), closeControl);
  for (const status of ['pending', 'queued', 'screening', 'grouping', 'analysing', 'unknown']) {
    // Product/image counts alone must not unlock dismissal while work is still running.
    for (const products of [[], fixture().products]) {
      const header = block(render({ ...fixture(), status, products }), 'header', 'pf-heading');
      assert.doesNotMatch(header, closeControl, status);
      assert.match(header, /Processing/);
    }
  }
});

test('run review can be closed after success or failure, even with no products', () => {
  for (const status of ['awaiting_confirmation', 'completed', 'failed']) {
    for (const products of [[], fixture().products]) {
      const header = block(render({ ...fixture(), status, products }), 'header', 'pf-heading');
      assert.match(header, /<button type="button"[^>]*aria-label="Close run review"/, status);
      assert.doesNotMatch(header, /disabled=""/);
    }
  }
});

test('pending validation is not included in the rejected-image count', () => {
  const initial = fixture();
  initial.images[14].passed = null;
  const metrics = block(render(initial), 'section', 'pf-metrics');
  assert.match(metrics, /<strong>1<\/strong><span>rejected image<\/span>/);
});

test('review progress and completion work for every three-product decision combination', () => {
  const choices = ['suggested', 'approved', 'cancelled'];
  for (const first of choices) for (const second of choices) for (const third of choices) {
    const statuses = [first, second, third];
    const approved = statuses.filter(status => status === 'approved').length;
    const cancelled = statuses.filter(status => status === 'cancelled').length;
    const eligible = 3 - cancelled;
    const complete = !statuses.includes('suggested');
    const footer = block(render(fixture(statuses)), 'footer', 'pf-footer');
    assert.ok(footer.includes(eligible ? approved + ' of ' + eligible + ' products reviewed' : 'All products cancelled'), statuses.join(', '));
    assert.ok(footer.includes(approved + ' approved' + (cancelled ? ' · ' + cancelled + ' cancelled' : '')));
    assert.equal(footer.includes('Done reviewing'), complete);
    assert.equal(footer.includes('Approve all'), !complete);
    if (eligible) {
      assert.match(footer, new RegExp('aria-valuemax="' + eligible + '" aria-valuenow="' + approved + '"'));
    } else {
      assert.doesNotMatch(footer, /role="progressbar"|0 of 0/);
    }
  }
});

test('Approve all is a non-submit footer action whenever any product remains pending', () => {
  for (const statuses of [['suggested','suggested','suggested'], ['approved','pending','cancelled'], ['approved','rejected','suggested']]) {
    const footer = block(render(fixture(statuses)), 'footer', 'pf-footer');
    const button = Array.from(footer.matchAll(/<button\b[^>]*>[\s\S]*?<\/button>/g), match => match[0]).find(markup => markup.includes('Approve all'));
    assert.ok(button);
    assert.match(button, /^<button type="button"/);
    assert.doesNotMatch(button, /form="pf-product-form"/);
  }
  for (const initial of [fixture(['approved','cancelled','rejected']), null, {...fixture(),status:'analysing'}, {...fixture(),status:'failed'}]) {
    assert.doesNotMatch(render(initial), /Approve all/);
  }
});

test('approved products keep locked fields and green ticks while allowing cancellation', () => {
  const initial = fixture(['approved', 'suggested', 'cancelled']);
  const rail = block(render(initial), 'aside', 'pf-rail');
  assert.equal((rail.match(/class="pf-approved-tick"/g) || []).length, 1);
  assert.match(rail, /class="pf-sr-only" id="pf-status-product-1">Approved/);
  assert.match(rail, /class="pf-sr-only" id="pf-status-product-3">Cancelled/);
  const editor = renderEditor(initial, { product: initial.products[0] });
  assert.equal((editor.match(/readOnly=""/g) || []).length, 6);
  const cancel = editor.match(/<button[^>]*aria-label="Cancel product"[^>]*>/)[0];
  assert.doesNotMatch(cancel, /disabled/);
  assert.match(editor, />Edit details<\/button>/);
});

test('cancellation explains library removal after approval and stays disabled for closed decisions or saves', () => {
  const initial = fixture(['approved','cancelled','rejected']);
  const approved = initial.products[0];
  const confirmation = renderEditor(initial, {product:approved,cancelOpen:true});
  assert.match(confirmation, /It will be removed from your Product Library, but its details and images will stay in this run/);
  assert.match(confirmation, /Keep product/);
  for (const overrides of [{product:approved,saving:true}, {product:approved,editing:true}, {product:initial.products[1]}, {product:initial.products[2]}]) {
    const cancel = renderEditor(initial, overrides).match(/<button[^>]*aria-label="Cancel product"[^>]*>/)[0];
    assert.match(cancel, /disabled=""/);
  }
});

test('approved products unlock their six editable fields without unlocking category or cancellation', () => {
  const initial = fixture(['approved','suggested','cancelled']);
  const editor = renderEditor(initial, { product:initial.products[0], editing:true });
  assert.doesNotMatch(editor, /readOnly=""/);
  assert.match(editor, /Editing approved details/);
  assert.match(editor, /Saved changes also update this product in your Product Library/);
  assert.match(editor, /disabled="" aria-label="Cancel product"/);
  assert.doesNotMatch(block(editor, 'section', 'pf-category'), /<(input|textarea|select)\b/);
  assert.equal((renderEditor(initial, { product:initial.products[0], editing:true, saving:true }).match(/readOnly=""/g) || []).length, 6);
  assert.doesNotMatch(renderEditor(initial, { product:initial.products[2] }), />Edit details<\/button>/);
});

test('summary uses approved product photos and current escaped names rather than initials', () => {
  const initial = fixture(['approved', 'cancelled', 'approved']);
  initial.products[0].product_name = 'Studio <Silk> & Cotton';
  const approved = initial.products.filter(product => product.confirmation_status === 'approved');
  const html = renderToStaticMarkup(React.createElement(Summary, { approved, images: initial.images, onBack: noop, onProduce: noop }));
  const grid = block(html, 'ul', 'pf-summary-grid');
  assert.equal((grid.match(/class="pf-summary-card"/g) || []).length, 2);
  assert.equal((grid.match(/<img\b/g) || []).length, 2);
  assert.match(grid, /group-1-1.jpg/);
  assert.match(grid, /group-3-1.jpg/);
  assert.match(grid, /Studio &lt;Silk&gt; &amp; Cotton/);
  assert.doesNotMatch(grid, /Navy crew-neck tee|group-2-/);
  assert.match(html, /Back to review/);
  assert.match(html, /Produce outputs/);
});

test('empty approved summary offers Back to review without Produce outputs', () => {
  const html = renderToStaticMarkup(React.createElement(Summary, { approved: [], images: [], onBack: noop, onProduce: noop }));
  assert.match(html, /No products have been approved for the next step/);
  assert.match(html, /Back to review/);
  assert.doesNotMatch(html, /Produce outputs|pf-summary-grid/);
});

test('missing product photos use an image fallback instead of broken images or initials', () => {
  const initial = fixture(['approved', 'suggested', 'suggested']);
  const html = renderToStaticMarkup(React.createElement(Summary, { approved: [initial.products[0]], images: [], onBack: noop, onProduce: noop }));
  assert.match(html, /class="pf-image-empty"/);
  assert.doesNotMatch(html, /<img\b/);
});

test('bulk approval sends only pending drafts with trimmed editable fields and reconciles canonical saved records', async () => {
  const initial = fixture(['approved','pending','cancelled']);
  const draft = initial.products[1];
  Object.assign(draft, {product_name:'  Updated shirt  ',product_type:'  Cotton shirt  ',colours:'  Navy blue  ',materials:' Cotton ',features:[' Collared ','  ',' Button front '],description:'  Current edited description.  '});
  const saved = {...draft,product_name:'Canonical saved shirt',features:['Collared','Button front'],confirmation_status:'approved',status:'approved',final_product_id:'saved-catalogue-product'};
  const requests = [];
  const ui = interactive(initial, {fetch:async (url, options) => {
    requests.push({url,options});
    return {ok:true,json:async () => ({products:[saved]})};
  }});

  await ui.button('Approve all').props.onClick();
  ui.rerender();

  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, 'https://api.example.invalid/analysis-jobs/analysis-fixture/products/approve-all');
  assert.equal(requests[0].options.method, 'POST');
  assert.equal(requests[0].options.headers.Authorization, 'Bearer test-token');
  assert.equal(requests[0].options.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(requests[0].options.body), {products:[{
    product_number:2,product_name:'Updated shirt',product_type:'Cotton shirt',colours:'Navy blue',materials:'Cotton',features:['Collared','Button front'],description:'Current edited description.',
  }]});
  assert.equal(ui.nodes(node => typeof node.type === 'function' && node.type.name === 'Summary').length, 0);
  assert.doesNotMatch(ui.text(), /Approve all/);
  ui.button('Done reviewing').props.onClick();
  ui.rerender();
  const summary = ui.component('Summary');
  assert.equal(summary.props.approved.length, 2);
  assert.equal(summary.props.approved[1].product_name, 'Canonical saved shirt');
  assert.equal(summary.props.approved[1].final_product_id, 'saved-catalogue-product');
});

test('bulk approval validates every pending draft, selects invalid unselected products, and sends nothing', async () => {
  const invalidFields = [
    ['product_name','   '], ['product_name','x'.repeat(161)], ['product_type',''], ['product_type','x'.repeat(161)],
    ['colours',' '], ['colours','x'.repeat(301)], ['materials',''], ['materials','x'.repeat(301)],
    ['description',' '], ['description','x'.repeat(321)], ['features',['  ']], ['features',Array(31).fill('Feature')],
  ];
  for (const [field,value] of invalidFields) {
    const initial = fixture();
    initial.products[2][field] = value;
    let tokenCalls = 0;
    let requestCalls = 0;
    const ui = interactive(initial, {getToken:async () => {tokenCalls++; return 'test-token';},fetch:async () => {requestCalls++; throw new Error('Unexpected submission');}});
    await ui.button('Approve all').props.onClick();
    ui.rerender();
    assert.equal(tokenCalls, 0, field);
    assert.equal(requestCalls, 0, field);
    assert.equal(ui.component('ProductEditor').props.product.product_number, 3, field);
    const error = ui.nodes(node => node.props.role === 'alert')[0];
    assert.ok(error, field);
    assert.match(textContent(error), /Product 3:/, field);
  }
});

test('bulk approval blocks duplicate submissions and edits until the pending request settles', async () => {
  const initial = fixture();
  let releaseToken;
  const token = new Promise(resolve => {releaseToken = resolve;});
  let tokenCalls = 0;
  const requests = [];
  const ui = interactive(initial, {getToken:() => {tokenCalls++; return token;},fetch:async (url, options) => {
    requests.push({url,options});
    return {ok:true,json:async () => ({products:approvedRecords(initial.products)})};
  }});
  const click = ui.button('Approve all').props.onClick;
  const first = click();
  await click();
  ui.rerender();
  assert.equal(tokenCalls, 1);
  assert.equal(requests.length, 0);
  const editor = ui.component('ProductEditor');
  assert.equal(editor.props.saving, true);
  editor.props.update(1, 'product_name', 'Unsubmitted concurrent edit');
  ui.rerender();
  assert.equal(ui.component('ProductEditor').props.product.product_name, initial.products[0].product_name);
  const tabs = ui.nodes(node => node.type === 'button' && node.props.className === 'pf-product-tab');
  assert.ok(tabs.length > 0);
  assert.ok(tabs.every(tab => tab.props.disabled));
  assert.ok(ui.nodes(node => node.type === 'button' && node.props['aria-label'] === 'Close run review')[0].props.disabled);

  releaseToken('test-token');
  await first;
  ui.rerender();
  assert.equal(requests.length, 1);
  assert.equal(ui.component('ProductEditor').props.saving, false);
  assert.ok(ui.button('Done reviewing'));
});

test('a failed bulk request retains edits and pending decisions so retry can safely approve them', async () => {
  const initial = fixture();
  const bodies = [];
  const ui = interactive(initial, {fetch:async (url, options) => {
    const body = JSON.parse(options.body);
    bodies.push(body);
    if (bodies.length === 1) return {ok:false};
    return {ok:true,json:async () => ({products:approvedRecords(initial.products.map(product => ({...product,...body.products.find(saved => saved.product_number === product.product_number)})))})};
  }});
  ui.component('ProductEditor').props.update(1, 'product_name', 'My edited product');
  ui.rerender();
  await ui.button('Approve all').props.onClick();
  ui.rerender();
  assert.equal(ui.component('ProductEditor').props.product.product_name, 'My edited product');
  assert.equal(ui.component('ProductEditor').props.product.confirmation_status, 'suggested');
  assert.equal(ui.component('ProductEditor').props.saving, false);
  assert.match(ui.text(), /Your edits are still here/);
  assert.doesNotMatch(ui.text(), /Done reviewing/);

  await ui.button('Approve all').props.onClick();
  ui.rerender();
  assert.equal(bodies.length, 2);
  assert.deepEqual(bodies[1], bodies[0]);
  assert.equal(bodies[1].products[0].product_name, 'My edited product');
  assert.equal(ui.component('ProductEditor').props.product.product_name, 'My edited product');
  assert.equal(ui.component('ProductEditor').props.product.confirmation_status, 'approved');
  assert.ok(ui.button('Done reviewing'));
});

test('an incomplete bulk response cannot mark only part of the pending drafts approved', async () => {
  const initial = fixture();
  const ui = interactive(initial, {fetch:async () => ({ok:true,json:async () => ({products:approvedRecords(initial.products.slice(0, 1))})})});
  await ui.button('Approve all').props.onClick();
  ui.rerender();
  assert.equal(ui.component('ProductEditor').props.product.confirmation_status, 'suggested');
  assert.equal(ui.nodes(node => node.props.className === 'pf-approved-tick').length, 0);
  assert.match(ui.text(), /Your edits are still here/);
  assert.ok(ui.button('Approve all'));
  assert.doesNotMatch(ui.text(), /Done reviewing/);
});

test('bulk response reconciliation respects a server-side cancellation rather than approving every draft locally', async () => {
  const initial = fixture();
  const records = approvedRecords(initial.products);
  records[1] = {...records[1],confirmation_status:'cancelled',status:'cancelled',final_product_id:null};
  const ui = interactive(initial, {fetch:async () => ({ok:true,json:async () => ({products:records})})});
  await ui.button('Approve all').props.onClick();
  ui.rerender();
  assert.match(ui.text(), /2 approved · 1 cancelled/);
  assert.doesNotMatch(ui.text(), /Approve all/);
  ui.button('Done reviewing').props.onClick();
  ui.rerender();
  assert.equal(ui.component('Summary').props.approved.map(product => product.product_number).join(','), '1,3');
});

test('bulk approval is unavailable during approved-product editing and pending cancellation confirmation', async () => {
  for (const mode of ['editing','cancelling']) {
    const initial = fixture(mode === 'editing' ? ['approved','pending','suggested'] : undefined);
    let requests = 0;
    const ui = interactive(initial, {fetch:async () => {requests++; throw new Error('Unexpected approval');}});
    const editor = ui.component('ProductEditor');
    if (mode === 'editing') editor.props.onEdit();
    else editor.props.onCancel();
    ui.rerender();
    if (mode === 'editing') assert.doesNotMatch(ui.text(), /Approve all/);
    else {
      assert.equal(ui.button('Approve all').props.disabled, true, mode);
      await ui.button('Approve all').props.onClick();
    }
    assert.equal(requests, 0, mode);
  }
});

test('cancelling an approved product requires confirmation, saves once, and updates counts and summary', async () => {
  const initial = fixture(['approved','approved','cancelled']);
  initial.products[0].final_product_id = 'saved-product-1';
  let releaseToken;
  const token = new Promise(resolve => {releaseToken = resolve;});
  const requests = [];
  const ui = interactive(initial, {getToken:() => token, fetch:async (url,options) => {
    requests.push({url,options});
    return {ok:true};
  }});
  ui.component('ProductEditor').props.onCancel();
  ui.rerender();
  assert.equal(ui.component('ProductEditor').props.cancelOpen, true);
  assert.equal(requests.length, 0);
  ui.component('ProductEditor').props.onKeep();
  ui.rerender();
  assert.equal(ui.component('ProductEditor').props.cancelOpen, false);
  assert.equal(ui.component('ProductEditor').props.product.confirmation_status, 'approved');

  ui.component('ProductEditor').props.onCancel();
  ui.rerender();
  const confirm = ui.component('ProductEditor').props.onConfirmCancel;
  const saving = confirm();
  await confirm();
  ui.rerender();
  assert.equal(ui.component('ProductEditor').props.saving, true);
  assert.equal(ui.component('ProductEditor').props.product.confirmation_status, 'approved');
  releaseToken('test-token');
  await saving;
  ui.rerender();

  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, 'https://api.example.invalid/analysis-jobs/analysis-fixture/products/1');
  assert.equal(requests[0].options.method, 'PATCH');
  assert.equal(JSON.parse(requests[0].options.body).status, 'cancelled');
  assert.equal(ui.component('ProductEditor').props.product.confirmation_status, 'cancelled');
  assert.equal(ui.component('ProductEditor').props.product.final_product_id, 'saved-product-1');
  assert.match(ui.text(), /1 of 1 products reviewed/);
  assert.match(ui.text(), /1 approved · 2 cancelled/);
  assert.equal(ui.nodes(node => node.props.className === 'pf-approved-tick').length, 1);
  ui.button('Done reviewing').props.onClick();
  ui.rerender();
  assert.equal(ui.component('Summary').props.approved.map(product => product.product_number).join(','), '2');
});

test('failed cancellation keeps the approved product and can be retried', async () => {
  const initial = fixture(['approved','suggested','cancelled']);
  let requests = 0;
  const ui = interactive(initial, {fetch:async () => ({ok:++requests > 1})});
  ui.component('ProductEditor').props.onCancel();
  ui.rerender();
  await ui.component('ProductEditor').props.onConfirmCancel();
  ui.rerender();
  assert.equal(ui.component('ProductEditor').props.saving, false);
  assert.equal(ui.component('ProductEditor').props.product.confirmation_status, 'approved');
  assert.match(ui.text(), /We could not save that decision/);
  assert.match(ui.text(), /1 approved · 1 cancelled/);

  ui.component('ProductEditor').props.onCancel();
  ui.rerender();
  await ui.component('ProductEditor').props.onConfirmCancel();
  ui.rerender();
  assert.equal(requests, 2);
  assert.equal(ui.component('ProductEditor').props.product.confirmation_status, 'cancelled');
  assert.match(ui.text(), /0 approved · 2 cancelled/);
  assert.doesNotMatch(ui.text(), /We could not save that decision/);
});
