'use client';

import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
import { OUTPUT_CATEGORIES, getOutputRecipes } from './output-recipes';
import './output-selection.css';

export type OutputProduct = { id: string; name: string; category: string | null; image_url: string | null };

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

export default function OutputSelection({ products, onBack, selection, onSelectionChange }: Props) {
  const [activeProductId, setActiveProductId] = useState(products[0]?.id ?? '');
  const [reviewOpen, setReviewOpen] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const reviewDialog = useRef<HTMLDialogElement>(null);
  const reviewHeading = useRef<HTMLHeadingElement>(null);
  const reviewButton = useRef<HTMLButtonElement>(null);
  const activeProduct = products.find(product => product.id === activeProductId) ?? products[0];
  const activeCategory = activeProduct?.category?.trim().toLowerCase();
  const recipesByProduct = new Map(products.map(product => [product.id, getOutputRecipes(product.category)]));
  const activeRecipes = activeProduct ? recipesByProduct.get(activeProduct.id) ?? [] : [];
  useEffect(() => { heading.current?.focus({ preventScroll: true }); }, []);
  const selectedFor = (productId: string) => {
    const recipeIds = new Set((recipesByProduct.get(productId) ?? []).map(recipe => recipe.id));
    return [...new Set(selection[productId] ?? [])].filter(id => recipeIds.has(id));
  };
  const selectedIds = new Set(activeProduct ? selectedFor(activeProduct.id) : []);
  const missingProducts = products.filter(product => selectedFor(product.id).length === 0);
  const total = products.reduce((count, product) => count + selectedFor(product.id).length, 0);
  const ready = products.length > 0 && missingProducts.length === 0;

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

  function toggleRecipe(recipeId: string) {
    if (!activeProduct || !activeRecipes.some(recipe => recipe.id === recipeId)) return;
    const next = new Set(selectedFor(activeProduct.id));
    if (next.has(recipeId)) next.delete(recipeId);
    else next.add(recipeId);
    onSelectionChange({ ...selection, [activeProduct.id]: [...next] });
    setReviewOpen(false);
  }

  return <section className="pf-output-selection" aria-labelledby="output-selection-title">
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
          return <button className="pf-output-product" type="button" key={product.id} aria-pressed={activeProduct.id === product.id} onClick={() => chooseProduct(product.id)}>
            <ProductImage product={product}/>
            <span className="pf-output-product-copy"><b>{product.name}</b><small>{count} {count === 1 ? 'output' : 'outputs'} selected</small></span>
            <span className="pf-output-product-count" aria-hidden="true">{count}</span>
          </button>;
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
            <p id="output-selection-total">{total} {total === 1 ? 'output' : 'outputs'} selected</p>
            <div className="pf-output-summary-actions"><button className="pf-output-summary-back" type="button" onClick={() => setReviewOpen(false)}>Back to selection</button><button className="pf-output-summary-continue" type="button" disabled>Continue <span aria-hidden="true">→</span></button></div>
          </footer>
        </div>
      </dialog>

      <div className="pf-output-current"><p>Showing templates for {activeCategory ? <strong>{activeCategory}</strong> : 'this product'}</p><span>Images are output examples.</span></div>
      <div className="pf-output-catalogue" role="group" aria-label={`Output choices for ${activeProduct.name}`}>
        {OUTPUT_CATEGORIES.map(category => <section className="pf-output-category" key={category} aria-labelledby={`output-category-${category}`}>
          <div className="pf-output-category-heading"><h2 id={`output-category-${category}`}>{category}</h2><span>{activeRecipes.filter(recipe => recipe.category === category).length} templates</span></div>
          <div className="pf-output-grid">{activeRecipes.filter(recipe => recipe.category === category).map((recipe, index) => <button className={`pf-output-card${recipe.exampleImage.startsWith('/') ? ' pf-output-card-portrait' : ''}`} type="button" key={recipe.id} aria-label={recipe.name} aria-pressed={selectedIds.has(recipe.id)} aria-describedby={`output-description-${recipe.id}`} onClick={() => toggleRecipe(recipe.id)}>
            <Image src={recipe.exampleImage} alt="" fill sizes="(max-width: 420px) 100vw, (max-width: 760px) 50vw, (max-width: 1100px) 30vw, 25vw" unoptimized={!recipe.exampleImage.startsWith('/')}/>
            <span className="pf-output-example">Example</span>
            {selectedIds.has(recipe.id) && <span className="pf-output-selected"><span aria-hidden="true">✓</span> Selected</span>}
            <span className="pf-output-card-copy"><b>{String(index + 1).padStart(2, '0')} · {recipe.name}</b><span id={`output-description-${recipe.id}`}>{recipe.description}</span></span>
          </button>)}</div>
        </section>)}
      </div>
    </>}
  </section>;
}
