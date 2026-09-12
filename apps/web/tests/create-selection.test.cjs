'use strict';

// Run with: node --test apps/web/tests/create-selection.test.cjs
// Exercise the real UI handlers with isolated state and navigation; no auth or IO.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const test = require('node:test');
const vm = require('node:vm');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const ts = require('typescript');

const studioDirectory = path.resolve(__dirname, '../app/studio');
const noop = () => {};
const unexpected = () => { throw new Error('Selection tests must not make network requests.'); };

function loadComponent(name, { react = React, push = unexpected, history = { state: null, replaceState: unexpected } } = {}) {
  const modules = new Map();
  function load(filename) {
    if (modules.has(filename)) return modules.get(filename).exports;
    const module = { exports: {} };
    modules.set(filename, module);
    const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    }).outputText;
    const requireFromComponent = createRequire(filename);
    vm.runInNewContext(compiled, {
      module, exports: module.exports, URLSearchParams, console,
      process: { env: { NEXT_PUBLIC_ENABLE_GENERATION_SLICE: 'false' } }, fetch: unexpected, window: { history },
      require(dependency) {
        if (dependency === 'react') return react;
        if (dependency === '@clerk/nextjs') return { useAuth: () => ({ getToken: async () => null }) };
        if (dependency.endsWith('.css')) return {};
        if (dependency === 'next/navigation') return { useRouter: () => ({ push }) };
        if (dependency === 'next/image') return { __esModule: true, default: ({ fill, unoptimized, priority, ...props }) => React.createElement('img', props) };
        if (dependency === 'next/link') return { __esModule: true, default: ({ prefetch, ...props }) => React.createElement('a', props) };
        if (dependency.startsWith('.')) {
          const relative = path.resolve(path.dirname(filename), dependency);
          const target = [relative + '.tsx', relative + '.ts'].find(candidate => fs.existsSync(candidate));
          if (target) return load(target);
        }
        return requireFromComponent(dependency);
      },
    }, { filename });
    return module.exports;
  }
  return load(path.join(studioDirectory, name + '.tsx')).default;
}

function textContent(node) {
  if (node == null || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textContent).join('');
  return textContent(node.props?.children);
}

function accessibleText(node) {
  if (node == null || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(accessibleText).join('');
  if (node.props?.['aria-hidden']) return '';
  return accessibleText(node.props?.children);
}

function interactive(name, initialProps) {
  const slots = [];
  let cursor = 0;
  const hooks = {
    ...React,
    useState(initialValue) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = typeof initialValue === 'function' ? initialValue() : initialValue;
      return [slots[index], next => { slots[index] = typeof next === 'function' ? next(slots[index]) : next; }];
    },
    useRef(initialValue) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = { current: initialValue };
      return slots[index];
    },
    useId() {
      const index = cursor++;
      if (!(index in slots)) slots[index] = 'test-id-' + index;
      return slots[index];
    },
    useMemo: factory => factory(), useCallback: callback => callback, useEffect: noop,
  };
  const navigations = [];
  const replacedUrls = [];
  // Null lets Next's history wrapper preserve its internal state and synchronize
  // useSearchParams; passing Next's __NA state would bypass that wrapper.
  const history = { state: { __NA: true }, replaceState: (state, unused, url) => { assert.equal(state, null); replacedUrls.push(url); } };
  const Component = loadComponent(name, { react: hooks, push: url => navigations.push(url), history });
  let props = initialProps;
  let tree;
  function rerender(nextProps = props) {
    props = nextProps;
    cursor = 0;
    tree = Component(props);
    return tree;
  }
  function nodes(predicate, root = tree) {
    const found = [];
    function visit(node) {
      if (Array.isArray(node)) { node.forEach(visit); return; }
      if (!node || typeof node !== 'object' || !node.props) return;
      if (predicate(node)) found.push(node);
      visit(node.props.children);
    }
    visit(root);
    return found;
  }
  function button(label) {
    const result = nodes(node => node.type === 'button' && (node.props['aria-label'] ?? accessibleText(node).trim()) === label)[0];
    assert.ok(result, 'Missing button: ' + label);
    return result;
  }
  function productButton(product) {
    const result = nodes(node => node.type === 'button' && typeof node.props['aria-pressed'] === 'boolean' && node.props['aria-label']?.includes(product.name))[0];
    assert.ok(result, 'Missing accessible catalogue button: ' + product.name);
    return result;
  }
  function component(name) {
    const result = nodes(node => typeof node.type === 'function' && node.type.name === name)[0];
    assert.ok(result, 'Missing component: ' + name);
    return result;
  }
  rerender();
  return { rerender, nodes, button, productButton, component, navigations, replacedUrls, text: () => textContent(tree) };
}

function fixture() {
  return [
    { id: 'catalogue-shirt/blue?size=M&season=AW', name: 'Blue cotton shirt', category: 'tops', image_url: 'https://assets.example.test/blue-shirt.jpg' },
    { id: 'catalogue-bag+tan ü', name: 'Tan leather bag', category: 'bags', image_url: 'https://assets.example.test/tan-bag.jpg' },
    { id: 'catalogue-boots-03', name: 'Suede ankle boots', category: null, image_url: null },
  ];
}

function selectionUrl(ui, expectedIds, outputs) {
  assert.ok(ui.navigations.length, 'Expected a durable navigation URL');
  const url = new URL(ui.navigations.at(-1), 'https://app.example.test');
  assert.equal(url.pathname, '/studio');
  assert.equal(url.searchParams.get('view'), 'create');
  assert.equal(url.searchParams.get('step'), outputs ? 'outputs' : null);
  assert.deepEqual(url.searchParams.getAll('product').sort(), [...expectedIds].sort());
  assert.equal(url.hash, '');
  return url;
}

test('catalogue products render as accessible unselected buttons with no next action', () => {
  const products = fixture();
  const ui = interactive('CreateView', { products, onUpload: noop });
  for (const product of products) {
    const button = ui.productButton(product);
    assert.equal(button.props.type, 'button');
    assert.equal(button.props['aria-pressed'], false);
    assert.equal(typeof button.props.onClick, 'function');
  }
  assert.doesNotMatch(ui.text(), /Choose outputs/);
  const Component = loadComponent('CreateView');
  const html = renderToStaticMarkup(React.createElement(Component, { products, onUpload: noop }));
  assert.equal((html.match(/aria-pressed="false"/g) || []).length, products.length);
  assert.match(html, /Blue cotton shirt/);
  assert.match(html, /Suede ankle boots/);
});

test('selecting and deselecting products supports one or several independent selections', () => {
  const products = fixture();
  const ui = interactive('CreateView', { products, onUpload: noop });
  ui.productButton(products[0]).props.onClick();
  ui.rerender();
  assert.equal(ui.productButton(products[0]).props['aria-pressed'], true);
  assert.equal(ui.productButton(products[1]).props['aria-pressed'], false);
  assert.equal(Boolean(ui.button('Choose outputs').props.disabled), false);
  ui.productButton(products[1]).props.onClick();
  ui.rerender();
  assert.equal(ui.productButton(products[0]).props['aria-pressed'], true);
  assert.equal(ui.productButton(products[1]).props['aria-pressed'], true);
  ui.productButton(products[0]).props.onClick();
  ui.rerender();
  assert.equal(ui.productButton(products[0]).props['aria-pressed'], false);
  assert.equal(ui.productButton(products[1]).props['aria-pressed'], true);
  ui.productButton(products[1]).props.onClick();
  ui.rerender();
  assert.doesNotMatch(ui.text(), /Choose outputs/);
});

test('Choose outputs preserves selected product IDs safely in repeated URL parameters', () => {
  const products = fixture();
  const ui = interactive('CreateView', { products, onUpload: noop });
  for (const product of products.slice(0, 2)) {
    ui.productButton(product).props.onClick();
    ui.rerender();
  }
  ui.button('Choose outputs').props.onClick();
  selectionUrl(ui, products.slice(0, 2).map(product => product.id), true);
  assert.equal(ui.replacedUrls.length, 1);
  selectionUrl({ navigations: ui.replacedUrls }, products.slice(0, 2).map(product => product.id), false);
  const url = new URL(ui.navigations.at(-1), 'https://app.example.test');
  assert.equal(url.searchParams.has('season'), false, 'Product IDs cannot inject query parameters');
  assert.equal(url.searchParams.has('size'), false);
});

test('initial selections discard unavailable IDs and collapse duplicates', () => {
  const products = fixture();
  const ui = interactive('CreateView', { products, onUpload: noop, initialSelectedIds: ['removed-product', products[1].id, products[1].id] });
  assert.equal(ui.productButton(products[0]).props['aria-pressed'], false);
  assert.equal(ui.productButton(products[1]).props['aria-pressed'], true);
  assert.equal(ui.productButton(products[2]).props['aria-pressed'], false);
  ui.button('Choose outputs').props.onClick();
  selectionUrl(ui, [products[1].id], true);
});

test('clearing the selection removes the next action without changing catalogue products', () => {
  const products = fixture();
  const ui = interactive('CreateView', { products, onUpload: noop, initialSelectedIds: products.map(product => product.id) });
  ui.button('Clear selection').props.onClick();
  ui.rerender();
  assert.doesNotMatch(ui.text(), /Choose outputs/);
  for (const product of products) assert.equal(ui.productButton(product).props['aria-pressed'], false);
});

test('upload remains available with an empty catalogue and without choosing any product', () => {
  for (const products of [[], fixture()]) {
    let uploads = 0;
    const ui = interactive('CreateView', { products, onUpload: () => { uploads++; } });
    const upload = ui.nodes(node => node.type === 'button' && textContent(node).includes('Upload product images'))[0];
    assert.ok(upload);
    upload.props.onClick();
    assert.equal(uploads, 1);
    assert.doesNotMatch(ui.text(), /Choose outputs/);
    assert.equal(ui.navigations.length, 0);
  }
});

test('output selection receives only current selected products and Back preserves their IDs', () => {
  const products = fixture();
  const selectedIds = [products[0].id, products[2].id];
  const ui = interactive('CreateView', { products, onUpload: noop, initialSelectedIds: [...selectedIds, 'removed-product'], initialOutputStep: true });
  const output = ui.component('OutputSelection');
  assert.deepEqual(Array.from(output.props.products, product => product.id).sort(), selectedIds.sort());
  assert.equal(output.props.products.find(product => product.id === products[0].id).image_url, products[0].image_url);
  output.props.onBack();
  selectionUrl(ui, selectedIds, false);
});

test('a stale output-step URL never passes unavailable products to output selection', () => {
  const products = fixture();
  const ui = interactive('CreateView', { products, onUpload: noop, initialSelectedIds: ['removed-product'], initialOutputStep: true });
  const output = ui.component('OutputSelection');
  assert.equal(output.props.products.length, 0);
  output.props.onBack();
  selectionUrl(ui, [], false);
});

function outputUi(products, initialSelection = {}) {
  let selection = initialSelection;
  const props = () => ({ products, selection, onBack: noop, onSelectionChange: next => { selection = next; } });
  const ui = interactive('OutputSelection', props());
  const rerender = () => ui.rerender(props());
  function selectProduct(product) {
    const button = ui.nodes(node => node.type === 'button' && typeof node.props['aria-pressed'] === 'boolean' && textContent(node).includes(product.name))[0];
    assert.ok(button, 'Missing product chooser: ' + product.name);
    button.props.onClick();
    rerender();
  }
  function chooseRecipe(name) {
    ui.button(name).props.onClick();
    rerender();
  }
  return { ui, rerender, selectProduct, chooseRecipe, selection: () => JSON.parse(JSON.stringify(selection)) };
}

function summaryDialog(ui) {
  const dialog = ui.nodes(node => node.type === 'dialog' && node.props.id === 'output-selection-summary')[0];
  assert.ok(dialog, 'Missing output review dialog');
  return dialog;
}

test('output choices remain isolated per product when selecting, switching and deselecting', () => {
  const products = fixture().slice(0, 2);
  const initialSelection = {};
  const { ui, selectProduct, chooseRecipe, selection } = outputUi(products, initialSelection);
  chooseRecipe('Folded View');
  chooseRecipe('Front View');
  assert.equal(ui.button('Folded View').props['aria-pressed'], true);
  assert.equal(ui.button('Front View').props['aria-pressed'], true);

  selectProduct(products[1]);
  assert.equal(ui.button('Clean Product Shot').props['aria-pressed'], false);
  assert.equal(ui.button('Front View').props['aria-pressed'], false);
  chooseRecipe('Clean Product Shot');
  assert.deepEqual(selection(), {
    [products[0].id]: ['ecommerce-tops-folded-view', 'ecommerce-tops-front-view'],
    [products[1].id]: ['ecommerce-clean-product-shot'],
  });

  selectProduct(products[0]);
  chooseRecipe('Folded View');
  assert.equal(ui.button('Folded View').props['aria-pressed'], false);
  assert.equal(ui.button('Front View').props['aria-pressed'], true);
  assert.deepEqual(selection(), {
    [products[0].id]: ['ecommerce-tops-front-view'],
    [products[1].id]: ['ecommerce-clean-product-shot'],
  });
  assert.deepEqual(initialSelection, {}, 'Controlled input is never mutated');
});

test('review requires a known output for every current product and groups the correct choices', () => {
  const products = fixture().slice(0, 2);
  const { ui, rerender, selectProduct, chooseRecipe } = outputUi(products, {
    [products[0].id]: ['removed-recipe'],
    [products[1].id]: ['lifestyle-studio-model-shot', 'lifestyle-studio-model-shot'],
    'removed-product': ['ecommerce-clean-product-shot'],
  });
  assert.equal(ui.button('Review selection').props.disabled, true);

  chooseRecipe('Folded View');
  assert.equal(ui.button('Review selection').props.disabled, false);
  ui.button('Review selection').props.onClick();
  rerender();
  const dialog = ui.nodes(node => node.type === 'dialog' && node.props.id === 'output-selection-summary')[0];
  assert.ok(dialog, 'Review opens a native dialog');
  assert.equal(ui.button('Review selection').props['aria-haspopup'], 'dialog');
  assert.equal(ui.button('Review selection').props['aria-expanded'], true);
  assert.equal(dialog.props['aria-labelledby'], 'output-summary-title');
  assert.equal(dialog.props['aria-describedby'], 'output-summary-description');
  const shirt = ui.nodes(node => node.type === 'section' && node.props['aria-label'] === products[0].name)[0];
  const bag = ui.nodes(node => node.type === 'section' && node.props['aria-label'] === products[1].name)[0];
  assert.match(textContent(shirt), /Folded View/);
  assert.doesNotMatch(textContent(shirt), /Studio Model Shot/);
  assert.match(textContent(bag), /Studio Model Shot/);
  assert.doesNotMatch(textContent(bag), /Folded View/);

  ui.button('Back to selection').props.onClick();
  rerender();
  assert.equal(ui.button('Review selection').props['aria-expanded'], false);
  selectProduct(products[1]);
  chooseRecipe('Studio Model Shot');
  assert.equal(ui.button('Review selection').props.disabled, true);
});

test('review dismissal through Back, Close or Escape preserves every product output choice', () => {
  const products = fixture().slice(0, 2);
  const initialSelection = {
    [products[0].id]: ['ecommerce-tops-folded-view', 'ecommerce-tops-front-view'],
    [products[1].id]: ['lifestyle-studio-model-shot'],
  };
  for (const dismissal of ['Back to selection', 'Close selection review', 'Escape']) {
    const { ui, rerender, selection } = outputUi(products, initialSelection);
    ui.button('Review selection').props.onClick();
    rerender();
    assert.equal(ui.button('Review selection').props['aria-expanded'], true);
    if (dismissal === 'Escape') {
      let prevented = false;
      const dialog = summaryDialog(ui);
      dialog.props.onCancel({ preventDefault: () => { prevented = true; } });
      assert.equal(prevented, true, 'React state controls native Escape dismissal');
    } else ui.button(dismissal).props.onClick();
    rerender();
    assert.equal(ui.button('Review selection').props['aria-expanded'], false, dismissal);
    assert.deepEqual(selection(), initialSelection, dismissal);
    ui.button('Review selection').props.onClick();
    rerender();
    assert.equal(ui.button('Review selection').props['aria-expanded'], true, 'Review can reopen after ' + dismissal);
    assert.deepEqual(selection(), initialSelection);
  }
});

test('review backdrop dismisses only direct clicks outside the dialog bounds', () => {
  const products = fixture().slice(0, 1);
  const initialSelection = { [products[0].id]: ['ecommerce-tops-folded-view'] };
  const { ui, rerender, selection } = outputUi(products, initialSelection);
  ui.button('Review selection').props.onClick();
  rerender();
  const element = { getBoundingClientRect: () => ({ left: 100, right: 500, top: 100, bottom: 500 }) };
  for (const event of [
    { target: {}, currentTarget: element, clientX: 20, clientY: 20 },
    { target: element, currentTarget: element, clientX: 300, clientY: 300 },
  ]) {
    summaryDialog(ui).props.onClick(event);
    rerender();
    assert.equal(ui.button('Review selection').props['aria-expanded'], true, 'Content or in-bounds clicks leave review open');
  }
  summaryDialog(ui).props.onClick({ target: element, currentTarget: element, clientX: 50, clientY: 300 });
  rerender();
  assert.equal(ui.button('Review selection').props['aria-expanded'], false);
  assert.deepEqual(selection(), initialSelection);
});

test('review tiles show the selected recipe thumbnails and an unavailable Continue action', () => {
  const products = fixture().slice(0, 2);
  const { ui, rerender } = outputUi(products, {
    [products[0].id]: ['ecommerce-tops-folded-view', 'ecommerce-tops-front-view', 'ecommerce-tops-front-view'],
    [products[1].id]: ['lifestyle-studio-model-shot'],
  });
  ui.button('Review selection').props.onClick();
  rerender();
  const dialog = summaryDialog(ui);
  const expected = [
    [products[0], ['Folded View', 'Front View']],
    [products[1], ['Studio Model Shot']],
  ];
  for (const [product, names] of expected) {
    const group = ui.nodes(node => node.type === 'section' && node.props['aria-label'] === product.name, dialog)[0];
    const tiles = ui.nodes(node => node.type === 'li', group);
    assert.equal(tiles.length, names.length, 'Only the unique selected recipes appear for ' + product.name);
    for (const name of names) {
      const tile = tiles.find(node => textContent(node).includes(name));
      assert.ok(tile, 'Missing selected recipe: ' + name);
      const thumbnail = ui.nodes(node => typeof node.props.src === 'string', tile);
      const recipeImages = ui.nodes(node => typeof node.props.src === 'string', ui.button(name));
      assert.equal(thumbnail.length, 1, 'A thumbnail accompanies ' + name);
      assert.equal(thumbnail[0].props.src, recipeImages[0].props.src, 'The thumbnail matches the selected output example');
    }
  }
  assert.equal(ui.button('Generation unavailable').props.disabled, true);
  assert.equal(textContent(ui.nodes(node => node.props.id === 'output-selection-total', dialog)[0]), '3 outputs selected');
  assert.doesNotMatch(textContent(dialog), /Edit selection/);
});

test('empty output selection offers Back without output choices or an enabled review action', () => {
  let backCalls = 0;
  const ui = interactive('OutputSelection', { products: [], selection: { stale: ['ecommerce-clean-product-shot'] }, onBack: () => { backCalls++; }, onSelectionChange: unexpected });
  ui.button('Back to products').props.onClick();
  assert.equal(backCalls, 1);
  assert.doesNotMatch(ui.text(), /Review selection|Folded View/);
  assert.equal(ui.nodes(node => node.type === 'button' && 'aria-pressed' in node.props).length, 0);
  const Component = loadComponent('OutputSelection');
  const html = renderToStaticMarkup(React.createElement(Component, { products: fixture().slice(0, 1), selection: {}, onBack: noop, onSelectionChange: unexpected }));
  assert.match(html, /Images are output examples\./);
  assert.match(html, /Ecommerce/);
  assert.match(html, /Lifestyle/);
  assert.match(html, /Campaign/);
  assert.match(html, /aria-label="Folded View" aria-pressed="false"/);
});

const outerwearExamples = [
  ['Front Close', '01-front-close.png'],
  ['Front Medium', '02-front-medium.png'],
  ['Over-the-Shoulder (No Face)', '03-over-the-shoulder-no-face.png'],
  ['Full Body with Model (No Face)', '04-full-body-model-no-face.png'],
  ['Close-Up', '05-construction-close-up.png'],
  ['Back', '06-back-product.png'],
  ['Front with Model (No Face)', '07-front-model-no-face.png'],
  ['Back with Model (No Face)', '08-back-model-no-face.png'],
  ['Side / Angled with Model (No Face)', '09-side-angle-model-no-face.png'],
  ['Fabric Shot', '10-fabric-leather-texture.png'],
];

function mixedProducts() {
  const [first, second] = fixture();
  return [
    { ...first, name: 'Wool trench coat', category: 'outerwear' },
    { ...second, name: 'Cotton blouse', category: 'tops' },
  ];
}

function outputCards(ui, root) {
  return ui.nodes(node => node.type === 'button' && node.props['aria-describedby']?.startsWith('output-description-'), root);
}

function categorySection(ui, category) {
  const section = ui.nodes(node => node.type === 'section' && node.props['aria-labelledby'] === 'output-category-' + category)[0];
  assert.ok(section, 'Missing output category: ' + category);
  return section;
}

test('Create passes the actual selected product categories to output selection', () => {
  const products = [...mixedProducts(), fixture()[2]];
  const ui = interactive('CreateView', {
    products, onUpload: noop, initialSelectedIds: products.map(product => product.id), initialOutputStep: true,
  });
  const output = ui.component('OutputSelection');
  assert.deepEqual(Array.from(output.props.products, product => ({ id: product.id, category: product.category })), products.map(product => ({ id: product.id, category: product.category })));
  assert.equal(output.props.products[0].name, 'Wool trench coat');
});

test('outerwear uses exactly the ten ordered local examples while other categories retain their choices', () => {
  const products = mixedProducts();
  const { ui, selectProduct } = outputUi(products);
  const ecommerce = categorySection(ui, 'Ecommerce');
  const cards = outputCards(ui, ecommerce);
  assert.equal(outputCards(ui).length, 34);
  assert.deepEqual(cards.map(card => card.props['aria-label']), outerwearExamples.map(([name]) => name));
  assert.match(textContent(ecommerce), /10 templates/);
  for (const category of ['Lifestyle', 'Campaign']) assert.equal(outputCards(ui, categorySection(ui, category)).length, 12);
  const sharedNames = ['Lifestyle', 'Campaign'].map(category => outputCards(ui, categorySection(ui, category)).map(card => card.props['aria-label']));
  const publicDirectory = path.resolve(__dirname, '../public');
  const expectedFiles = outerwearExamples.map(([, filename]) => filename);
  cards.forEach((card, index) => {
    const images = ui.nodes(node => typeof node.props.src === 'string', card);
    const expectedPath = '/output-examples/outerwear/' + expectedFiles[index];
    const primary = ui.nodes(node => node.props.className?.includes('pf-output-card-image-primary'), card);
    assert.equal(primary.length, 1);
    assert.equal(primary[0].props.src, expectedPath, 'Correct example for ' + outerwearExamples[index][0]);
    assert.equal(images.length, 2, 'Each Outerwear card includes the leather example and product thumbnail');
    assert.equal(ui.nodes(node => node.props.className === 'pf-output-card-product-thumb', card).length, 1);
    assert.equal(ui.nodes(node => node.props.className?.includes('pf-output-card-image-hover'), card).length, 0);
    const asset = path.join(publicDirectory, expectedPath.slice(1));
    assert.ok(fs.statSync(asset).isFile(), 'Missing local example: ' + expectedPath);
    assert.ok(fs.statSync(asset).size > 0);
  });
  const publishedPngs = fs.readdirSync(path.join(publicDirectory, 'output-examples/outerwear')).filter(filename => filename.endsWith('.png'));
  assert.deepEqual(publishedPngs.sort(), [...expectedFiles].sort(), 'Publish only the ten leather-jacket examples');

  selectProduct(products[1]);
  assert.equal(outputCards(ui).length, 34);
  assert.equal(outputCards(ui, categorySection(ui, 'Ecommerce')).length, 10);
  assert.match(textContent(categorySection(ui, 'Ecommerce')), /10 templates/);
  assert.equal(ui.button('Folded View').props['aria-pressed'], false);
  assert.deepEqual(['Lifestyle', 'Campaign'].map(category => outputCards(ui, categorySection(ui, category)).map(card => card.props['aria-label'])), sharedNames);
  const defaultNames = outputCards(outputUi([{ ...products[1], category: null }]).ui).map(card => card.props['aria-label']);
  for (const category of [null, 'bags', 'unknown']) {
    const fallback = outputUi([{ ...products[1], category }]).ui;
    assert.deepEqual(outputCards(fallback).map(card => card.props['aria-label']), defaultNames);
    const current = fallback.nodes(node => node.props.className === 'pf-output-current')[0];
    assert.equal(textContent(fallback.nodes(node => node.type === 'p', current)[0]), 'Showing templates for ' + (category ? category.charAt(0).toUpperCase() + category.slice(1).toLowerCase() : 'this product'));
  }
});

test('mixed categories keep independent valid choices and show the matching popup names and thumbnails', () => {
  const products = mixedProducts();
  const { ui, rerender, selectProduct, chooseRecipe, selection } = outputUi(products);
  const current = ui.nodes(node => node.props.className === 'pf-output-current')[0];
  assert.equal(textContent(ui.nodes(node => node.type === 'p', current)[0]), 'Showing templates for Outerwear');
  assert.equal(textContent(ui.nodes(node => node.type === 'strong', current)[0]), 'Outerwear');
  chooseRecipe('Front Close');
  chooseRecipe('Fabric Shot');
  selectProduct(products[1]);
  const switched = ui.nodes(node => node.props.className === 'pf-output-current')[0];
  assert.equal(textContent(ui.nodes(node => node.type === 'p', switched)[0]), 'Showing templates for Tops');
  assert.equal(textContent(ui.nodes(node => node.type === 'strong', switched)[0]), 'Tops');
  assert.equal(outputCards(ui).some(card => card.props['aria-label'] === 'Front Close'), false);
  chooseRecipe('Folded View');
  chooseRecipe('Everyday Wear');
  selectProduct(products[0]);
  assert.equal(ui.button('Front Close').props['aria-pressed'], true);
  assert.equal(ui.button('Fabric Shot').props['aria-pressed'], true);
  assert.equal(ui.button('Everyday Wear').props['aria-pressed'], false, 'Shared output types are still selected separately per product');
  assert.deepEqual(selection(), {
    [products[0].id]: ['ecommerce-outerwear-front-close', 'ecommerce-outerwear-fabric'],
    [products[1].id]: ['ecommerce-tops-folded-view', 'lifestyle-everyday-wear'],
  });
  assert.equal(ui.button('Review selection').props.disabled, false);
  ui.button('Review selection').props.onClick();
  rerender();
  const dialog = summaryDialog(ui);
  const coat = ui.nodes(node => node.type === 'section' && node.props['aria-label'] === products[0].name, dialog)[0];
  const blouse = ui.nodes(node => node.type === 'section' && node.props['aria-label'] === products[1].name, dialog)[0];
  assert.match(textContent(coat), /Front Close/);
  assert.match(textContent(coat), /Fabric Shot/);
  assert.doesNotMatch(textContent(coat), /Folded View|Everyday Wear/);
  assert.match(textContent(blouse), /Folded View/);
  assert.match(textContent(blouse), /Everyday Wear/);
  assert.doesNotMatch(textContent(blouse), /Front Close|Fabric Shot/);
  assert.deepEqual(ui.nodes(node => typeof node.props.src === 'string', coat).map(node => node.props.src), [
    '/output-examples/outerwear/01-front-close.png',
    '/output-examples/outerwear/10-fabric-leather-texture.png',
  ]);
  assert.ok(ui.nodes(node => typeof node.props.src === 'string', blouse).every(node => !node.props.src.includes('/output-examples/outerwear/')));
  assert.match(textContent(ui.nodes(node => node.props.id === 'output-summary-description')[0]), /4 outputs selected across 2 products/);
});

test('stale ecommerce IDs from another product category cannot satisfy review or appear in the popup', () => {
  const products = mixedProducts();
  const { ui, rerender, selectProduct, chooseRecipe } = outputUi(products, {
    [products[0].id]: ['ecommerce-clean-product-shot'],
    [products[1].id]: ['ecommerce-outerwear-front-close'],
  });
  assert.equal(ui.button('Review selection').props.disabled, true);
  assert.match(textContent(ui.nodes(node => node.props.role === 'status')[0]), /0 outputs selected across 2 products/);
  chooseRecipe('Front Close');
  assert.equal(ui.button('Review selection').props.disabled, true, 'The blouse still needs a valid choice');
  selectProduct(products[1]);
  chooseRecipe('Folded View');
  assert.equal(ui.button('Review selection').props.disabled, false);
  ui.button('Review selection').props.onClick();
  rerender();
  const dialog = summaryDialog(ui);
  const coat = ui.nodes(node => node.type === 'section' && node.props['aria-label'] === products[0].name, dialog)[0];
  const blouse = ui.nodes(node => node.type === 'section' && node.props['aria-label'] === products[1].name, dialog)[0];
  assert.equal(ui.nodes(node => node.type === 'li', coat).length, 1);
  assert.equal(ui.nodes(node => node.type === 'li', blouse).length, 1);
  assert.doesNotMatch(textContent(coat), /Folded View/);
  assert.doesNotMatch(textContent(blouse), /Front Close/);
});

const footwearExamples = [
  ['Three-Quarter Product', '01-three-quarter-product.png'],
  ['Outer Side', '02-outer-side.png'],
  ['Inner Side', '03-inner-side.png'],
  ['Front View', '04-front-view.png'],
  ['Rear View', '05-rear-view.png'],
  ['Top View', '06-top-view.png'],
  ['Sole View', '07-sole-view.png'],
  ['Front on Feet', '09-front-on-feet.png'],
  ['Side on Feet', '10-side-on-feet.png'],
];

function footwearProducts() {
  return [
    { id: 'catalogue-white-trainers', name: 'White leather trainers', category: ' Footwear ', image_url: 'https://assets.example.test/trainers.jpg' },
    ...mixedProducts(),
  ];
}

test('normalized footwear categories show nine ordered portrait examples with the correct local PNGs', () => {
  const product = footwearProducts()[0];
  for (const category of ['footwear', ' Footwear ']) {
    const { ui } = outputUi([{ ...product, category }]);
    const ecommerce = categorySection(ui, 'Ecommerce');
    const cards = outputCards(ui, ecommerce);
    assert.equal(outputCards(ui).length, 33);
    assert.deepEqual(cards.map(card => card.props['aria-label']), footwearExamples.map(([name]) => name));
    assert.match(textContent(ecommerce), /9 templates/);
    cards.forEach((card, index) => {
      const [name, filename] = footwearExamples[index];
      const image = ui.nodes(node => typeof node.props.src === 'string', card)[0];
      assert.match(card.props.className, /\bpf-output-card-portrait\b/, name);
      assert.equal(card.props['aria-describedby'], 'output-description-ecommerce-footwear-' + filename.slice(3, -4));
      assert.equal(image.props.src, '/output-examples/footwear/' + filename, name);
      assert.equal(image.props.unoptimized, false, 'Local footwear examples use image optimization');
      const asset = path.resolve(__dirname, '../public/output-examples/footwear', filename);
      assert.ok(fs.statSync(asset).isFile(), 'Missing local example: ' + filename);
      assert.ok(fs.statSync(asset).size > 0);
    });
    for (const sharedCategory of ['Lifestyle', 'Campaign']) {
      const shared = outputCards(ui, categorySection(ui, sharedCategory));
      assert.equal(shared.length, 12);
      assert.ok(shared.every(card => !card.props.className.includes('pf-output-card-portrait')));
    }
  }
  const publicDirectory = path.resolve(__dirname, '../public/output-examples/footwear');
  const publishedPngs = fs.readdirSync(publicDirectory).filter(filename => filename.endsWith('.png'));
  assert.deepEqual(publishedPngs.sort(), footwearExamples.map(([, filename]) => filename).sort());
});

test('footwear, outerwear and default products retain independent choices and correct review images', () => {
  const products = footwearProducts();
  const { ui, rerender, selectProduct, chooseRecipe, selection } = outputUi(products);
  chooseRecipe('Three-Quarter Product');
  chooseRecipe('Sole View');
  selectProduct(products[1]);
  assert.equal(outputCards(ui).length, 34);
  chooseRecipe('Front Close');
  selectProduct(products[2]);
  assert.equal(outputCards(ui).length, 34);
  chooseRecipe('Folded View');
  selectProduct(products[0]);
  assert.equal(ui.button('Three-Quarter Product').props['aria-pressed'], true);
  assert.equal(ui.button('Sole View').props['aria-pressed'], true);
  assert.equal(ui.button('Front View').props['aria-pressed'], false);
  assert.deepEqual(selection(), {
    [products[0].id]: ['ecommerce-footwear-three-quarter-product', 'ecommerce-footwear-sole-view'],
    [products[1].id]: ['ecommerce-outerwear-front-close'],
    [products[2].id]: ['ecommerce-tops-folded-view'],
  });
  ui.button('Review selection').props.onClick();
  rerender();
  const dialog = summaryDialog(ui);
  const expected = [
    [products[0], ['Three-Quarter Product', 'Sole View'], ['/output-examples/footwear/01-three-quarter-product.png', '/output-examples/footwear/07-sole-view.png']],
    [products[1], ['Front Close'], ['/output-examples/outerwear/01-front-close.png']],
    [products[2], ['Folded View'], ['https://images.unsplash.com/photo-1547887538-e3a2f32cb1cc?w=600&q=85']],
  ];
  for (const [product, names, images] of expected) {
    const group = ui.nodes(node => node.type === 'section' && node.props['aria-label'] === product.name, dialog)[0];
    const tiles = ui.nodes(node => node.type === 'li', group);
    assert.equal(tiles.length, names.length, product.name);
    assert.deepEqual(tiles.map(tile => ui.nodes(node => node.type === 'b', tile).map(textContent).join('')), names);
    assert.deepEqual(ui.nodes(node => typeof node.props.src === 'string', group).map(node => node.props.src), images);
  }
  assert.match(textContent(ui.nodes(node => node.props.id === 'output-summary-description')[0]), /4 outputs selected across 3 products/);
});

test('stale footwear choices never count for other categories or let a mixed review skip products', () => {
  const products = footwearProducts();
  const { ui, rerender, selectProduct, chooseRecipe } = outputUi(products, {
    [products[0].id]: ['ecommerce-front-view', 'ecommerce-outerwear-front-close'],
    [products[1].id]: ['ecommerce-footwear-front-view'],
    [products[2].id]: ['ecommerce-footwear-three-quarter-product'],
  });
  assert.equal(ui.button('Review selection').props.disabled, true);
  assert.match(textContent(ui.nodes(node => node.props.role === 'status')[0]), /0 outputs selected across 3 products/);
  chooseRecipe('Front View');
  assert.equal(ui.button('Review selection').props.disabled, true);
  selectProduct(products[1]);
  chooseRecipe('Front Close');
  assert.equal(ui.button('Review selection').props.disabled, true);
  selectProduct(products[2]);
  chooseRecipe('Folded View');
  assert.equal(ui.button('Review selection').props.disabled, false);
  ui.button('Review selection').props.onClick();
  rerender();
  const dialog = summaryDialog(ui);
  assert.equal(ui.nodes(node => node.type === 'li', dialog).length, 3);
  assert.match(textContent(ui.nodes(node => node.props.id === 'output-summary-description')[0]), /3 outputs selected across 3 products/);
});

const socksExamples = [
  ['Three-Quarter on Feet', '01-three-quarter-on-feet.png'],
  ['Rear on Feet', '03-rear-on-feet.png'],
  ['Folded Product', '10-folded-product.png'],
  ['Flat Lay', '04-flat-lay.png'],
  ['Heel Detail', '06-heel-detail.png'],
  ['Knit Texture', '08-knit-texture.png'],
  ['Front on Feet', '09-front-on-feet.png'],
  ['Heel Detail on Foot', '06-heel-detail-on-foot.png'],
];

function socksProducts() {
  return [
    { id: 'catalogue-white-socks', name: 'White ribbed socks', category: ' Socks ', image_url: 'https://assets.example.test/socks.jpg' },
    ...footwearProducts().slice(0, 2),
  ];
}

test('normalized socks categories use eight ordered local examples and preserve the other 24 templates', () => {
  const product = socksProducts()[0];
  const baseline = outputUi([fixture()[0]]).ui;
  const sharedTemplates = ui => ['Lifestyle', 'Campaign'].map(category => outputCards(ui, categorySection(ui, category)).map(card => ({
    name: card.props['aria-label'],
    image: ui.nodes(node => typeof node.props.src === 'string', card)[0].props.src,
  })));
  for (const category of ['socks', '\t SoCkS \n']) {
    const { ui } = outputUi([{ ...product, category }]);
    const ecommerce = categorySection(ui, 'Ecommerce');
    const cards = outputCards(ui, ecommerce);
    assert.equal(outputCards(ui).length, 32);
    assert.deepEqual(cards.map(card => card.props['aria-label']), socksExamples.map(([name]) => name));
    assert.match(textContent(ecommerce), /8 templates/);
    assert.deepEqual(sharedTemplates(ui), sharedTemplates(baseline));
    for (const sharedCategory of ['Lifestyle', 'Campaign']) assert.equal(outputCards(ui, categorySection(ui, sharedCategory)).length, 12);
    cards.forEach((card, index) => {
      const [name, filename] = socksExamples[index];
      const image = ui.nodes(node => typeof node.props.src === 'string', card)[0];
      assert.equal(card.props['aria-describedby'], 'output-description-ecommerce-socks-' + filename.slice(3, -4));
      assert.equal(image.props.src, '/output-examples/socks/' + filename, name);
      assert.match(card.props.className, /\bpf-output-card-portrait\b/, name);
      assert.equal(image.props.unoptimized, false);
      const asset = path.resolve(__dirname, '../public/output-examples/socks', filename);
      assert.ok(fs.statSync(asset).isFile(), 'Missing local example: ' + filename);
      assert.ok(fs.statSync(asset).size > 0);
    });
  }
  const publicDirectory = path.resolve(__dirname, '../public/output-examples/socks');
  const publishedPngs = fs.readdirSync(publicDirectory).filter(filename => filename.endsWith('.png'));
  assert.deepEqual(publishedPngs.sort(), socksExamples.map(([, filename]) => filename).sort());
});

test('socks, footwear and outerwear keep independent choices and category-specific popup images', () => {
  const products = socksProducts();
  const { ui, rerender, selectProduct, chooseRecipe, selection } = outputUi(products, {
    [products[0].id]: ['ecommerce-footwear-front-on-feet', 'ecommerce-socks-side-profile', 'ecommerce-socks-cuff-detail', 'ecommerce-socks-toe-detail-on-foot'],
    [products[1].id]: ['ecommerce-socks-front-on-feet'],
    [products[2].id]: ['ecommerce-socks-three-quarter-on-feet'],
  });
  assert.equal(ui.button('Review selection').props.disabled, true);
  assert.match(textContent(ui.nodes(node => node.props.role === 'status')[0]), /0 outputs selected across 3 products/);
  chooseRecipe('Three-Quarter on Feet');
  chooseRecipe('Front on Feet');
  selectProduct(products[1]);
  assert.equal(ui.button('Front on Feet').props['aria-pressed'], false, 'Identically named sock and shoe templates remain separate choices');
  chooseRecipe('Front on Feet');
  assert.equal(ui.button('Review selection').props.disabled, true, 'Outerwear still needs its own valid choice');
  selectProduct(products[2]);
  chooseRecipe('Over-the-Shoulder (No Face)');
  selectProduct(products[0]);
  assert.equal(ui.button('Three-Quarter on Feet').props['aria-pressed'], true);
  assert.equal(ui.button('Front on Feet').props['aria-pressed'], true);
  assert.deepEqual(selection(), {
    [products[0].id]: ['ecommerce-socks-three-quarter-on-feet', 'ecommerce-socks-front-on-feet'],
    [products[1].id]: ['ecommerce-footwear-front-on-feet'],
    [products[2].id]: ['ecommerce-outerwear-over-the-shoulder'],
  });
  assert.equal(ui.button('Review selection').props.disabled, false);
  ui.button('Review selection').props.onClick();
  rerender();
  const dialog = summaryDialog(ui);
  const expected = [
    [products[0], ['Three-Quarter on Feet', 'Front on Feet'], ['/output-examples/socks/01-three-quarter-on-feet.png', '/output-examples/socks/09-front-on-feet.png']],
    [products[1], ['Front on Feet'], ['/output-examples/footwear/09-front-on-feet.png']],
    [products[2], ['Over-the-Shoulder (No Face)'], ['/output-examples/outerwear/03-over-the-shoulder-no-face.png']],
  ];
  for (const [product, names, images] of expected) {
    const group = ui.nodes(node => node.type === 'section' && node.props['aria-label'] === product.name, dialog)[0];
    const tiles = ui.nodes(node => node.type === 'li', group);
    assert.deepEqual(tiles.map(tile => ui.nodes(node => node.type === 'b', tile).map(textContent).join('')), names);
    assert.deepEqual(ui.nodes(node => typeof node.props.src === 'string', group).map(node => node.props.src), images);
  }
  assert.match(textContent(ui.nodes(node => node.props.id === 'output-summary-description')[0]), /4 outputs selected across 3 products/);
});

const bottomsExamples = [
  ['Front View', '01-front-view.png'],
  ['Back View', '02-back-view.png'],
  ['Side / Three-Quarter Product', '03-side-angle-product.png'],
  ['Folded Product Flat Lay', '04-folded-product-flat-lay.png'],
  ['Front Model', '05-front-model.png'],
  ['Back Model', '06-back-model.png'],
  ['Waistband & Closure Detail', '07-waistband-closure-detail.png'],
  ['Pocket Panel Detail', '08-pocket-panel-detail.png'],
  ['Hem & Leg Detail', '09-hem-leg-detail.png'],
];

test('normalized bottoms categories use nine ordered local examples and preserve shared choices', () => {
  const product = { id: 'catalogue-indigo-jeans', name: 'Dark indigo straight-leg jeans', category: ' Bottoms ', image_url: 'https://assets.example.test/jeans.jpg' };
  const baseline = outputUi([fixture()[0]]).ui;
  const sharedTemplates = ui => ['Lifestyle', 'Campaign'].map(category => outputCards(ui, categorySection(ui, category)).map(card => card.props['aria-label']));

  for (const category of ['bottoms', '\t BoTtOmS \n']) {
    const { ui } = outputUi([{ ...product, category }]);
    const ecommerce = categorySection(ui, 'Ecommerce');
    const cards = outputCards(ui, ecommerce);
    assert.equal(outputCards(ui).length, 33);
    assert.deepEqual(cards.map(card => card.props['aria-label']), bottomsExamples.map(([name]) => name));
    assert.match(textContent(ecommerce), /9 templates/);
    assert.deepEqual(sharedTemplates(ui), sharedTemplates(baseline));
    for (const sharedCategory of ['Lifestyle', 'Campaign']) assert.equal(outputCards(ui, categorySection(ui, sharedCategory)).length, 12);
    cards.forEach((card, index) => {
      const [name, filename] = bottomsExamples[index];
      const image = ui.nodes(node => typeof node.props.src === 'string', card)[0];
      assert.equal(card.props['aria-describedby'], 'output-description-ecommerce-bottoms-' + filename.slice(3, -4));
      assert.equal(image.props.src, '/output-examples/bottoms/' + filename, name);
      assert.match(card.props.className, /\bpf-output-card-portrait\b/, name);
      assert.equal(image.props.unoptimized, false);
      const asset = path.resolve(__dirname, '../public/output-examples/bottoms', filename);
      assert.ok(fs.statSync(asset).isFile(), 'Missing local example: ' + filename);
      assert.ok(fs.statSync(asset).size > 0);
    });
  }

  const publicDirectory = path.resolve(__dirname, '../public/output-examples/bottoms');
  const publishedPngs = fs.readdirSync(publicDirectory).filter(filename => filename.endsWith('.png'));
  assert.deepEqual(publishedPngs.sort(), bottomsExamples.map(([, filename]) => filename).sort());
});

const underwearExamples = [
  ['Front with Model (No Face)', '01-front-model.png'],
  ['Front Flat Lay', '02-front-flat-lay.png'],
  ['Back Flat Lay', '03-back-flat-lay.png'],
  ['Rear Three-Quarter', '04-rear-three-quarter.png'],
  ['Front Product', '05-front-product.png'],
  ['Side Profile', '06-side-profile.png'],
  ['Waistband & Fabric Detail', '07-waistband-detail.png'],
];

test('underwear uses seven ordered local Ecommerce examples and category-specific IDs', () => {
  const product = { id: 'catalogue-grey-boxers', name: 'Grey cotton boxer briefs', category: ' Underwear ', product_family: 'lower_body_underwear', image_url: 'https://assets.example.test/boxers.jpg' };
  const { ui, chooseRecipe, selection } = outputUi([product]);
  const ecommerce = categorySection(ui, 'Ecommerce');
  const cards = outputCards(ui, ecommerce);
  assert.equal(cards.length, 7);
  assert.deepEqual(cards.map(card => card.props['aria-label']), underwearExamples.map(([name]) => name));
  assert.match(textContent(ecommerce), /7 templates/);
  cards.forEach((card, index) => {
    const [name, filename] = underwearExamples[index];
    const image = ui.nodes(node => typeof node.props.src === 'string', card)[0];
    assert.equal(image.props.src, '/output-examples/underwear/' + filename, name);
    assert.equal(image.props.unoptimized, false);
    const asset = path.resolve(__dirname, '../public/output-examples/underwear', filename);
    assert.ok(fs.statSync(asset).isFile(), 'Missing local example: ' + filename);
    assert.ok(fs.statSync(asset).size > 0);
  });
  chooseRecipe('Front Product');
  chooseRecipe('Waistband & Fabric Detail');
  assert.deepEqual(selection(), { [product.id]: ['ecommerce-underwear-front-product', 'ecommerce-underwear-waistband-detail'] });
  assert.equal(outputCards(ui).length, 31);
});

test('underwear templates are limited to lower-body family products', () => {
  const lower = { id: 'catalogue-lower-underwear', name: 'Boxer briefs', category: 'underwear', product_family: 'lower_body_underwear', image_url: null };
  const bra = { id: 'catalogue-bra', name: 'Soft bralette', category: 'underwear', product_family: 'bra', image_url: null };
  const lowerUi = outputUi([lower]).ui;
  assert.equal(outputCards(lowerUi, categorySection(lowerUi, 'Ecommerce')).length, 7);
  assert.equal(textContent(categorySection(lowerUi, 'Ecommerce')).includes('7 templates'), true);
  const braUi = outputUi([bra]).ui;
  assert.equal(outputCards(braUi, categorySection(braUi, 'Ecommerce')).length, 0);
  assert.equal(textContent(categorySection(braUi, 'Ecommerce')).includes('0 templates'), true);
});

test('bottoms selection uses category-specific IDs and approved detail thumbnails', () => {
  const product = { id: 'catalogue-indigo-jeans-selection', name: 'Dark indigo jeans', category: 'bottoms', image_url: null };
  const { ui, rerender, chooseRecipe, selection } = outputUi([product]);
  chooseRecipe('Front View');
  chooseRecipe('Pocket Panel Detail');

  assert.deepEqual(selection(), {
    [product.id]: ['ecommerce-bottoms-front-view', 'ecommerce-bottoms-pocket-panel-detail'],
  });
  assert.equal(ui.button('Review selection').props.disabled, false);
  ui.button('Review selection').props.onClick();
  rerender();
  const dialog = summaryDialog(ui);
  assert.deepEqual(ui.nodes(node => typeof node.props.src === 'string', dialog).map(node => node.props.src), [
    '/output-examples/bottoms/01-front-view.png',
    '/output-examples/bottoms/08-pocket-panel-detail.png',
  ]);
});
