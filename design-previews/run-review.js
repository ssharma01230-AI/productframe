/* UI-only mock. No fetch, API requests, uploads, browser storage, or production imports. */
(() => {
  'use strict';

  const photos = {
    jacket: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800&q=85',
    trainers: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=85',
    bag: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=800&q=85',
    dress: 'https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=800&q=85',
    rejected: 'https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=500&q=85'
  };
  const seedProducts = [
    { id: 1, name: 'Everyday leather jacket', type: 'Zip-front leather biker jacket', category: 'Outerwear', colours: 'Black, silver-tone hardware', materials: 'Appears to be grained leather', features: 'Notched collar, asymmetric zip, zipped pockets, adjustable belt', description: 'A black biker jacket with a structured silhouette and distinctive silver-tone hardware. An asymmetric front zip, notched collar and zipped pockets give it a classic finish, while the adjustable waist belt adds definition.', confidence: 98, photo: photos.jacket, count: 4 },
    { id: 2, name: 'Courtline trainers', type: 'Low-top lace-up trainers', category: 'Footwear', colours: 'Scarlet red, white accents', materials: 'Appears to be mesh, rubber sole', features: 'Lace-up fastening, textured upper, padded collar, contrasting sole', description: 'Scarlet low-top trainers with a textured upper, tonal laces and a contrasting sole. The gently padded collar frames the ankle, while the curved panels and streamlined profile create a lightweight, sport-inspired everyday shape.', confidence: 97, photo: photos.trainers, count: 4 },
    { id: 3, name: 'Studio leather bag', type: 'Structured top-handle handbag', category: 'Accessories', colours: 'Tomato red, gold-tone hardware', materials: 'Appears to be textured leather', features: 'Structured body, top handles, adjustable shoulder strap, metal fittings', description: 'A structured handbag with a vivid red finish and neat metal fittings. Top handles provide a compact carrying option, while a longer strap offers versatility. Its clean outline keeps the focus on the leather-like surface.', confidence: 96, photo: photos.bag, count: 3 },
    { id: 4, name: 'Meadow day dress', type: 'Printed lightweight summer dress', category: 'Dresses', colours: 'Ivory, soft botanical tones', materials: 'Appears to be a light woven fabric', features: 'Botanical print, fitted waist, flowing skirt, lightweight construction', description: 'A light printed dress with a softly defined waist and a flowing skirt. The delicate pattern brings detail to the pale fabric, while the relaxed silhouette gives the piece an easy, warm-weather feel.', confidence: 95, photo: photos.dress, count: 3 }
  ];
  const rejectedImage = { number: 15, filename: 'IMG_0015.jpg', photo: photos.rejected, reason: 'Not a wearable fashion product.' };
  const editableFields = new Set(['name', 'type', 'colours', 'materials', 'features', 'description']);
  const paths = {
    chevronLeft: '<path d="m14 6-6 6 6 6"/>',
    chevronRight: '<path d="m10 6 6 6-6 6"/>',
    close: '<path d="m6 6 12 12M18 6 6 18"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
    upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    home: '<path d="m3 10 9-7 9 7v11h-7v-7h-4v7H3Z"/>',
    layers: '<path d="m3 7 9-4 9 4-9 4-9-4Zm0 5 9 4 9-4M3 17l9 4 9-4"/>',
    image: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
    shield: '<path d="m12 3 8 3v5c0 5-4 8-8 10-4-2-8-5-8-10V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
    warning: '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3v.1"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
    sparkle: '<path d="m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3Z"/>',
    replay: '<path d="M3 10a9 9 0 1 1 1 8M3 4v6h6"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>'
  };
  const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.image}</svg>`;
  const esc = value => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const resetProducts = () => seedProducts.map(product => ({ ...product, status: 'pending', view: 0 }));
  let products = resetProducts();
  let selectedId = 1;
  let mode = document.body.dataset.initialState || 'complete';
  let reviewScreen = 'review';
  const selectedOutputTypes = new Set();
  const outputOptions = [
    { id: 'ecommerce', name: 'Ecommerce', description: 'Clean product imagery, ready for your shop.', icon: 'grid' },
    { id: 'lifestyle', name: 'Lifestyle', description: 'Your pieces, styled for the everyday.', icon: 'image' },
    { id: 'campaign', name: 'Campaign', description: 'Art-directed imagery with a point of view.', icon: 'sparkle' }
  ];
  let showingRejected = mode === 'rejected';
  let confirmationId = null;
  let loadingTimer = null;
  let toastTimer = null;
  const uploadCount = seedProducts.reduce((total, product) => total + product.count, 0) + 1;
  const loadingPhases = [
    { title: 'Checking your images', detail: 'Screening for usable product photos.' },
    { title: 'Finding matching products', detail: 'Matching different views of the same product.' },
    { title: 'Adding the finishing touches', detail: 'Drafting the details for your review.' }
  ];
  let loadingStep = 0;
  let announcedPhase = -1;

  function batchProgress(step, total = uploadCount) {
    const tick = Math.max(0, Math.min(step, 16));
    return {
      checked: Math.floor(total * Math.min(tick / 9, 1)),
      percent: Math.round(tick / 16 * 100),
      phase: tick < 10 ? 0 : tick < 13 ? 1 : 2
    };
  }
  const root = document.getElementById('preview-root');

  root.innerHTML = `
    <main class="workspace">
      <aside class="workspace-sidebar"><div class="brand"><span class="brand-mark">P</span>productframe</div><div class="workspace-nav" aria-hidden="true"><span>${icon('home')}Home</span><span class="selected">${icon('grid')}Products</span><span>${icon('layers')}Brand</span><span>${icon('layers')}Packs</span></div></aside>
      <section class="workspace-content"><header><span>Studio / <b>Product content</b></span><span class="avatar">SS</span></header><div class="workspace-intro"><div class="eyebrow">PRODUCTFRAME / CONTENT STUDIO</div><h1>Start with your product.</h1><p>A few photos. A little context. A product story ready to take shape.</p><div class="background-upload">${icon('upload')}<strong>15 images ready for review</strong><p class="mock-label">Static design preview · no real uploads</p><button class="button primary" id="open-review">Open run review ${icon('arrow')}</button></div></div></section>
    </main>
    <dialog class="run-dialog" id="run-review" aria-labelledby="run-title" aria-describedby="run-description">
      <section class="run-panel" id="run-panel"></section>
      <nav class="demo-nav" aria-label="Mock preview states"><span class="demo-label">MOCK PREVIEW</span><button type="button" data-state="loading">Loading</button><button type="button" data-state="complete">Completed</button><button type="button" data-state="cancel">Cancellation</button><button type="button" data-state="rejected">Rejected image</button><button type="button" class="replay-button" id="replay-opening" aria-label="Replay popup opening" title="Replay popup opening">${icon('replay')}</button></nav>
      <div class="sr-only" id="announcer" aria-live="polite" aria-atomic="true"></div>
      <div class="toast" id="toast" role="status" hidden></div>
    </dialog>`;
  const dialog = document.getElementById('run-review');
  const panel = document.getElementById('run-panel');
  const announce = text => { document.getElementById('announcer').textContent = text; };
  const selectedProduct = () => products.find(product => product.id === selectedId);
  const approvedProducts = () => products.filter(product => product.status === 'approved');
  function reviewStats() {
    const cancelled = products.filter(product => product.status === 'cancelled').length;
    const approved = products.filter(product => product.status === 'approved').length;
    const eligible = products.filter(product => product.status !== 'cancelled');
    const reviewed = eligible.filter(product => product.status !== 'pending').length;
    return { cancelled, approved, total: eligible.length, reviewed, complete: reviewed === eligible.length };
  }

  function header() {
    const isLoading = mode === 'loading';
    return `<header class="run-heading"><div class="heading-line"><h2 id="run-title" tabindex="-1">${isLoading ? 'Reviewing your products' : '4 unique products identified'}</h2><div class="heading-controls"><span class="state-badge ${isLoading ? 'processing' : ''}">${isLoading ? '<span class="dot"></span>Processing' : `${icon('check')}Analysis complete`}</span><button type="button" class="icon-button" data-action="close-review" aria-label="Close run review" title="Close review; keep mock decisions">${icon('close')}</button></div></div><p class="heading-description${isLoading ? ' sr-only' : ''}" id="run-description">${isLoading ? 'We’ll check your images, group products and get the details ready.' : 'A considered first pass. Review the details, then make them yours.'}</p></header><section class="run-metrics" aria-label="Run summary"><div class="metric">${icon('image')}<strong>${uploadCount}</strong><span>images uploaded</span></div><div class="metric">${icon('shield')}<strong id="metric-passed">${isLoading ? '—' : '14'}</strong><span>passed validation</span></div><div class="metric">${icon('layers')}<strong id="metric-products">${isLoading ? '—' : '4'}</strong><span>unique products</span></div><div class="metric rejected">${icon('warning')}<strong id="metric-rejected">${isLoading ? '—' : '1'}</strong><span>rejected image</span></div></section>`;
  }

  function renderCards() {
    return products.map(product => `<button class="product-card" type="button" data-product="${product.id}" aria-label="Review product ${product.id}: ${esc(product.name || 'Untitled product')}" aria-pressed="${selectedId === product.id && !showingRejected}" aria-describedby="product-status-${product.id}"><span class="card-image"><img src="${product.photo}" alt="" loading="eager">${product.status === 'approved' ? `<span class="thumbnail-approved" aria-hidden="true">${icon('check')}</span>` : ''}</span><span class="card-copy"><span class="card-number">PRODUCT ${String(product.id).padStart(2, '0')}</span><span class="card-name">${esc(product.name || 'Untitled product')}</span><span class="card-meta ${product.status}" id="product-status-${product.id}">${product.status === 'pending' ? `${product.count} images · To review` : `${icon(product.status === 'approved' ? 'check' : 'close')}${product.status[0].toUpperCase() + product.status.slice(1)}`}</span></span></button>`).join('');
  }

  function rail() {
    return `<aside class="product-rail" aria-label="Products in this run"><div class="rail-heading"><span class="eyebrow">Your products</span><span>04</span></div><div class="product-list" id="product-list">${renderCards()}</div><div class="rejected-shortcut"><button type="button" data-action="show-rejected" aria-pressed="${showingRejected}">${icon('warning')}<span><b>1 image not included</b><small>View validation note →</small></span></button></div></aside>`;
  }

  function photoStyles(view) {
    return [`object-position:50% 50%;transform:scale(1)`, `object-position:45% 25%;transform:scale(1.18)`, `object-position:65% 60%;transform:scale(1.38)`, `object-position:35% 80%;transform:scale(1.6)`][view];
  }

  function setProductView(index) {
    const product = selectedProduct();
    const hero = document.getElementById('hero-photo');
    if (!hero || product.count < 1 || !Number.isInteger(index)) return;
    product.view = (index % product.count + product.count) % product.count;
    hero.style.cssText = photoStyles(product.view);
    hero.alt = `${product.name || 'Untitled product'}, mock view ${product.view + 1}`;
    document.getElementById('image-view-label').textContent = `Image ${product.view + 1} of ${product.count}`;
    panel.querySelectorAll('[data-view]').forEach(thumb => thumb.setAttribute('aria-pressed', String(Number(thumb.dataset.view) === product.view)));
    announce(`Image ${product.view + 1} of ${product.count} for ${product.name || 'Untitled product'}.`);
  }

  function productDetail() {
    const product = selectedProduct();
    const locked = product.status !== 'pending';
    const field = (name, label, textarea = false, full = true) => `<label class="field ${full ? 'full' : ''}" for="field-${name}"><span>${label}</span>${textarea ? `<textarea id="field-${name}" name="${name}" data-field="${name}" class="${name === 'description' ? 'description' : ''}" rows="${name === 'description' ? 4 : 2}" ${locked ? 'readonly' : ''}>${esc(product[name])}</textarea>` : `<input id="field-${name}" name="${name}" data-field="${name}" value="${esc(product[name])}" ${name === 'name' ? 'required maxlength="160" aria-describedby="name-error"' : 'maxlength="400"'} ${locked ? 'readonly' : ''}>`}</label>`;
    return `<section class="product-detail" id="product-detail" aria-label="Selected product details"><div class="detail-heading"><div class="detail-heading-left"><span class="eyebrow">Product ${String(product.id).padStart(2, '0')} / 04</span></div><button type="button" class="icon-button" data-action="ask-cancel" aria-label="Cancel product ${product.id}" title="Cancel this product" ${locked ? 'disabled' : ''}>${icon('close')}</button></div>${locked ? `<div class="decision-note ${product.status}"><span>${product.status === 'approved' ? 'Approved for the Product Library in this mock run.' : `${product.status === 'cancelled' ? 'Cancelled' : 'Rejected'} — kept in this run, excluded from the library.`}</span><button class="text-button" type="button" data-action="undo-decision">Change decision</button></div>` : ''}<div class="product-content"><div class="gallery"><div class="hero-image"><img id="hero-photo" src="${product.photo}" alt="${esc(product.name)}, mock view ${product.view + 1}" style="${photoStyles(product.view)}"><span class="image-label" id="image-view-label">Image ${product.view + 1} of ${product.count}</span>${product.count > 1 ? `<button type="button" class="gallery-arrow previous" data-action="previous-image" aria-label="Previous image" aria-controls="hero-photo">${icon('chevronLeft')}</button><button type="button" class="gallery-arrow next" data-action="next-image" aria-label="Next image" aria-controls="hero-photo">${icon('chevronRight')}</button>` : ''}</div><div class="thumbnails" aria-label="Grouped product images">${Array.from({length: product.count}, (_, index) => `<button class="thumbnail" type="button" data-view="${index}" aria-label="View image ${index + 1} of ${esc(product.name)}" aria-pressed="${product.view === index}"><img src="${product.photo}" alt="" style="${photoStyles(index)}"></button>`).join('')}</div><label class="category-field" for="category"><span>Category ${icon('lock')}</span><input id="category" value="${esc(product.category)}" readonly aria-readonly="true" aria-describedby="category-hint"><small class="category-hint" id="category-hint">Read-only classification</small></label></div><form class="product-form" id="product-form"><div class="fields">${field('name', 'Product name')}${field('type', 'Product type')}${field('colours', 'Colours', false, false)}${field('materials', 'Materials', false, false)}${field('features', 'Features', true)}${field('description', 'Description', true)}</div><p class="error-message" id="name-error" hidden>Please give this product a name.</p><p class="form-note">${icon('sparkle')}Suggested details. Your approval makes them final.</p></form></div><div id="confirmation-slot"></div></section>`;
  }

  function rejectionDetail() {
    return `<section class="product-detail rejection-view" id="product-detail" aria-label="Rejected image details"><h3>Products that didn’t quite fit</h3><p>Your other 14 images are ready. We couldn’t use this one.</p><article class="rejection-card"><div class="rejection-photo"><img src="${rejectedImage.photo}" alt="Mock rejected upload showing a skincare product"></div><div><span class="eyebrow">Image ${rejectedImage.number}</span><h4>${rejectedImage.filename}</h4><p><span class="reason-label">Reason:</span> <span id="rejection-reason">${rejectedImage.reason}</span></p></div></article><div class="rejection-explainer">${icon('image')}<span>Try clear, well-lit photos of clothing, shoes, bags or fashion accessories.</span></div></section>`;
  }

  function footer() {
    if (mode === 'loading') return `<footer class="run-footer"><div class="review-progress-label">${icon('clock')}<span>Review is up next</span></div><div class="footer-actions"><button class="button" type="button" data-action="finish-demo">Skip to completed preview →</button></div></footer>`;
    const { reviewed, total, approved, cancelled, complete } = reviewStats();
    const label = total === 0 ? 'All products cancelled' : `${reviewed} of ${total} products reviewed`;
    const decisionSummary = `${approved} approved${cancelled ? ` · ${cancelled} cancelled` : ''}`;
    const progress = total ? `<div class="mini-progress" role="progressbar" aria-label="Products reviewed" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${reviewed}" aria-valuetext="${label}${cancelled ? `, ${cancelled} cancelled` : ''}"><span style="width:${reviewed / total * 100}%"></span></div>` : '';
    return `<footer class="run-footer"><div class="review-progress"><div class="review-progress-label">${icon(total === 0 ? 'close' : complete ? 'check' : 'layers')}<span>${label}</span></div><div class="progress-caption">${progress}<span>${decisionSummary}</span></div></div><div class="footer-actions">${showingRejected ? `<button class="button" type="button" data-action="back-to-products">Back to products ${icon('arrow')}</button>` : complete ? '<button class="button primary" type="button" data-action="finish-review">Done reviewing ✓</button>' : `<button class="button primary" type="button" data-action="approve" ${selectedProduct().status !== 'pending' ? 'disabled' : ''}>${icon('check')}Approve product</button>`}</div></footer>`;
  }

  function stepHeader(title, description, badge) {
    return `<header class="run-heading step-heading"><div class="heading-line"><h2 id="run-title" tabindex="-1">${title}</h2><div class="heading-controls"><span class="state-badge">${icon('check')}${badge}</span><button type="button" class="icon-button" data-action="close-review" aria-label="Close review" title="Close preview; keep mock decisions">${icon('close')}</button></div></div><p class="heading-description" id="run-description">${description}</p></header>`;
  }

  function approvedSummary() {
    const approved = approvedProducts();
    const count = approved.length;
    const description = count ? `${count} approved ${count === 1 ? 'product' : 'products'}. A final look before you bring ${count === 1 ? 'it' : 'them'} to life.` : 'Head back to review to choose the pieces you’d like to work with.';
    const cards = approved.map((product, index) => `<li class="approved-card" style="--card-index:${index}"><div class="approved-photo"><img src="${product.photo}" alt="" loading="eager"><span class="approved-photo-badge" aria-label="Approved">${icon('check')}</span></div><h3>${esc(product.name)}</h3></li>`).join('');
    return stepHeader(count ? 'Your edit is ready' : 'No products approved', description, 'Review complete') + `<section class="summary-body" aria-label="Approved products">${count ? `<ul class="approved-grid" style="--approved-count:${count}">${cards}</ul><p class="summary-next">The pieces are picked. Let’s set the scene.</p>` : `<div class="summary-empty">${icon('layers')}<h3>A fresh edit starts here.</h3><p>All four products were cancelled. You can change any decision in the review.</p></div>`}</section><footer class="run-footer step-footer"><button class="button step-back" type="button" data-action="back-to-review">${icon('chevronLeft')}Back to review</button>${count ? `<button class="button primary" type="button" data-action="produce-outputs">Produce outputs ${icon('arrow')}</button>` : ''}</footer>`;
  }

  function outputStep() {
    const approved = approvedProducts();
    return stepHeader('Produce outputs', 'Choose how your products take the spotlight.', 'Products approved') + `<section class="outputs-body" aria-label="Output options"><ul class="approved-strip" aria-label="Approved products for outputs">${approved.map(product => `<li><span class="card-image"><img src="${product.photo}" alt=""></span><span>${esc(product.name)}</span></li>`).join('')}</ul><fieldset class="output-fieldset"><legend>What would you like to create?</legend><p class="output-hint" id="output-hint">Choose one or more styles for your ${approved.length === 1 ? 'product' : 'products'}.</p><div class="output-options">${outputOptions.map(option => `<label class="output-option${selectedOutputTypes.has(option.id) ? ' selected' : ''}"><input type="checkbox" data-output="${option.id}" ${selectedOutputTypes.has(option.id) ? 'checked' : ''} aria-labelledby="output-${option.id}-name" aria-describedby="output-${option.id}-description"><span class="output-option-icon" aria-hidden="true">${icon(option.icon)}</span><span class="output-option-name" id="output-${option.id}-name">${option.name}</span><span class="output-option-description" id="output-${option.id}-description">${option.description}</span></label>`).join('')}</div></fieldset><p class="output-preview-note">Mock preview only. No images or files will be generated.</p><p class="generation-notice" id="generation-notice" hidden></p></section><footer class="run-footer step-footer"><button class="button step-back" type="button" data-action="back-to-approved">${icon('chevronLeft')}Your approved products</button><div class="footer-actions output-actions"><span class="output-count" id="output-count">${selectedOutputTypes.size} selected</span><button class="button primary" type="button" data-action="preview-generation" ${selectedOutputTypes.size ? '' : 'disabled'}>Preview generation ${icon('arrow')}</button></div></footer>`;
  }

  function goToScreen(next) {
    if (mode === 'loading' || next === reviewScreen) return;
    if (next === 'approved' && (!reviewStats().complete || !['review', 'outputs'].includes(reviewScreen))) return;
    if (next === 'outputs' && (reviewScreen !== 'approved' || !reviewStats().complete || !approvedProducts().length)) return;
    if (!['review', 'approved', 'outputs'].includes(next)) return;
    closeConfirmation(false);
    clearTimeout(toastTimer);
    document.getElementById('toast').hidden = true;
    reviewScreen = next;
    showingRejected = false;
    render(true);
    if (dialog.open) document.getElementById('run-title').focus({ preventScroll: true });
    const count = approvedProducts().length;
    announce(next === 'review' ? 'Back to review. Your edits and decisions are unchanged.' : next === 'approved' ? `${count} approved ${count === 1 ? 'product' : 'products'} ready to view.` : 'Choose your output styles. This is a mock preview only.');
  }

  function loadingBody() {
    return `<section class="loading-body" aria-label="Batch analysis"><div class="batch-progress"><div class="loading-thumbnails" aria-hidden="true">${Array.from({ length: 3 }, (_, index) => `<div class="loading-thumbnail" style="--thumbnail-index:${index}">${icon('image')}</div>`).join('')}</div><div class="loading-progress-details"><div class="loading-status"><span class="status-spinner" aria-hidden="true"></span><h3 id="processing-message">Checking your images</h3></div><div class="processing-row"><span id="processing-count">0 of ${uploadCount} images checked</span><span id="processing-percent">0%</span></div></div><div class="processing-track" role="progressbar" aria-label="Overall analysis progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span id="processing-fill" style="width:0%"></span></div></div></section>`;
  }

  function render(animate = false) {
    panel.dataset.screen = reviewScreen;
    panel.classList.toggle('screen-transition', animate);
    panel.innerHTML = reviewScreen === 'approved' ? approvedSummary() : reviewScreen === 'outputs' ? outputStep() : header() + (mode === 'loading' ? loadingBody() : `<div class="run-body">${rail()}${showingRejected ? rejectionDetail() : productDetail()}</div>`) + footer();
    document.querySelectorAll('[data-state]').forEach(button => button.setAttribute('aria-pressed', String(reviewScreen === 'review' && button.dataset.state === mode)));
    bindImageFallbacks();
    if (mode === 'loading') updateLoading();
  }

  function bindImageFallbacks() {
    panel.querySelectorAll('img').forEach(image => {
      const fail = () => {
        image.style.visibility = 'hidden';
        if (['hero-image', 'rejection-photo', 'approved-photo'].some(name => image.parentElement.classList.contains(name))) {
          if (!image.parentElement.querySelector('.image-fallback')) image.insertAdjacentHTML('afterend', `<span class="image-fallback">${icon('image')}Reference photo unavailable<br>Connect to the internet to load images.</span>`);
        }
      };
      image.addEventListener('error', fail, { once: true });
      if (image.complete && image.naturalWidth === 0) fail();
    });
  }

  function showToast(message) {
    clearTimeout(toastTimer);
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.hidden = false;
    announce(message);
    toastTimer = setTimeout(() => { toast.hidden = true; }, 3000);
  }

  function closeConfirmation(restore = true) {
    confirmationId = null;
    const slot = document.getElementById('confirmation-slot');
    if (slot) slot.replaceChildren();
    if (restore) panel.querySelector('[data-action="ask-cancel"]')?.focus({ preventScroll: true });
  }

  function openConfirmation() {
    if (selectedProduct().status !== 'pending') return;
    confirmationId = selectedId;
    document.getElementById('confirmation-slot').innerHTML = `<div class="confirmation" role="alertdialog" aria-labelledby="cancel-title" aria-describedby="cancel-description"><h3 id="cancel-title">Cancel this product?</h3><p id="cancel-description">It will stay in this run, but won’t enter your Product Library.</p><div class="confirmation-actions"><button class="button" type="button" data-action="keep-product">Keep product</button><button class="button cancel-confirm" type="button" data-action="confirm-cancel">Cancel product</button></div></div>`;
    panel.querySelector('[data-action="keep-product"]').focus({ preventScroll: true });
  }

  function makeDecision(status) {
    const product = selectedProduct();
    if (product.status !== 'pending') return;
    if (status === 'approved' && !product.name.trim()) {
      const input = document.getElementById('field-name');
      input.setAttribute('aria-invalid', 'true');
      document.getElementById('name-error').hidden = false;
      input.focus();
      announce('Please give this product a name before approving.');
      return;
    }
    product.name = product.name.trim();
    product.status = status;
    confirmationId = null;
    render();
    panel.querySelector(`[data-product="${selectedId}"]`).focus({ preventScroll: true });
    showToast(`${product.name || 'Untitled product'} ${status}. Preview only.`);
  }

  function updateLoading() {
    if (mode !== 'loading') return;
    const { checked, percent, phase } = batchProgress(loadingStep);
    const stage = loadingPhases[phase];
    document.getElementById('processing-count').textContent = `${checked} of ${uploadCount} images checked`;
    document.getElementById('processing-percent').textContent = `${percent}%`;
    document.getElementById('processing-fill').style.width = `${percent}%`;
    const progress = panel.querySelector('.processing-track');
    progress.setAttribute('aria-valuenow', String(percent));
    progress.setAttribute('aria-valuetext', `${percent}% overall. ${checked} of ${uploadCount} images checked. ${stage.title}.`);
    document.getElementById('metric-passed').textContent = checked ? String(Math.min(checked, uploadCount - 1)) : '—';
    document.getElementById('metric-products').textContent = phase === 2 ? String(products.length) : '—';
    document.getElementById('metric-rejected').textContent = checked === uploadCount ? '1' : '—';
    document.getElementById('processing-message').textContent = stage.title;
    if (announcedPhase !== phase) {
      announcedPhase = phase;
      announce(stage.title + '. ' + stage.detail);
    }
  }

  function startLoading() {
    clearInterval(loadingTimer);
    loadingStep = 0;
    announcedPhase = -1;
    updateLoading();
    loadingTimer = setInterval(() => {
      loadingStep += 1;
      if (loadingStep < 16) updateLoading();
      else {
        clearInterval(loadingTimer);
        loadingTimer = null;
        mode = 'complete'; showingRejected = false; render();
        if (dialog.open) document.getElementById('run-title').focus({ preventScroll: true });
        announce('Analysis complete. 14 images passed validation, 4 unique products identified, 1 rejected image.');
      }
    }, 700);
  }

  function switchState(nextMode) {
    clearInterval(loadingTimer);
    clearTimeout(toastTimer);
    document.getElementById('toast').hidden = true;
    mode = nextMode; selectedId = 1; products = resetProducts(); confirmationId = null;
    reviewScreen = 'review'; selectedOutputTypes.clear();
    loadingStep = 0; announcedPhase = -1; loadingTimer = null;
    showingRejected = nextMode === 'rejected';
    render();
    if (mode === 'loading') startLoading();
    if (mode === 'cancel') openConfirmation();
    announce(`${nextMode === 'cancel' ? 'Cancellation confirmation' : nextMode} mock preview. Changes reset for this preview state.`);
  }

  dialog.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button || button.disabled) return;
    if (button.dataset.state) { switchState(button.dataset.state); return; }
    const action = button.dataset.action;
    if (action === 'close-review') { closeConfirmation(false); dialog.close(); document.getElementById('open-review').focus(); return; }
    if (action === 'finish-review') { if (reviewScreen === 'review') goToScreen('approved'); return; }
    if (action === 'back-to-review') { goToScreen('review'); return; }
    if (action === 'produce-outputs') { goToScreen('outputs'); return; }
    if (action === 'back-to-approved') { if (reviewScreen === 'outputs') goToScreen('approved'); return; }
    if (action === 'preview-generation') {
      if (reviewScreen !== 'outputs' || !reviewStats().complete || !approvedProducts().length || !selectedOutputTypes.size) return;
      const notice = document.getElementById('generation-notice');
      const styles = outputOptions.filter(option => selectedOutputTypes.has(option.id)).map(option => option.name).join(', ');
      notice.textContent = `${styles} selected for ${approvedProducts().length} approved ${approvedProducts().length === 1 ? 'product' : 'products'}. This is where generation would start; no files are created in this preview.`;
      notice.hidden = false;
      announce(notice.textContent);
      notice.scrollIntoView({ block: 'nearest' });
      return;
    }
    if (reviewScreen !== 'review') return;
    if (button.dataset.product) {
      selectedId = Number(button.dataset.product); showingRejected = false; confirmationId = null;
      render(); panel.querySelector(`[data-product="${selectedId}"]`).focus({ preventScroll: true }); return;
    }
    if (button.dataset.view !== undefined) { setProductView(Number(button.dataset.view)); return; }
    if (action === 'previous-image' || action === 'next-image') {
      setProductView(selectedProduct().view + (action === 'next-image' ? 1 : -1));
      return;
    }
    if (action === 'ask-cancel') openConfirmation();
    if (action === 'keep-product') closeConfirmation();
    if (action === 'confirm-cancel' && confirmationId === selectedId) makeDecision('cancelled');
    if (action === 'approve') makeDecision('approved');
    if (action === 'undo-decision') { selectedProduct().status = 'pending'; render(); document.getElementById('field-name').focus(); announce('Product is ready for review again.'); }
    if (action === 'show-rejected' || action === 'back-to-products') { showingRejected = action === 'show-rejected'; confirmationId = null; render(); panel.querySelector(showingRejected ? '[data-action="back-to-products"]' : `[data-product="${selectedId}"]`).focus({ preventScroll: true }); }
    if (action === 'finish-demo') {
      switchState('complete');
      document.getElementById('run-title').focus({ preventScroll: true });
    }
  });

  dialog.addEventListener('change', event => {
    const option = event.target.dataset.output;
    if (reviewScreen !== 'outputs' || !outputOptions.some(item => item.id === option)) return;
    if (event.target.checked) selectedOutputTypes.add(option);
    else selectedOutputTypes.delete(option);
    event.target.closest('.output-option').classList.toggle('selected', event.target.checked);
    document.getElementById('output-count').textContent = `${selectedOutputTypes.size} selected`;
    panel.querySelector('[data-action="preview-generation"]').disabled = selectedOutputTypes.size === 0;
    document.getElementById('generation-notice').hidden = true;
  });

  dialog.addEventListener('input', event => {
    const field = event.target.dataset.field;
    if (reviewScreen !== 'review' || !editableFields.has(field) || selectedProduct().status !== 'pending') return;
    selectedProduct()[field] = event.target.value;
    if (field === 'name') {
      const card = panel.querySelector(`[data-product="${selectedId}"]`);
      card.querySelector('.card-name').textContent = event.target.value || 'Untitled product';
      card.setAttribute('aria-label', `Review product ${selectedId}: ${event.target.value || 'Untitled product'}`);
      document.getElementById('hero-photo').alt = `${event.target.value || 'Untitled product'}, mock view ${selectedProduct().view + 1}`;
      panel.querySelectorAll('[data-view]').forEach(thumb => thumb.setAttribute('aria-label', `View image ${Number(thumb.dataset.view) + 1} of ${event.target.value || 'Untitled product'}`));
      event.target.removeAttribute('aria-invalid');
      document.getElementById('name-error').hidden = true;
    }
  });
  dialog.addEventListener('submit', event => event.preventDefault());
  dialog.addEventListener('cancel', event => {
    event.preventDefault();
    if (confirmationId !== null) closeConfirmation();
    else { dialog.close(); document.getElementById('open-review').focus(); }
  });
  dialog.addEventListener('keydown', event => {
    if (confirmationId === null || event.key !== 'Tab') return;
    const choices = [...panel.querySelectorAll('.confirmation button')];
    event.preventDefault();
    const current = choices.indexOf(document.activeElement);
    const next = (current + (event.shiftKey ? -1 : 1) + choices.length) % choices.length;
    choices[next].focus();
  });
  document.getElementById('open-review').addEventListener('click', () => {
    dialog.showModal();
    document.getElementById('run-title').focus({ preventScroll: true });
    if (mode === 'loading' && !loadingTimer) startLoading();
  });
  document.getElementById('replay-opening').addEventListener('click', () => {
    panel.style.animation = 'none';
    requestAnimationFrame(() => requestAnimationFrame(() => { panel.style.animation = ''; }));
  });
  render();
  dialog.showModal();
  document.getElementById('run-title').focus({ preventScroll: true });
  if (mode === 'loading') startLoading();
  else if (mode === 'cancel') openConfirmation();
})();
