'use client';

import { useAuth } from '@clerk/nextjs';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState, useTransition, type KeyboardEvent, type ReactNode } from 'react';
import LibraryShell from './LibraryShell';
import type { GalleryAsset, GeneratedAsset, LibraryMode, ProductDetail, ProductSummary, SourceUpload } from './library-types';
import './product-library.css';

type SortOrder = 'newest' | 'oldest' | 'az' | 'za';
type PreviewAsset = { id: string; name: string; image_url: string; kind: string; product_name: string; product_id: string; created_at: string; filename: string };
type Props = { initial: ProductSummary[]; userId: string | null; mode: LibraryMode; selectedId?: string; detail: ProductDetail | null; gallery: GalleryAsset[]; loadError: string; detailError: string };

export default function ProductLibrary({ initial, userId, mode, selectedId, detail, gallery, loadError, detailError }: Props) {
  const router = useRouter();
  const { getToken } = useAuth();
  const [navigating, startTransition] = useTransition();
  const [sort, setSort] = useState<SortOrder>('newest');
  const [selectionMode, setSelectionMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleted, setDeleted] = useState<Set<string>>(new Set());
  const [confirmProducts, setConfirmProducts] = useState<ProductSummary[]>([]);
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [previewAsset, setPreviewAsset] = useState<PreviewAsset | null>(null);
  const products = sorted(initial.filter(product => !deleted.has(product.id)), sort);
  const approvedGallery = sorted(gallery.filter(asset => asset.status === 'approved' && !deleted.has(asset.product_id)), sort);
  const selection = products.filter(product => selected.has(product.id));
  const folder = detail && !deleted.has(detail.id) ? detail : null;
  const modeLabel = mode === 'gallery' ? 'Gallery' : 'Catalogue';

  function navigate(url: string) {
    setSelectionMode(false);
    setSelected(new Set());
    setError('');
    setNotice('');
    startTransition(() => router.push(url));
  }

  function toggleProduct(id: string) {
    setSelected(current => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  async function copyFolderLink(id: string) {
    setError('');
    try {
      await navigator.clipboard.writeText(new URL(`/products?product=${encodeURIComponent(id)}`, window.location.origin).href);
      setNotice('Folder link copied. Workspace sign-in is required to open it.');
    } catch { setError('The link could not be copied. You can copy this folder’s address from your browser.'); }
  }

  async function downloadUploads(product: { id: string; name: string }) {
    if (downloading) return;
    setDownloading(true);
    setError('');
    try {
      const token = await getToken();
      if (!token) throw new Error('Sign in again to download your uploads.');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/products/${encodeURIComponent(product.id)}/download`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error(response.status === 409 ? 'This folder has no uploads to download.' : 'The uploads could not be downloaded. Please try again.');
      saveBlob(await response.blob(), `${safeFilename(product.name)}-uploads.zip`);
      setNotice('Your uploads are ready to download.');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The download failed. Please try again.'); }
    finally { setDownloading(false); }
  }

  async function removeProducts() {
    if (deleting || !confirmProducts.length) return;
    setDeleting(true);
    setError('');
    const removed: string[] = [];
    try {
      const token = await getToken();
      if (!token) throw new Error('Sign in again to delete products.');
      for (const product of confirmProducts) {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/products/${encodeURIComponent(product.id)}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
        if (!response.ok) throw new Error(`“${product.name}” could not be deleted. Please try again.`);
        removed.push(product.id);
      }
      setNotice(`${countLabel(removed.length, 'product')} deleted.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Deletion failed. Please try again.'); }
    finally {
      setDeleted(current => new Set([...current, ...removed]));
      setSelected(current => new Set([...current].filter(id => !removed.includes(id))));
      setConfirmProducts([]);
      setDeleting(false);
      if (selectedId && removed.includes(selectedId)) router.replace('/products');
      router.refresh();
    }
  }

  function modeKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const nextMode = event.key === 'Home' ? 'catalogue' : event.key === 'End' ? 'gallery' : mode === 'catalogue' ? 'gallery' : 'catalogue';
    document.getElementById(`pl-tab-${nextMode}`)?.focus();
    navigate(nextMode === 'catalogue' ? '/products' : '/products?view=gallery');
  }

  return <LibraryShell userId={userId} breadcrumb={folder ? `Catalogue / ${folder.name}` : modeLabel}>
    <div className="pl-mode-switch" role="tablist" aria-label="Product library view">
      {(['catalogue', 'gallery'] as const).map(value => <button key={value} id={`pl-tab-${value}`} type="button" role="tab" aria-selected={mode === value} aria-controls="pl-library-panel" tabIndex={mode === value ? 0 : -1} onKeyDown={modeKeyDown} onClick={() => navigate(value === 'catalogue' ? '/products' : '/products?view=gallery')}><LibraryIcon name={value === 'catalogue' ? 'folder' : 'image'}/>{value === 'catalogue' ? 'Catalogue' : 'Gallery'}</button>)}
    </div>
    {(error || loadError) && <div className="pl-error" role="alert">{error || loadError}{loadError && <button className="pl-secondary" type="button" onClick={() => router.refresh()}>Try again</button>}</div>}
    {notice && <p className="pl-notice" role="status">{notice}</p>}
    {navigating && <p className="pl-loading" role="status">Loading your library…</p>}
    <div id="pl-library-panel" role="tabpanel" aria-labelledby={`pl-tab-${mode}`} aria-busy={navigating}>
      {selectedId ? <>
        <button type="button" className="pl-back" onClick={() => navigate('/products')}><LibraryIcon name="back"/>Back to catalogue</button>
        {folder ? <>
          <header className="pl-header">
            <div><p className="pl-eyebrow">PRODUCT FOLDER</p><h1 className="pl-title">{folder.name}</h1><p className="pl-detail-meta">{folder.category && `${folder.category} · `}{formatDate(folder.created_at)} · {countLabel(folder.uploads.length, 'upload')} · {countLabel(folder.generated_assets.length, 'generation')}</p></div>
            <div className="pl-detail-actions">
              <button className="pl-icon-button" type="button" title="Copy private folder link" aria-label="Copy folder link" onClick={() => copyFolderLink(folder.id)}><LibraryIcon name="link"/></button>
              <button className="pl-secondary" type="button" onClick={() => downloadUploads(folder)} disabled={downloading || !folder.uploads.length}><LibraryIcon name="download"/>{downloading ? 'Preparing…' : 'Download uploads'}</button>
              <button className="pl-icon-button danger" type="button" aria-label="Delete product" title="Delete product" disabled={!initial.some(product => product.id === folder.id)} onClick={() => setConfirmProducts(initial.filter(product => product.id === folder.id))}><LibraryIcon name="delete"/></button>
            </div>
          </header>
          <section className="pl-asset-section" aria-labelledby="pl-uploads-title">
            <header><h2 id="pl-uploads-title">Uploads</h2><span>{countLabel(folder.uploads.length, 'image')}</span></header>
            {folder.uploads.length ? <div className="pl-assets">{sortedUploads(folder.uploads).map(asset => <AssetCard key={asset.id} asset={sourcePreview(asset, folder)} onOpen={setPreviewAsset}/>)}</div> : <div className="pl-empty pl-empty-compact"><p>This product has no uploaded images yet.</p></div>}
          </section>
          <section className="pl-asset-section" aria-labelledby="pl-generations-title">
            <header><h2 id="pl-generations-title">Generations</h2><span>{countLabel(folder.generated_assets.length, 'output')}</span></header>
            {folder.generated_assets.length ? <div className="pl-assets">{folder.generated_assets.map(asset => <AssetCard key={asset.id} asset={generationPreview(asset, folder)} status={asset.status} onOpen={setPreviewAsset}/>)}</div> : <div className="pl-empty pl-empty-compact"><LibraryIcon name="image"/><p>Generated outputs for this product will appear here. Approved outputs will also appear in Gallery.</p></div>}
          </section>
        </> : <EmptyState icon="folder" title="Folder unavailable" text={detailError || 'This product could not be found.'}><button type="button" className="pl-secondary" onClick={() => router.refresh()}>Try again</button></EmptyState>}
      </> : <>
        <header className="pl-header">
          <div><p className="pl-eyebrow">{mode === 'gallery' ? 'APPROVED GENERATED CONTENT' : 'PRODUCT LIBRARY'}</p><h1 className="pl-title">{modeLabel}</h1><p className="pl-subtitle">{mode === 'gallery' ? 'Every approved generation, ready for its next moment.' : 'Your products, with every upload and generation in one place.'}</p></div>
          <div className="pl-header-actions"><span className="pl-stat"><b>{mode === 'gallery' ? approvedGallery.length : products.length}</b> {mode === 'gallery' ? 'outputs' : 'folders'}</span><Link className="pl-primary" href="/studio?view=create" prefetch={false}><LibraryIcon name="plus"/>{mode === 'gallery' ? 'Create assets' : 'New product'}</Link></div>
        </header>
        <div className="pl-toolbar">
          <label className="pl-sort">Sort by <select aria-label="Sort library" value={sort} onChange={event => setSort(event.target.value as SortOrder)}><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="az">A–Z</option><option value="za">Z–A</option></select></label>
          {mode === 'catalogue' && <div className="pl-selection-controls">
            {selectionMode && <div className="pl-bulk-actions">
              <span aria-live="polite">{selection.length} selected</span>
              <button className="pl-icon-button" type="button" aria-label={selection.length === products.length ? 'Deselect all folders' : 'Select all folders'} title="Select all folders" onClick={() => setSelected(selection.length === products.length ? new Set() : new Set(products.map(product => product.id)))}><LibraryIcon name="select"/></button>
              <button className="pl-icon-button" type="button" aria-label="Download selected folder uploads" title={selection.length !== 1 ? 'Select one folder to download its uploads' : 'Download uploads'} disabled={selection.length !== 1 || downloading || !selection[0]?.upload_count} onClick={() => downloadUploads(selection[0])}><LibraryIcon name="download"/></button>
              <button className="pl-icon-button" type="button" aria-label="Copy selected folder link" title={selection.length !== 1 ? 'Select one folder to copy its link' : 'Copy private folder link'} disabled={selection.length !== 1} onClick={() => copyFolderLink(selection[0].id)}><LibraryIcon name="link"/></button>
              <button className="pl-icon-button danger" type="button" aria-label="Delete selected products" title="Delete selected products" disabled={!selection.length} onClick={() => setConfirmProducts(selection)}><LibraryIcon name="delete"/></button>
            </div>}
            <button className="pl-secondary" type="button" disabled={!products.length} aria-pressed={selectionMode} onClick={() => { setSelectionMode(!selectionMode); setSelected(new Set()); }}>{selectionMode ? 'Cancel' : 'Select'}</button>
          </div>}
        </div>
        {mode === 'catalogue' ? products.length ? <div className="pl-folder-grid">{products.map(product => {
          const images = product.preview_images?.length ? product.preview_images : product.image_url ? [{ id: product.id, image_url: product.image_url, filename: product.name }] : [];
          return <article className={`pl-folder${selected.has(product.id) ? ' is-selected' : ''}`} key={product.id}>
            <button type="button" className="pl-folder-open" aria-label={`${selectionMode ? 'Select' : 'Open'} ${product.name}`} aria-pressed={selectionMode ? selected.has(product.id) : undefined} onClick={() => selectionMode ? toggleProduct(product.id) : navigate(`/products?product=${encodeURIComponent(product.id)}`)}>
              <div className="pl-folder-top"><LibraryIcon name="folder"/><span>{product.category || 'Product'}</span></div>
              <div className="pl-folder-preview" style={{ gridTemplateColumns: `repeat(${Math.max(1, images.length)}, minmax(0, 1fr))` }}>
                {images.length ? images.map(image => <div className="pl-folder-thumbnail" key={image.id}><Image src={image.image_url} alt="" fill sizes="(max-width: 700px) 85vw, 300px" unoptimized/></div>) : <div className="pl-preview-placeholder"><LibraryIcon name="folder"/><span>No uploads yet</span></div>}
              </div>
              <div className="pl-folder-copy"><h2>{product.name}</h2><div className="pl-folder-meta"><span>{formatDate(product.created_at)}</span><span>{countLabel(product.upload_count ?? 0, 'upload')} · {countLabel(product.generated_count ?? 0, 'generation')}</span></div></div>
              {selected.has(product.id) && <span className="pl-selection-check" aria-hidden="true">✓</span>}
            </button>
          </article>;
        })}</div> : !loadError && <EmptyState icon="folder" title="A home for every product" text="Upload and approve a product to create its folder. Its source images and generations will stay together here."><Link className="pl-primary" href="/studio?view=create">Create your first product<LibraryIcon name="plus"/></Link></EmptyState>
          : approvedGallery.length ? <div className="pl-gallery-grid">{approvedGallery.map(asset => <AssetCard key={asset.id} asset={generationPreview(asset, { id: asset.product_id, name: asset.product_name })} status="approved" showProduct onOpen={setPreviewAsset}/>)}</div>
          : !loadError && <EmptyState icon="image" title="Your approved work, all together" text="Approved generated outputs will appear here. You can find original uploads inside each product’s catalogue folder."><button className="pl-secondary" type="button" onClick={() => navigate('/products')}>Browse catalogue<LibraryIcon name="back"/></button></EmptyState>}
      </>}
    </div>

    <LibraryDialog open={confirmProducts.length > 0} onClose={() => { if (!deleting) setConfirmProducts([]); }} label="pl-delete-title">
      <header className="pl-dialog-head"><div><p className="pl-eyebrow">DELETE FROM CATALOGUE</p><h2 id="pl-delete-title">Delete {countLabel(confirmProducts.length, 'product')}?</h2></div><button className="pl-dialog-close" type="button" aria-label="Close delete confirmation" disabled={deleting} onClick={() => setConfirmProducts([])}><LibraryIcon name="close"/></button></header>
      <p>The selected products and their uploaded images will be permanently deleted. This cannot be undone.</p>
      <ul className="pl-confirm-list">{confirmProducts.map(product => <li key={product.id}>{product.name}</li>)}</ul>
      <footer className="pl-dialog-actions"><button className="pl-secondary" type="button" disabled={deleting} onClick={() => setConfirmProducts([])}>Cancel</button><button className="pl-primary danger" type="button" disabled={deleting} onClick={removeProducts}>{deleting ? 'Deleting…' : 'Delete permanently'}</button></footer>
    </LibraryDialog>

    <LibraryDialog open={Boolean(previewAsset)} onClose={() => setPreviewAsset(null)} label="pl-preview-title" preview>
      {previewAsset && <>
        <header className="pl-dialog-head"><div><p className="pl-eyebrow">{previewAsset.kind}</p><h2 id="pl-preview-title">{previewAsset.name}</h2><p>{previewAsset.product_name} · {formatDate(previewAsset.created_at)}</p></div><button className="pl-dialog-close" type="button" aria-label="Close image preview" onClick={() => setPreviewAsset(null)}><LibraryIcon name="close"/></button></header>
        <div className="pl-preview-image"><Image src={previewAsset.image_url} alt={previewAsset.name} width={1200} height={1000} unoptimized/></div>
        <footer className="pl-dialog-footer"><span>{previewAsset.kind === 'Upload' ? 'Original product image' : 'Generated product content'}</span><a className="pl-secondary" href={previewAsset.image_url} target="_blank" rel="noreferrer">Open full image<LibraryIcon name="external"/></a></footer>
      </>}
    </LibraryDialog>
  </LibraryShell>;
}

function AssetCard({ asset, status, showProduct, onOpen }: { asset: PreviewAsset; status?: GeneratedAsset['status']; showProduct?: boolean; onOpen: (asset: PreviewAsset) => void }) {
  return <article className="pl-asset-card"><button type="button" className="pl-asset-open" onClick={() => onOpen(asset)} aria-label={`Preview ${asset.name}`}><div className="pl-asset-image"><Image src={asset.image_url} alt={asset.name} fill sizes="(max-width: 700px) 85vw, 300px" unoptimized/><span className="pl-asset-badge">{showProduct ? asset.product_name : asset.kind}</span></div><div className="pl-asset-copy"><div><b title={asset.name}>{asset.name}</b><small>{formatDate(asset.created_at)}</small></div><span className={`pl-status ${status || ''}`}>{status ? statusLabel(status) : 'Original'}</span></div></button></article>;
}

function EmptyState({ icon, title, text, children }: { icon: 'folder' | 'image'; title: string; text: string; children?: ReactNode }) {
  return <div className="pl-empty"><LibraryIcon name={icon}/><h2>{title}</h2><p>{text}</p>{children}</div>;
}

function LibraryDialog({ open, onClose, label, preview, children }: { open: boolean; onClose: () => void; label: string; preview?: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!open || !dialog) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    if (!dialog.open) dialog.showModal();
    return () => { dialog.close(); document.body.style.overflow = overflow; opener?.isConnected && opener.focus({ preventScroll: true }); };
  }, [open]);
  return <dialog ref={ref} className={`pl-dialog${preview ? ' pl-preview-dialog' : ''}`} aria-labelledby={label} onCancel={event => { event.preventDefault(); onClose(); }} onClick={event => {
    if (event.target !== event.currentTarget) return;
    const r = event.currentTarget.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) onClose();
  }}>{children}</dialog>;
}

function sorted<T extends { name: string; created_at: string }>(items: T[], sort: SortOrder) {
  return [...items].sort((a, b) => {
    if (sort === 'az') return a.name.localeCompare(b.name);
    if (sort === 'za') return b.name.localeCompare(a.name);
    const difference = (Date.parse(a.created_at || '') || 0) - (Date.parse(b.created_at || '') || 0);
    return sort === 'newest' ? -difference : difference;
  });
}

function sortedUploads(uploads: SourceUpload[]) { return [...uploads].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)); }
function countLabel(count: number, word: string) { return `${count} ${word}${count === 1 ? '' : 's'}`; }
function formatDate(value: string) {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Date unavailable';
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(value));
}
function sourcePreview(asset: SourceUpload, product: { id: string; name: string }): PreviewAsset {
  return { ...asset, name: asset.filename || 'Uploaded image', kind: 'Upload', product_id: product.id, product_name: product.name };
}
function generationPreview(asset: GeneratedAsset, product: { id: string; name: string }): PreviewAsset {
  return { ...asset, kind: 'Generation', product_id: product.id, product_name: product.name };
}
function statusLabel(status: GeneratedAsset['status']) {
  return { pending: 'Queued', generating: 'Creating', ready: 'Needs review', approved: 'Approved', rejected: 'Rejected', failed: 'Failed' }[status];
}
function safeFilename(name: string) { return name.replace(/[^a-z0-9._-]+/gi, '-').replace(/^[-.]+|[-.]+$/g, '').slice(0, 100) || 'product'; }
function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

type LibraryIconName = 'folder' | 'image' | 'back' | 'download' | 'link' | 'delete' | 'select' | 'plus' | 'close' | 'external';
function LibraryIcon({ name }: { name: LibraryIconName }) {
  const paths = {
    folder: <><path d="M5.5 7.5V6a1.5 1.5 0 0 1 1.5-1.5h4l2 2h4a1.5 1.5 0 0 1 1.5 1.5v2"/><path d="M4 9a1.5 1.5 0 0 1 1.5-1.5H9l2 2h7.5A1.5 1.5 0 0 1 20 11v6.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5Z"/></>,
    image: <><rect x="3" y="4" width="18" height="16" rx="2.75"/><circle cx="8.6" cy="9.5" r="1.7"/><path d="m20.7 15.6-3.15-3.15a2 2 0 0 0-2.83 0L6.9 20"/></>,
    back: <path d="M20 12H4m6-6-6 6 6 6"/>,
    download: <path d="M12 3v12m-4-4 4 4 4-4M5 20h14"/>,
    link: <><path d="m10 13 4-4m-6.5 6.5-1 1a3.5 3.5 0 0 1-5-5l4-4a3.5 3.5 0 0 1 5 0m3 2 1-1a3.5 3.5 0 0 1 5 5l-4 4a3.5 3.5 0 0 1-5 0" transform="translate(2 0)"/></>,
    delete: <path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5"/>,
    select: <><rect x="4" y="4" width="16" height="16" rx="2"/><path d="m8 12 3 3 5-6"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
    close: <path d="m6 6 12 12M18 6 6 18"/>,
    external: <path d="M14 4h6v6m0-6L10 14M10 4H4v16h16v-6"/>,
  };
  return <svg className="pl-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}
