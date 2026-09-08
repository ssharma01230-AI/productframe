'use client';

import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { useEffect, useRef, useState, type ChangeEvent } from 'react';
import { OUTPUT_CATEGORIES, getOutputRecipes, type OutputRecipe } from './output-recipes';
import StudioIcon from './StudioIcon';
import type { GenerationPresentation, GenerationRunRequest, GenerationRunResponse } from './generation-types';
import './output-selection.css';

type MediaEvidence = { views?: string[]; evidence?: string[] };
export type OutputProduct = { id: string; name: string; category: string | null; product_family?: string | null; image_url: string | null; media_evidence?: MediaEvidence[] };

const generationSliceEnabled = process.env.NEXT_PUBLIC_ENABLE_GENERATION_SLICE !== 'false';

type Props = {
  products: OutputProduct[];
  onBack: () => void;
  selection: Record<string, string[]>;
  onSelectionChange: (selection: Record<string, string[]>) => void;
};

function ProductImage({ product }: { product: OutputProduct }) {
  return <span className="pf-output-product-image" aria-hidden="true">
    {product.image_url ? <Image src={product.image_url} alt="" fill sizes="40px" unoptimized /> : <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m4 18 5-5 3 3 4-6 4 7"/></svg>}
  </span>;
}

function renderRecipeImage(recipe: OutputRecipe) {
  const isLocalImage = recipe.exampleImage.startsWith('/');
  const hoverImage = recipe.hoverExampleImage;
  return <span className={`pf-output-card-media${hoverImage ? ' pf-output-card-media-switch' : ''}`} aria-hidden="true">
    <Image className="pf-output-card-image pf-output-card-image-primary" src={recipe.exampleImage} alt="" fill sizes="(max-width: 420px) 100vw, (max-width: 760px) 50vw, (max-width: 1100px) 30vw, 25vw" unoptimized={!isLocalImage}/>
    {hoverImage && <Image className="pf-output-card-image pf-output-card-image-hover" src={hoverImage} alt="" fill sizes="(max-width: 420px) 100vw, (max-width: 760px) 50vw, (max-width: 1100px) 30vw, 25vw" unoptimized={!hoverImage.startsWith('/')}/>}
  </span>;
}

export default function OutputSelection({ products, onBack, selection, onSelectionChange }: Props) {
  const [activeProductId, setActiveProductId] = useState(products[0]?.id ?? '');
  const [presentationByProduct, setPresentationByProduct] = useState<Record<string, GenerationPresentation>>(() => Object.fromEntries(products.map(product => [product.id, 'unisex'])));
  const [reviewOpen, setReviewOpen] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const reviewDialog = useRef<HTMLDialogElement>(null);
  const reviewHeading = useRef<HTMLHeadingElement>(null);
  const reviewButton = useRef<HTMLButtonElement>(null);
  const uploadInput = useRef<HTMLInputElement>(null);
  const uploadDialog = useRef<HTMLDialogElement>(null);
  const router = useRouter();
  const { getToken } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [pendingEvidenceRecipe, setPendingEvidenceRecipe] = useState<string | null>(null);
  const [evidenceOverrides, setEvidenceOverrides] = useState<Record<string, string[]>>({});
  const [submitting, setSubmitting] = useState(false);
  const [generationMessage, setGenerationMessage] = useState('');
  const [submissionKey, setSubmissionKey] = useState<string | null>(null);
  const activeProduct = products.find(product => product.id === activeProductId) ?? products[0];
  const activeCategory = activeProduct?.category?.trim().toLowerCase();
  const recipesByProduct = new Map(products.map(product => [product.id, getOutputRecipes(product.category, product.product_family)]));
  const activeRecipes = activeProduct ? recipesByProduct.get(activeProduct.id) ?? [] : [];
  const availableEvidence = new Set((activeProduct?.media_evidence ?? []).flatMap(item => [...(item.views ?? []), ...(item.evidence ?? [])]));
  const requiresEvidence = (recipe: { id: string }) => {
    if (!generationSliceEnabled) return false;
    const required = recipeEvidence(recipe.id, activeProduct?.category, activeProduct?.product_family);
    return required.length > 0 && !required.every(item => availableEvidence.has(item));
  };
  const hasEvidence = (recipe: { id: string }) => {
    // The rollout flag restores the pre-readiness selection behaviour as well
    // as disabling submission, which keeps rollback genuinely reversible.
    if (!generationSliceEnabled) return true;
    const required = recipeEvidence(recipe.id, activeProduct?.category, activeProduct?.product_family);
    // The user may explicitly continue with a best-effort output when the
    // recommended supporting view is unavailable.
    if (activeProduct && evidenceOverrides[activeProduct.id]?.includes(recipe.id)) return true;
    // Socks intentionally has no additional media gate.
    return required.length === 0 || required.every(item => availableEvidence.has(item));
  };
  useEffect(() => { heading.current?.focus({ preventScroll: true }); }, []);
  const selectedFor = (productId: string) => {
    const recipeIds = new Set((recipesByProduct.get(productId) ?? []).map(recipe => recipe.id));
    return [...new Set(selection[productId] ?? [])].filter(id => recipeIds.has(id));
  };
  const selectedIds = new Set(activeProduct ? selectedFor(activeProduct.id) : []);
  const missingProducts = products.filter(product => selectedFor(product.id).length === 0);
  const total = products.reduce((count, product) => count + selectedFor(product.id).length, 0);
  const ready = products.length > 0 && missingProducts.length === 0;
  const generationSelections = products.flatMap(product => selectedFor(product.id).map(template_id => ({
    product_id: product.id,
    template_id,
    channel: 'ecommerce' as const,
    presentation: presentationByProduct[product.id] ?? 'unisex',
  })));
  const canSubmitGeneration = generationSliceEnabled && ready && generationSelections.length > 0;

  useEffect(() => {
    const dialog = reviewDialog.current;
    if (!dialog || !reviewOpen || !ready) return;
    const previousOverflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = 'hidden';
    reviewHeading.current?.focus({ preventScroll: true });
    return () => {
      dialog.close();
      document.body.style.overflow = previousOverflow;
      if (reviewButton.current?.isConnected) reviewButton.current.focus({ preventScroll: true });
    };
  }, [reviewOpen, ready]);

  function chooseProduct(productId: string) {
    setActiveProductId(productId);
    setReviewOpen(false);
  }

  function requestEvidence(recipe: { id: string }) {
    if (uploading) return;
    const missing = recipeEvidence(recipe.id, activeProduct?.category, activeProduct?.product_family)[0]?.replaceAll('_', ' ') ?? 'product';
    setUploadMessage(`Add a clear image showing the missing ${missing}`);
    setPendingEvidenceRecipe(recipe.id);
    setUploadOpen(true);
  }

  function continueWithoutEvidence() {
    if (!activeProduct || !pendingEvidenceRecipe) return;
    const productId = activeProduct.id;
    const recipeId = pendingEvidenceRecipe;
    setEvidenceOverrides(previous => ({ ...previous, [productId]: [...new Set([...(previous[productId] ?? []), recipeId])] }));
    setUploadOpen(false);
    setPendingEvidenceRecipe(null);
    toggleRecipe(recipeId);
    setUploadMessage('Continuing without the recommended source image. The output may be less accurate.');
  }

  async function uploadEvidence(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = '';
    if (!files.length || !activeProduct) return;
    setUploading(true);
    setUploadMessage(`Uploading and analysing ${files.length} source ${files.length === 1 ? 'image' : 'images'}…`);
    try {
      const token = await getToken();
      if (!token) throw new Error('Sign in again to add source evidence.');
      const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
      const headers = { Authorization: `Bearer ${token}` };
      for (const file of files) {
        const upload = await fetch(`${base}/products/${encodeURIComponent(activeProduct.id)}/source-assets/upload-url`, { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ filename: file.name, content_type: file.type }) });
        if (!upload.ok) throw new Error('A source image could not be prepared for upload.');
        const details = await upload.json() as { asset_id: string; upload_url: string };
        const stored = await fetch(details.upload_url, { method: 'PUT', headers: { 'Content-Type': file.type }, body: file });
        if (!stored.ok) throw new Error('A source image upload failed.');
        const queued = await fetch(`${base}/products/${encodeURIComponent(activeProduct.id)}/source-assets/${encodeURIComponent(details.asset_id)}/evidence`, { method: 'POST', headers });
        if (!queued.ok) throw new Error('A source image could not be queued for analysis.');
      }
      setUploadMessage(`${files.length} source ${files.length === 1 ? 'image' : 'images'} queued for evidence analysis.`);
      setUploadOpen(false);
      router.refresh();
    } catch (cause) {
      setUploadMessage(cause instanceof Error ? cause.message : 'The evidence upload failed.');
    } finally { setUploading(false); }
  }

  useEffect(() => {
    const dialog = uploadDialog.current;
    if (!dialog || !uploadOpen) return;
    if (!dialog.open) dialog.showModal();
    return () => { if (dialog.open) dialog.close(); };
  }, [uploadOpen]);

  async function startGeneration() {
    if (!canSubmitGeneration || submitting) return;
    const key = submissionKey ?? (typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);
    setSubmissionKey(key);
    setSubmitting(true);
    setGenerationMessage('Starting generation…');
    try {
      const token = await getToken();
      if (!token) throw new Error('Sign in again to start generation.');
      const payload: GenerationRunRequest = { selections: generationSelections };
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/generation-runs`, { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'Idempotency-Key': key }, body: JSON.stringify({ ...payload, idempotency_key: key }) });
      if (!response.ok) {
        const detail = await response.json().catch(() => null) as { detail?: string } | null;
        throw new Error(detail?.detail || 'Generation could not be started.');
      }
      const result = await response.json() as GenerationRunResponse;
      router.push(`/studio?view=create&step=generation&run=${encodeURIComponent(result.run_id)}`);
    } catch (cause) {
      setGenerationMessage(cause instanceof Error ? cause.message : 'Generation could not be started.');
    } finally { setSubmitting(false); }
  }

  function toggleRecipe(recipeId: string) {
    if (!activeProduct || !activeRecipes.some(recipe => recipe.id === recipeId)) return;
    const next = new Set(selectedFor(activeProduct.id));
    if (next.has(recipeId)) next.delete(recipeId);
    else next.add(recipeId);
    onSelectionChange({ ...selection, [activeProduct.id]: [...next] });
    setSubmissionKey(null);
    setGenerationMessage('');
    setReviewOpen(false);
  }

  return <section className="pf-output-selection" aria-labelledby="output-selection-title">
    {uploadMessage && !uploadOpen && <p className="pf-output-evidence-message" role="status">{uploadMessage}</p>}
    <dialog ref={uploadDialog} className="pf-output-evidence-dialog" aria-labelledby="pf-evidence-upload-title" onCancel={event => { event.preventDefault(); if (!uploading) setUploadOpen(false); }} onClick={event => { if (event.target === event.currentTarget && !uploading) setUploadOpen(false); }}>
      <div className="pf-output-evidence-dialog-content">
        <h2 id="pf-evidence-upload-title">Upload another product image</h2>
        <p className="pf-output-evidence-hint"><StudioIcon name="garment"/><span>{uploadMessage || 'Add a clear image showing the product detail required for this output.'}</span></p>
        <ul className="pf-output-evidence-tips"><li>Show the full product clearly</li><li>Use even, natural lighting</li><li>Keep the background simple</li></ul>
        <input ref={uploadInput} className="pf-output-evidence-input" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={uploadEvidence} aria-label="Choose source evidence images" />
        <label className="pf-output-evidence-picker"> <img src="/documents/upload-icon-green.svg" alt="" /> <span>{uploading ? 'Uploading…' : 'Choose images'}</span><small>JPG, PNG or WEBP · Multiple allowed</small><input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={uploadEvidence} disabled={uploading} /></label>
        <div className="pf-output-evidence-actions"><div className="pf-output-evidence-continue-wrap"><button type="button" className="pf-output-evidence-continue" onClick={continueWithoutEvidence} disabled={uploading}>Continue without reference</button><small>We’ll generate using the available product references. The result may be less accurate.</small></div><button type="button" className="pf-output-evidence-cancel" onClick={() => { setUploadOpen(false); setPendingEvidenceRecipe(null); }} disabled={uploading}>Cancel</button></div>
      </div>
    </dialog>
    <button className="pf-output-back" type="button" onClick={onBack}><span aria-hidden="true">←</span> Back to products</button>
    <header className="pf-output-heading">
      <p className="pf-output-eyebrow">CONTENT CATALOGUE</p>
      <h1 id="output-selection-title" tabIndex={-1} ref={heading}>Choose the moments worth making.</h1>
      <p>Build a considered set of visuals for every place your product needs to live.</p>
    </header>

    {!products.length ? <div className="pf-output-empty">
      <h2>Choose a product to get started.</h2>
      <p>Go back to your products and select the ones you want to create content for.</p>
    </div> : <>
      <div className="pf-output-products" role="group" aria-label="Choose a product">
        {products.map(product => {
          const count = selectedFor(product.id).length;
          return <div className="pf-output-product-wrap" key={product.id}>
            <button className="pf-output-product" type="button" aria-pressed={activeProduct.id === product.id} onClick={() => chooseProduct(product.id)}>
              <ProductImage product={product}/>
              <span className="pf-output-product-copy"><b>{product.name}</b><small>{count} {count === 1 ? 'output' : 'outputs'} selected</small></span>
              <span className="pf-output-product-count" aria-hidden="true">{count}</span>
            </button>
            <label className="pf-output-presentation"><StudioIcon name="user"/><span>Gender</span><select value={presentationByProduct[product.id] ?? 'unisex'} aria-label={`Gender for ${product.name}`} onChange={event => setPresentationByProduct(previous => ({ ...previous, [product.id]: event.target.value as GenerationPresentation }))}>
              <option value="male">Male</option><option value="female">Female</option><option value="unisex">Unisex</option>
            </select></label>
          </div>;
        })}
      </div>

      <div className="pf-output-selection-actions">
        <span className="pf-output-selection-count" role="status"><b>{total}</b> {total === 1 ? 'output' : 'outputs'} selected across {products.length} {products.length === 1 ? 'product' : 'products'}</span>
        <button className="pf-output-review-button" ref={reviewButton} type="button" disabled={!ready} aria-haspopup="dialog" aria-expanded={reviewOpen && ready} aria-controls="output-selection-summary" onClick={() => setReviewOpen(true)}>Review selection <span aria-hidden="true">→</span></button>
      </div>

      <dialog className="pf-output-summary" id="output-selection-summary" ref={reviewDialog} aria-labelledby="output-summary-title" aria-describedby="output-summary-description" onCancel={event => { event.preventDefault(); setReviewOpen(false); }} onClose={event => { if (!event.currentTarget.open) setReviewOpen(false); }} onClick={event => {
        if (event.target !== event.currentTarget) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) setReviewOpen(false);
      }}>
        <div className="pf-output-summary-content">
          <header className="pf-output-summary-heading">
            <div><p className="pf-output-eyebrow">YOUR SELECTION</p><h2 id="output-summary-title" tabIndex={-1} ref={reviewHeading}>Your outputs, organised by product.</h2><p id="output-summary-description">{total} {total === 1 ? 'output' : 'outputs'} selected across {products.length} {products.length === 1 ? 'product' : 'products'}</p></div>
            <button className="pf-output-summary-close" type="button" aria-label="Close selection review" onClick={() => setReviewOpen(false)}><span aria-hidden="true">×</span></button>
          </header>
          <div className="pf-output-summary-groups">{products.map(product => {
              const ids = new Set(selectedFor(product.id));
              const recipes = (recipesByProduct.get(product.id) ?? []).filter(recipe => ids.has(recipe.id));
              return <section className="pf-output-summary-group" key={product.id} aria-label={product.name}>
                <div className="pf-output-summary-product"><h3>{product.name}</h3><span>{recipes.length} {recipes.length === 1 ? 'output' : 'outputs'}</span></div>
                <ul>{recipes.map(recipe => <li key={recipe.id}><span className={`pf-output-summary-example${recipe.exampleImage.startsWith('/') ? ' pf-output-summary-example-portrait' : ''}`}><Image src={recipe.exampleImage} alt="" fill sizes="52px" unoptimized={!recipe.exampleImage.startsWith('/')} /></span><div><b>{recipe.name}</b><span>{recipe.category}</span></div></li>)}</ul>
              </section>;
            })}</div>
          <footer className="pf-output-summary-footer">
              <p id="output-selection-total">{generationMessage || `${total} ${total === 1 ? 'output' : 'outputs'} selected`}</p>
              <div className="pf-output-summary-actions"><button className="pf-output-summary-back" type="button" onClick={() => setReviewOpen(false)}>Back to selection</button><button className="pf-output-summary-continue" type="button" disabled={!canSubmitGeneration || submitting} onClick={startGeneration}>{submitting ? 'Starting…' : canSubmitGeneration ? 'Continue' : generationSliceEnabled ? 'Select one product and output' : 'Generation unavailable'} <span aria-hidden="true">→</span></button></div>
            </footer>
        </div>
      </dialog>

      <div className="pf-output-current"><p>Showing templates for {activeCategory ? <strong>{formatCategory(activeCategory)}</strong> : 'this product'}</p><span>Images are output examples.</span></div>
      <div className="pf-output-catalogue" role="group" aria-label={`Output choices for ${activeProduct.name}`}>
        {OUTPUT_CATEGORIES.map(category => <section className="pf-output-category" key={category} aria-labelledby={`output-category-${category}`}>
          <div className="pf-output-category-heading"><h2 id={`output-category-${category}`}>{category}</h2><span>{activeRecipes.filter(recipe => recipe.category === category).length} templates</span></div>
          <div className="pf-output-grid">{activeRecipes.filter(recipe => recipe.category === category).map((recipe, index) => <button className={`pf-output-card${recipe.exampleImage.startsWith('/') ? ' pf-output-card-portrait' : ''}${recipe.hoverExampleImage ? ' pf-output-card-has-hover-image' : ''}`} type="button" key={recipe.id} aria-label={recipe.name} aria-pressed={selectedIds.has(recipe.id)} aria-describedby={`output-description-${recipe.id}`} onClick={() => hasEvidence(recipe) ? toggleRecipe(recipe.id) : requestEvidence(recipe)}>
            {renderRecipeImage(recipe)}
            {requiresEvidence(recipe) ? <span className="pf-output-example pf-output-needs-evidence"><b aria-hidden="true">!</b><span>Additional angle required</span></span> : <span className="pf-output-example">Example</span>}
            {selectedIds.has(recipe.id) && <span className="pf-output-selected"><span aria-hidden="true">✓</span> Selected</span>}
            <span className={`pf-output-card-product-thumb${requiresEvidence(recipe) ? ' is-missing' : ''}`} aria-hidden="true">{!requiresEvidence(recipe) && activeProduct.image_url ? <Image src={activeProduct.image_url} alt="" fill sizes="52px" unoptimized={!activeProduct.image_url.startsWith('/')}/> : !requiresEvidence(recipe) ? <span>✓</span> : <img src="/documents/upload-icon-green.svg" alt=""/>}</span>
            <span className="pf-output-card-copy"><b>{String(index + 1).padStart(2, '0')} · {recipe.name}</b><span id={`output-description-${recipe.id}`}>{recipe.description}</span></span>
          </button>)}</div>
        </section>)}
      </div>
    </>}
  </section>;
}

function formatCategory(value: string) { return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase(); }

function recipeEvidence(id: string, category?: string | null, family?: string | null): string[] {
  const normalized = category?.trim().toLowerCase();
  if (normalized === 'socks') return [];
  if (normalized === 'underwear' && family?.trim().toLowerCase() !== 'lower_body_underwear') return [];
  if (normalized === 'footwear') {
    if (id.includes('sole')) return ['sole_or_underside'];
    if (id.includes('top')) return ['top_view'];
    if (id.includes('rear')) return ['rear_view'];
    if (id.includes('inner') || id.includes('outer') || id.includes('three-quarter') || id.includes('feet')) return ['top_view'];
    return ['top_view'];
  }
  if (normalized === 'outerwear' || normalized === 'bottoms' || normalized === 'tops' || normalized === 'underwear') {
    return id.includes('back') || id.includes('rear') || id.includes('over-the-shoulder') ? ['rear_view'] : ['front_view'];
  }
  return [];
}
