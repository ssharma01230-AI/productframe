'use client';

import { useAuth } from '@clerk/nextjs';
import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import Image from 'next/image';
import './run-review.css';
import { useRouter } from 'next/navigation';

type ImageResult = { id:string; image_number:number; filename:string|null; image_url:string|null; passed:boolean|null; product_number:number|null; rejection_reason:string|null; status:string };
type Product = { id:string; final_product_id:string|null; product_number:number; product_name:string; category:string; product_type:string; colours:string; materials:string; features:string[]; description:string; confidence:number; confirmation_status:string };
type Results = { id:string; status:string; total_images:number; processed_images:number; unique_product_count:number; progress?:{stage:string; message:string|null; completed:number; total:number; percent:number}; images:ImageResult[]; products:Product[] };
type Draft = Product;
type EditableField = 'product_name' | 'product_type' | 'colours' | 'materials' | 'features' | 'description';
const api = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export default function RunReview({ jobId, imageCount, initial }: { jobId:string; imageCount:number; initial:Results|null }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [results, setResults] = useState<Results|null>(initial);
  const [drafts, setDrafts] = useState<Draft[]>(isAnalysisFinished(initial?.status) ? initial?.products ?? [] : []);
  const [screen, setScreen] = useState<'review'|'summary'>('review');
  const [selected, setSelected] = useState(0);
  const [cancelTarget, setCancelTarget] = useState<number|null>(null);
  const [saving, setSaving] = useState<number|'all'|null>(null);
  const savingRef = useRef(false);
  const [editingDraft, setEditingDraft] = useState<Draft|null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    async function poll() {
      try {
        const token = await getToken();
        if (!active) return;
        if (!token) { setError('Your sign-in session has expired. Sign in again to check this analysis.'); return; }
        const response = await fetch(`${api}/analysis-jobs/${jobId}/results`, { headers:{ Authorization:`Bearer ${token}` }, cache:'no-store' });
        if (response.ok && active) {
          const next:Results = await response.json();
          if (!active) return;
          setResults(next);
          if (isAnalysisFinished(next.status)) setDrafts(current => current.length ? current : next.products);
          if (!isAnalysisFinished(next.status)) timer = window.setTimeout(poll, 1800);
        } else if (active) timer = window.setTimeout(poll, 2500);
      } catch { if (active) timer = window.setTimeout(poll, 2500); }
    }
    poll(); return () => { active = false; window.clearTimeout(timer); };
  }, [getToken, jobId]);

  const update = (number:number, key:keyof Draft, value:string|string[]) => {
    if (savingRef.current) return;
    if (editingDraft?.product_number === number) setEditingDraft(item => item ? {...item, [key]:value} : item);
    else setDrafts(items => items.map(item => item.product_number === number ? {...item, [key]:value} : item));
  };
  async function decide(product:Draft, status:'approved'|'cancelled') {
    const editingApproved = product.confirmation_status === 'approved' && editingDraft?.product_number === product.product_number && status === 'approved';
    const allowed = status === 'cancelled' ? canCancelProduct(product) && editingDraft === null : isPending(product) || editingApproved;
    if (savingRef.current || !allowed) return;
    if (status === 'cancelled') { setCancelTarget(null); }
    const savedProduct = {...product, ...approvalFields(product), confirmation_status:status};
    const validationError = status === 'approved' ? approvalError(savedProduct) : null;
    if (validationError) { setError(validationError); return; }
    savingRef.current = true;
    setSaving(product.product_number); setError('');
    try {
      const token = await getToken();
      if (!token) { setError('Your sign-in session has expired. Sign in again before saving your changes.'); return; }
      const {product_name, product_type, colours, materials, features, description} = savedProduct;
      const response = await fetch(`${api}/analysis-jobs/${jobId}/products/${product.product_number}`, { method:'PATCH', headers:{ Authorization:`Bearer ${token}`, 'Content-Type':'application/json' }, body:JSON.stringify({ product_name, product_type, colours, materials, features, description, status }) });
      if (!response.ok) { setError(editingApproved ? 'We couldn’t save your changes. Your edits are still here—please try again.' : 'We could not save that decision. Please try again.'); return; }
      setDrafts(items => items.map(item => item.product_number === product.product_number ? savedProduct : item));
      if (editingApproved) setEditingDraft(null);
    } catch {
      setError(editingApproved ? 'We couldn’t save your changes. Your edits are still here—please try again.' : 'We could not save that decision. Please try again.');
    } finally { savingRef.current = false; setSaving(null); }
  }
  async function approveAll() {
    if (savingRef.current || editingDraft || cancelTarget !== null || !['awaiting_confirmation', 'completed'].includes(results?.status ?? '')) return;
    const pending = drafts.filter(isPending);
    if (!pending.length) return;
    const products = pending.map(product => ({ product_number:product.product_number, ...approvalFields(product) }));
    for (const product of products) {
      const validationError = approvalError(product);
      if (validationError) {
        setSelected(drafts.findIndex(item => item.product_number === product.product_number));
        setError(`Product ${product.product_number}: ${validationError}`);
        return;
      }
    }
    savingRef.current = true;
    setSaving('all'); setError('');
    try {
      const token = await getToken();
      if (!token) { setError('Your sign-in session has expired. Sign in again before approving your products.'); return; }
      const response = await fetch(`${api}/analysis-jobs/${jobId}/products/approve-all`, { method:'POST', headers:{ Authorization:`Bearer ${token}`, 'Content-Type':'application/json' }, body:JSON.stringify({ products }) });
      if (!response.ok) throw new Error('Approval failed');
      const saved: { products: Product[] } = await response.json();
      const byNumber = new Map(saved.products.map(product => [product.product_number, product]));
      if (products.some(product => !byNumber.has(product.product_number))) throw new Error('Incomplete approval response');
      setDrafts(items => items.map(item => byNumber.get(item.product_number) ?? item));
    } catch {
      setError('We couldn’t confirm all approvals. Your edits are still here. Please try again.');
    } finally { savingRef.current = false; setSaving(null); }
  }
  const images = results?.images ?? [];
  const rejected = images.filter(image => image.passed === false);
  const total = results?.total_images ?? imageCount;
  const passed = results ? images.filter(image => image.passed === true).length : 0;
  const reviewedProducts = drafts.filter(item => ['approved','rejected','cancelled'].includes(item.confirmation_status));
  const cancelled = drafts.filter(item => item.confirmation_status === 'cancelled').length;
  const approved = drafts.filter(item => item.confirmation_status === 'approved');
  const pendingCount = drafts.filter(isPending).length;
  const eligible = drafts.length - cancelled;
  const complete = drafts.length > 0 && reviewedProducts.length === drafts.length;
  const showReviewFooter = drafts.length > 0 && (results?.status === 'awaiting_confirmation' || results?.status === 'completed');
  const allCancelled = drafts.length > 0 && cancelled === drafts.length;
  const current = drafts[selected] ?? null;
  const currentImages = current ? images.filter(image => image.product_number === current.product_number && image.passed === true) : [];
  const [imageIndex, setImageIndex] = useState(0);
  useEffect(() => { setImageIndex(0); }, [selected]);
  const counts = useMemo(() => ({ processed:results?.processed_images ?? 0, products:results?.unique_product_count ?? drafts.length }), [results, drafts.length]);

  const analysisComplete = results?.status === 'awaiting_confirmation' || results?.status === 'completed';
  const analysisFailed = results?.status === 'failed';
  const canCloseReview = analysisComplete || results?.status === 'failed';
  const reviewedCount = reviewedProducts.filter(item => item.confirmation_status !== 'cancelled').length;
  const reviewLabel = allCancelled ? 'All products cancelled' : reviewedCount + ' of ' + eligible + ' products reviewed';
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => { headingRef.current?.focus({ preventScroll: true }); }, [screen]);
  const selectProduct = (index: number) => {
    if (editingDraft || savingRef.current) return;
    setSelected(index);
    setImageIndex(0);
    setCancelTarget(null);
    setError('');
  };
  const summaryDescription = approved.length
    ? approved.length + ' approved ' + (approved.length === 1 ? 'product. A final look before you bring it to life.' : 'products. A final look before you bring them to life.')
    : 'Head back to review to choose the pieces you’d like to work with.';

  return (
    <div className="pf-overlay">
      <section className="pf-modal" role="dialog" aria-modal="true" aria-labelledby="pf-title" aria-describedby="pf-description">
        <header className="pf-heading">
          <div className="pf-heading-line">
            <h2 id="pf-title" tabIndex={-1} ref={headingRef}>
              {screen === 'summary' ? (approved.length ? 'Your edit is ready' : 'No products approved') : analysisComplete ? counts.products + (counts.products === 1 ? ' product identified' : ' products identified') : analysisFailed ? 'Analysis stopped' : 'Reviewing your products'}
            </h2>
            <div className="pf-heading-controls">
              {screen !== 'summary' && !analysisComplete && !analysisFailed && <span className="pf-state-badge processing">
                <span className="pf-dot" />
                Processing
              </span>}
              {canCloseReview && <button type="button" className="pf-icon-button" aria-label="Close run review" disabled={editingDraft !== null || saving !== null} title={editingDraft ? 'Save or discard your changes first' : undefined} onClick={() => router.push('/studio')}><Icon name="close" /></button>}
            </div>
          </div>
          <p className="pf-description" id="pf-description">
            {screen === 'summary' ? summaryDescription : analysisComplete ? 'Confirm we’ve got it right.' : analysisFailed ? 'We couldn’t finish preparing these products. You can close this window and try again.' : 'We’ll check your images, group products and get the details ready.'}
          </p>
        </header>

        {screen === 'summary' ? (
          <Summary approved={approved} images={images} onBack={() => setScreen('review')} onProduce={() => router.push('/products?run_id=' + encodeURIComponent(jobId))} />
        ) : (
          <>
            <section className="pf-metrics" aria-label="Run summary">
              <Metric value={total} label="images uploaded" icon="image" />
              <Metric value={results ? passed : '—'} label="passed validation" icon="shield" />
              <Metric value={results ? counts.products : '—'} label="unique products" icon="layers" />
              <Metric value={results ? rejected.length : '—'} label={rejected.length === 1 ? 'rejected image' : 'rejected images'} icon="warning" warm />
            </section>
            {!analysisComplete || !results?.products.length ? (
              <Loading progress={results?.progress} status={results?.status} />
            ) : (
              <div className="pf-body">
                <aside className="pf-rail" aria-label="Products in this run">
                  <div className="pf-rail-heading"><span>Your products</span><span>{String(drafts.length).padStart(2, '0')}</span></div>
                  <div className="pf-product-list">
                    {drafts.map((product, index) => {
                      return (
                        <button className="pf-product-tab" type="button" key={product.id} aria-pressed={index === selected} aria-label={'Review ' + (product.product_name || 'Untitled product')} aria-describedby={'pf-status-' + product.id} disabled={editingDraft !== null || saving !== null} onClick={() => selectProduct(index)}>
                          <span className="pf-tab-image">
                            <ProductPhoto src={productImage(product, images)} alt="" sizes="48px" />
                            {product.confirmation_status === 'approved' && <span className="pf-approved-tick" aria-hidden="true"><Icon name="check" /></span>}
                          </span>
                          <span className="pf-tab-copy">
                            <span className="pf-tab-name">{product.product_name || 'Untitled product'}</span>
                            <span className="pf-sr-only" id={'pf-status-' + product.id}>{isPending(product) ? 'To review' : statusLabel(product.confirmation_status)}</span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  {rejected.length > 0 && (
                    <div className="pf-rejected-shortcut">
                      <button type="button" className="pf-rejected-tab" disabled={editingDraft !== null || saving !== null} aria-pressed={selected < 0} onClick={() => selectProduct(-1)}>
                        <Icon name="warning" />
                        <span><b>{rejected.length} image{rejected.length === 1 ? '' : 's'} not included</b><small>View validation note →</small></span>
                      </button>
                    </div>
                  )}
                </aside>
                {selected < 0 ? <Rejected images={rejected} passed={passed} /> : current && (
                  <ProductEditor
                    product={editingDraft ?? current} totalProducts={drafts.length} images={currentImages} imageIndex={imageIndex}
                    setImageIndex={setImageIndex} update={update} onCancel={() => { if (!savingRef.current && !editingDraft && canCancelProduct(current)) { setCancelTarget(current.product_number); setError(''); } }}
                    onApprove={() => decide(editingDraft ?? current, 'approved')} saving={saving !== null} cancelOpen={cancelTarget === current.product_number}
                    editing={editingDraft !== null} onEdit={() => { if (!savingRef.current) { setEditingDraft({...current, features:[...current.features]}); setCancelTarget(null); setError(''); } }}
                    onKeep={() => setCancelTarget(null)} onConfirmCancel={() => decide(current, 'cancelled')}
                  />
                )}
              </div>
            )}
            {error && <p className="pf-error" role="alert">{error}</p>}
            {showReviewFooter && (
              <footer className="pf-footer">
                <div className="pf-review-progress">
                  <div className="pf-review-progress-label"><Icon name={allCancelled ? 'close' : complete ? 'check' : 'layers'} /><span>{reviewLabel}</span></div>
                  <div className="pf-progress-caption">
                    {eligible > 0 && <div className="pf-mini-progress" role="progressbar" aria-label="Products reviewed" aria-valuemin={0} aria-valuemax={eligible} aria-valuenow={reviewedCount} aria-valuetext={reviewLabel}><span style={{ width: reviewedCount / eligible * 100 + '%' }} /></div>}
                    <span>{approved.length} approved{cancelled ? ' · ' + cancelled + ' cancelled' : ''}</span>
                  </div>
                </div>
                <div className="pf-footer-actions">
                  {!editingDraft && pendingCount > 0 && <button type="button" className="pf-button" disabled={saving !== null || cancelTarget !== null} title={`Approve all ${pendingCount} remaining unreviewed products`} onClick={approveAll}>{saving === 'all' ? 'Approving all…' : 'Approve all'}</button>}
                  {editingDraft ? <>
                    <button type="button" className="pf-button" disabled={saving !== null} onClick={() => { setEditingDraft(null); setError(''); }}>Discard changes</button>
                    <button type="submit" form="pf-product-form" className="pf-button pf-primary" disabled={saving !== null}>{saving !== null ? 'Saving…' : 'Save changes'}<Icon name="check" /></button>
                  </> : selected < 0 ? (
                    <button type="button" className="pf-button" onClick={() => selectProduct(0)}>Back to products <Icon name="arrow" /></button>
                  ) : complete ? (
                    <button type="button" className="pf-button pf-primary" disabled={saving !== null} onClick={() => setScreen('summary')}>Done reviewing <Icon name="check" /></button>
                  ) : current && (
                    <button type="submit" form="pf-product-form" className="pf-button pf-primary" disabled={saving !== null || cancelTarget !== null || !isPending(current)}><Icon name="check" />{saving === current.product_number ? 'Saving…' : 'Approve product'}</button>
                  )}
                </div>
              </footer>
            )}
          </>
        )}
      </section>
    </div>
  );
}

const iconPaths = {
  close: <path d="m6 6 12 12M18 6 6 18" />,
  check: <path d="m5 12 4 4L19 6" />,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
  chevronLeft: <path d="m14 6-6 6 6 6" />,
  chevronRight: <path d="m10 6 6 6-6 6" />,
  image: <><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8" cy="8" r="1.5" /><path d="m3 17 5-5 4 4 4-6 5 7" /></>,
  shield: <><path d="m12 3 8 3v5c0 5-4 8-8 10-4-2-8-5-8-10V6l8-3Z" /><path d="m8 12 3 3 5-6" /></>,
  layers: <path d="m3 7 9-4 9 4-9 4-9-4Zm0 5 9 4 9-4M3 17l9 4 9-4" />,
  warning: <><path d="m12 3 10 18H2L12 3Z" /><path d="M12 9v5m0 3v.1" /></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2" /></>,
  sparkle: <path d="m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3Z" />
};
type IconName = keyof typeof iconPaths;
function Icon({ name }: { name: IconName }) {
  return <svg className="pf-icon" viewBox="0 0 24 24" aria-hidden="true">{iconPaths[name]}</svg>;
}
function Metric({ value, label, icon, warm = false }: { value: number | string; label: string; icon: IconName; warm?: boolean }) {
  return <div className={'pf-metric' + (warm ? ' warm' : '')}><Icon name={icon} /><strong>{value}</strong><span>{label}</span></div>;
}
function isPending(product: Product) { return product.confirmation_status === 'suggested' || product.confirmation_status === 'pending'; }
function canCancelProduct(product: Product) { return isPending(product) || product.confirmation_status === 'approved'; }
function approvalFields(product: Product) {
  return { product_name:product.product_name.trim(), product_type:product.product_type.trim(), colours:product.colours.trim(), materials:product.materials.trim(), features:product.features.map(item => item.trim()).filter(Boolean), description:product.description.trim() };
}
function approvalError(product: ReturnType<typeof approvalFields>) {
  if (!product.product_name) return 'Every product needs a name before approval.';
  if (!product.product_type || !product.colours || !product.materials || !product.description || !product.features.length || product.features.length > 30) return 'Complete each product field and include between 1 and 30 features before saving.';
  if (product.product_name.length > 160 || product.product_type.length > 160 || product.colours.length > 300 || product.materials.length > 300 || product.description.length > 320) return 'Shorten any fields that exceed their character limits before saving.';
  return null;
}
function statusLabel(status: string) { return status ? status[0].toUpperCase() + status.slice(1) : 'To review'; }
function productImage(product: Product, images: ImageResult[]) {
  return images.find(image => image.product_number === product.product_number && image.passed === true && image.image_url)?.image_url ?? null;
}
function ProductPhoto({ src, alt, sizes }: { src: string | null; alt: string; sizes: string }) {
  const [failed, setFailed] = useState<string | null>(null);
  if (!src || failed === src) return <span className="pf-image-empty" role={alt ? 'img' : undefined} aria-label={alt ? alt + ' — image unavailable' : undefined} aria-hidden={alt ? undefined : true}><Icon name="image" /></span>;
  // Signed asset URLs must go directly to storage, without a second optimization request.
  return <Image src={src} alt={alt} fill sizes={sizes} unoptimized onError={() => setFailed(src)} />;
}
function isAnalysisFinished(status?: string) { return status === 'awaiting_confirmation' || status === 'completed' || status === 'failed'; }

function Loading({ progress, status }: { progress?: Results['progress']; status?: string }) {
  if (isAnalysisFinished(status)) return <div className="pf-loading pf-loading-stopped" role="status">
    <Icon name={status === 'failed' ? 'warning' : 'image'} />
    <h3>{status === 'failed' ? 'We couldn’t finish this analysis.' : 'No products to review.'}</h3>
    <p>{status === 'failed' ? 'Try again with clear photos of clothing, shoes, bags or accessories.' : 'Try another selection of product images.'}</p>
  </div>;
  const statusMessages: Record<string, string> = { pending:'Waiting for analysis to start', queued:'Waiting for analysis to start', screening:'Checking your uploaded images', grouping:'Grouping matching images', analysing:'Analysing your products' };
  const message = progress?.message?.trim() || statusMessages[status ?? ''] || 'Waiting for a progress update';
  const stage = progress?.stage ?? status ?? '';
  const stageTitles: Record<string, string> = { validation:'Checking your images', screening:'Analysing your images', analysis:'Analysing your images', grouping:'Grouping your products', synthesis:'Preparing product details' };
  const unit = stage === 'synthesis' ? 'products' : ['validation', 'screening', 'analysis'].includes(stage) ? 'images' : null;
  const hasCount = !!progress && Number.isFinite(progress.total) && progress.total > 0 && Number.isFinite(progress.completed) && unit !== null;
  const stageTotal = hasCount ? progress!.total : 0;
  const stageCompleted = hasCount ? Math.min(stageTotal, Math.max(0, progress!.completed)) : 0;
  // The worker's percent weights the whole pipeline. This bar tracks completed
  // images (or product details) in the named stage instead.
  const percent = hasCount ? Math.round(stageCompleted / stageTotal * 100) : null;
  const stageCount = hasCount ? `${stageCompleted} of ${stageTotal} ${unit}` : '';
  const progressDescription = [message, stageCount, percent === null ? '' : `${percent}%`].filter(Boolean).join(' · ');

  return (
    <div className="pf-loading">
      <div className="pf-loading-batch">
        <div className="pf-loading-images" aria-hidden="true">{[0, 1, 2].map(index => <div className="pf-loading-image" key={index} style={{ '--thumbnail-index': index } as CSSProperties}><Icon name="image" /></div>)}</div>
        <div className="pf-loading-copy">
          <div className="pf-loading-title"><span className="pf-spinner" aria-hidden="true" /><strong>{stageTitles[stage] ?? 'Reviewing your products'}</strong></div>
          <div className="pf-loading-messages" aria-hidden="true">
            <span className="pf-loading-message entering" key={message}>{message}</span>
          </div>
          <span className="pf-sr-only" role="status">{progressDescription}</span>
        </div>
        <div className={'pf-progress' + (percent === null ? ' indeterminate' : '')} role="progressbar" aria-label="Analysis progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent ?? undefined} aria-valuetext={progressDescription}><i style={percent === null ? undefined : { width: percent + '%' }} /></div>
        <div className="pf-live-progress" aria-hidden="true"><span>{stageCount || (stage === 'grouping' ? 'Finding matching products' : 'Waiting for the next update')}</span>{percent !== null && <span>{percent}%</span>}</div>
      </div>
    </div>
  );
}
function Rejected({ images, passed }: { images: ImageResult[]; passed: number }) {
  return (
    <section className="pf-editor pf-rejection" aria-label="Rejected image details">
      <h3>Products that didn’t quite fit</h3>
      <p>{passed > 0 ? 'Your other ' + passed + ' image' + (passed === 1 ? ' is' : 's are') + ' ready. ' : ''}We couldn’t use {images.length === 1 ? 'this one' : 'these images'}.</p>
      {images.map(image => <article className="pf-rejection-card" key={image.id}><div className="pf-rejection-photo"><ProductPhoto src={image.image_url} alt={image.filename ?? 'Rejected upload'} sizes="128px" /></div><div><span className="pf-eyebrow">Image {image.image_number}</span><h4>{image.filename ?? 'Uploaded image'}</h4><p><span className="pf-reason-label">Reason:</span> {shortReason(image.rejection_reason)}</p></div></article>)}
      <div className="pf-rejection-explainer"><Icon name="image" /><span>Try clear, well-lit photos of clothing, shoes, bags or fashion accessories.</span></div>
    </section>
  );
}
function shortReason(reason: string | null) { return (reason ?? 'Image did not meet fashion-product requirements.').split(' ').slice(0, 8).join(' '); }

type EditorProps = {
  product: Draft; totalProducts: number; images: ImageResult[]; imageIndex: number;
  setImageIndex: (value: number) => void; update: (number: number, key: keyof Draft, value: string | string[]) => void;
  onCancel: () => void; onApprove: () => void; saving: boolean; cancelOpen: boolean; onKeep: () => void; onConfirmCancel: () => void;
  editing?: boolean; onEdit?: () => void;
};
function ProductEditor({ product, totalProducts, images, imageIndex, setImageIndex, update, onCancel, onApprove, saving, cancelOpen, onKeep, onConfirmCancel, editing = false, onEdit }: EditorProps) {
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const editButtonRef = useRef<HTMLButtonElement>(null);
  const nameFieldRef = useRef<HTMLInputElement>(null);
  const wasEditing = useRef(false);
  useEffect(() => {
    if (editing) nameFieldRef.current?.focus({ preventScroll: true });
    else if (wasEditing.current) editButtonRef.current?.focus({ preventScroll: true });
    wasEditing.current = editing;
  }, [editing]);
  const dismissCancellation = () => {
    onKeep();
    cancelButtonRef.current?.focus({ preventScroll: true });
  };
  const visibleIndex = Math.min(imageIndex, Math.max(0, images.length - 1));
  const image = images[visibleIndex];
  const locked = !isPending(product) && !(editing && product.confirmation_status === 'approved');
  const field = (key: EditableField, label: string, full = true) => {
    const id = 'pf-field-' + key;
    return (
      <label className={'pf-field' + (full ? ' pf-full' : '')} htmlFor={id}>
        <span>{label}</span>
        {key === 'features' ? (
          <FeaturesInput key={product.id + ':' + product.confirmation_status + ':' + editing} id={id} features={product.features} locked={locked || saving} onChange={value => update(product.product_number, key, value)} />
        ) : key === 'description' ? (
          <textarea id={id} name={key} className="pf-description-field" rows={4} readOnly={locked || saving} required maxLength={320}
            value={product.description} onChange={event => update(product.product_number, key, event.target.value)} />
        ) : (
          <input id={id} name={key} ref={key === 'product_name' ? nameFieldRef : undefined} value={product[key]} readOnly={locked || saving} required maxLength={key === 'product_name' || key === 'product_type' ? 160 : 300}
            onChange={event => update(product.product_number, key, event.target.value)} />
        )}
      </label>
    );
  };
  return (
    <section className="pf-editor" aria-label="Selected product details">
      <div className="pf-editor-top">
        <span className="pf-eyebrow">Product {String(product.product_number).padStart(2, '0')} / {String(totalProducts).padStart(2, '0')}</span>
        <button type="button" className="pf-icon-button" ref={cancelButtonRef} onClick={onCancel} disabled={!canCancelProduct(product) || editing || saving} aria-label="Cancel product"><Icon name="close" /></button>
      </div>
      {!isPending(product) && <div className={'pf-decision-note ' + product.confirmation_status}>
        <span>{editing ? 'Editing approved details. Save or discard your changes to continue.' : product.confirmation_status === 'approved' ? 'Approved for the Product Library.' : statusLabel(product.confirmation_status) + ' — excluded from the library.'}</span>
        {product.confirmation_status === 'approved' && !editing && onEdit && <button type="button" className="pf-edit-details" ref={editButtonRef} disabled={saving} onClick={onEdit}>Edit details</button>}
      </div>}
      <div className="pf-editor-grid">
        <div className="pf-gallery">
          <div className="pf-hero-image">
            <ProductPhoto src={image?.image_url ?? null} alt={product.product_name || 'Product image'} sizes="(max-width: 390px) 100px, (max-width: 760px) 30vw, 300px" />
            {image && <span className="pf-image-label">Image {visibleIndex + 1} of {images.length}</span>}
            {images.length > 1 && <>
              <button type="button" onClick={() => setImageIndex((visibleIndex - 1 + images.length) % images.length)} className="pf-arrow previous" aria-label="Previous image"><Icon name="chevronLeft" /></button>
              <button type="button" onClick={() => setImageIndex((visibleIndex + 1) % images.length)} className="pf-arrow next" aria-label="Next image"><Icon name="chevronRight" /></button>
            </>}
          </div>
          <div className="pf-thumbnails" aria-label="Grouped product images">
            {images.map((item, index) => <button type="button" className="pf-thumbnail" aria-pressed={index === visibleIndex} aria-label={'View image ' + (index + 1) + ' of ' + product.product_name} key={item.id} onClick={() => setImageIndex(index)}><ProductPhoto src={item.image_url} alt="" sizes="80px" /></button>)}
          </div>
          <section className="pf-category" aria-label="Read-only category"><dl><dt><span>Category</span><Icon name="lock" /></dt><dd>{product.category}</dd></dl><small>Read-only classification</small></section>
        </div>
        <form id="pf-product-form" className="pf-product-form" onSubmit={event => { event.preventDefault(); if (!locked && !saving && !cancelOpen) onApprove(); }}>
          <div className="pf-fields">
            {field('product_name', 'Product name')}
            {field('product_type', 'Product type')}
            {field('colours', 'Colours', false)}
            {field('materials', 'Materials', false)}
            {field('features', 'Features')}
            {field('description', 'Description')}
          </div>
          <p className="pf-suggested"><Icon name="sparkle" />{editing ? 'Saved changes also update this product in your Product Library.' : 'Suggested details can be changed as you see fit.'}</p>
        </form>
      </div>
      {cancelOpen && <div className="pf-inline-confirm" role="alertdialog" aria-labelledby="pf-cancel-title" aria-describedby="pf-cancel-description" onKeyDown={event => {
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); dismissCancellation(); }
        if (event.key === 'Tab') {
          const choices = event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)');
          const first = choices[0], last = choices[choices.length - 1];
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
          else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        }
      }}>
        <h3 id="pf-cancel-title">Cancel this product?</h3><p id="pf-cancel-description">{product.confirmation_status === 'approved' ? 'It will be removed from your Product Library, but its details and images will stay in this run.' : 'It will stay in this run, but won’t enter your Product Library.'}</p>
        <div className="pf-confirm-actions"><button type="button" className="pf-button" onClick={dismissCancellation} autoFocus>Keep product</button><button type="button" className="pf-button pf-cancel-confirm" disabled={saving} onClick={onConfirmCancel}>Cancel product</button></div>
      </div>}
    </section>
  );
}
function FeaturesInput({ id, features, locked, onChange }: { id:string; features:string[]; locked:boolean; onChange:(value:string[]) => void }) {
  // Keep exact keystrokes (spaces and commas included); normalize only on save.
  const [text, setText] = useState(() => features.join(', '));
  return <textarea id={id} name="features" rows={2} readOnly={locked} required value={text} onChange={event => {
    setText(event.target.value);
    onChange(event.target.value.split(','));
  }} />;
}
function Summary({ approved, images, onBack, onProduce }: { approved: Product[]; images: ImageResult[]; onBack: () => void; onProduce: () => void }) {
  return (
    <>
      <section className="pf-summary" aria-label="Approved products">
        {approved.length ? <>
          <ul className="pf-summary-grid" style={{ '--approved-count': Math.min(approved.length, 4) } as CSSProperties}>
            {approved.map((product, index) => <li className="pf-summary-card" key={product.id} style={{ '--card-index': index } as CSSProperties}>
              <div className="pf-summary-photo"><ProductPhoto src={productImage(product, images)} alt="" sizes="(max-width: 760px) 40vw, 240px" /><span className="pf-summary-tick" aria-label="Approved"><Icon name="check" /></span></div>
              <h3>{product.product_name}</h3>
            </li>)}
          </ul>
          <p className="pf-summary-next">The pieces are picked. Let’s set the scene.</p>
        </> : <div className="pf-summary-empty"><Icon name="layers" /><h3>A fresh edit starts here.</h3><p>No products have been approved for the next step.</p></div>}
      </section>
      <footer className="pf-footer pf-step-footer">
        <button type="button" className="pf-button pf-step-back" onClick={onBack}><Icon name="chevronLeft" />Back to review</button>
        {approved.length > 0 && <button type="button" className="pf-button pf-primary" onClick={onProduce}>Produce outputs <Icon name="arrow" /></button>}
      </footer>
    </>
  );
}
