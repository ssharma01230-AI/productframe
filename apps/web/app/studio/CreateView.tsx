'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import GenerationGallery from './GenerationGallery';
import OutputSelection, { type OutputProduct } from './OutputSelection';
import StudioIcon from './StudioIcon';
import './create-view.css';

function formatCategory(value: string) { return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase(); }

export default function CreateView({ products, onUpload, initialSelectedIds = [], initialOutputStep = false, generationRunId }: { products: OutputProduct[]; onUpload: () => void; initialSelectedIds?: string[]; initialOutputStep?: boolean; generationRunId?: string }) {
  const router = useRouter();
  const [selectedIds, setSelectedIds] = useState<string[]>(() => [...new Set(initialSelectedIds)]);
  const [outputSelection, setOutputSelection] = useState<Record<string, string[]>>({});
  const selectionKey = JSON.stringify(initialSelectedIds);
  const heading = useRef<HTMLHeadingElement>(null);
  const catalogueHeading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { setSelectedIds([...new Set(JSON.parse(selectionKey) as string[])]); }, [selectionKey]);
  useEffect(() => { if (!initialOutputStep) heading.current?.focus({ preventScroll: true }); }, [initialOutputStep]);
  const selectedProducts = products.filter(product => selectedIds.includes(product.id));
  const selectedCount = selectedProducts.length;
  const selectionLabel = `${selectedCount} ${selectedCount === 1 ? 'product' : 'products'} selected`;
  const selectionUrl = (outputs: boolean) => {
    const params = new URLSearchParams({ view:'create' });
    if (outputs) params.set('step', 'outputs');
    selectedProducts.forEach(product => params.append('product', product.id));
    return '/studio?' + params.toString();
  };
  const toggleProduct = (id: string) => {
    setSelectedIds(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id]);
  };
  const chooseOutputs = () => {
    if (!selectedCount) return;
    // Keep browser Back on the same product selection without a server round-trip.
    window.history.replaceState(null, '', selectionUrl(false));
    router.push(selectionUrl(true));
  };

  if (generationRunId) return <GenerationGallery runId={generationRunId}/>;
  if (initialOutputStep) return <OutputSelection products={selectedProducts} onBack={() => router.push(selectionUrl(false))} selection={outputSelection} onSelectionChange={setOutputSelection} />;

  return <section className="pf-create-view" aria-labelledby="create-title">
    <div className="pf-create-intro">
      <p className="pf-create-eyebrow">CREATE PRODUCT CONTENT</p>
      <h1 id="create-title" tabIndex={-1} ref={heading}>What are you creating for?</h1>
      <p className="pf-create-subtitle">Start with new product images, or choose something already in your catalogue.</p>
    </div>

    <div className="pf-create-paths">
      <section className="pf-create-path" aria-labelledby="create-upload-title">
        <div className="pf-create-path-heading">
          <div>
            <h2 id="create-upload-title">Upload a product</h2>
            <p>Add one or more product images</p>
          </div>
        </div>
        <button className="pf-create-upload-card" type="button" onClick={onUpload} aria-haspopup="dialog">
          <div className="pf-create-upload-drop">
            <div>
              <div className="pf-create-plus" aria-hidden="true">＋</div>
              <b>Upload product images</b>
              <span>or click to browse</span>
            </div>
          </div>
          <div className="pf-create-upload-examples" aria-hidden="true">
            <img src="https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500&q=85" alt=""/>
            <img src="https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=300&q=80" alt=""/>
            <img src="https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&q=80" alt=""/>
          </div>
          <div className="pf-create-upload-foot">
            <span>JPG · PNG · WEBP <em>✦ Clear, evenly lit photos on a simple background work best</em></span>
            <strong>Up to 50 images · Multiple angles welcome →</strong>
          </div>
        </button>
      </section>

      <section className="pf-create-path" aria-labelledby="create-catalogue-title">
        <div className="pf-create-path-heading">
          <div>
            <h2 id="create-catalogue-title" tabIndex={-1} ref={catalogueHeading}>Select from your catalogue</h2>
            <p>Select one or more products to create outputs for</p>
          </div>
          <span className="pf-create-path-count">{products.length} {products.length === 1 ? 'product' : 'products'}</span>
        </div>
        <div className="pf-create-catalogue-grid">
          {products.length ? products.map(product => <button className="pf-create-catalogue-card" key={product.id} type="button" aria-pressed={selectedIds.includes(product.id)} aria-label={product.name} onClick={() => toggleProduct(product.id)}>
            <div className="pf-create-product-photo">
              {product.image_url ? <img src={product.image_url} alt=""/> : <span className="pf-create-no-image">No image</span>}
              <span className="pf-create-selection-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 4 4L19 6"/></svg></span>
            </div>
            <span className="pf-create-product-info">
              <b>{product.name}</b>
              <small>{selectedIds.includes(product.id) ? 'Selected for outputs' : (product.category ? formatCategory(product.category) : 'Product')}</small>
            </span>
          </button>) : <div className="pf-create-empty">Approved products will appear here after review.</div>}
        </div>
        <span className="pf-create-sr-only" role="status">{selectionLabel}</span>
        {selectedCount > 0 && <div className="pf-create-selection-actions">
          <div className="pf-create-selection-copy"><StudioIcon name="sparkle"/><span>{selectionLabel}</span></div>
          <div className="pf-create-selection-buttons">
            <button className="pf-create-clear-selection" type="button" onClick={() => { setSelectedIds([]); catalogueHeading.current?.focus({ preventScroll: true }); }}>Clear selection</button>
            <button className="pf-create-continue" type="button" onClick={chooseOutputs}>Choose outputs<StudioIcon name="arrow"/></button>
          </div>
        </div>}
      </section>
    </div>
  </section>;
}
