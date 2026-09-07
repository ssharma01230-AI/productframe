'use client';

import { UserButton } from '@clerk/nextjs';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import ProductForm from './ProductForm';
import CreateView from './CreateView';
import type { OutputProduct } from './OutputSelection';
import StudioIcon from './StudioIcon';
import './studio-home.css';

type StudioHomeProps = {
  workspace: { name: string; role: string } | null;
  userId: string | null;
  apiError: boolean;
  message?: string;
  activeRunId?: string;
  initialCreate?: boolean;
  initialSelectedIds?: string[];
  initialOutputStep?: boolean;
  products: OutputProduct[];
};

const exampleImages = {
  product: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500&q=85',
  wardrobe: 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=300&q=80',
  shopping: 'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=300&q=80',
  campaign: 'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=300&q=80',
  style: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=300&q=80',
};

function Navigation({ createOpen, onCreate, onNavigate }: { createOpen: boolean; onCreate: () => void; onNavigate?: () => void }) {
  return <>
    <Link className={`sh-nav-item${createOpen ? '' : ' sh-nav-active'}`} href="/studio" prefetch={false} aria-current={createOpen ? undefined : 'page'} onClick={onNavigate}><StudioIcon name="home"/>Home</Link>
    <button className={`sh-nav-item${createOpen ? ' sh-nav-active' : ''}`} type="button" aria-current={createOpen ? 'page' : undefined} onClick={onCreate}><StudioIcon name="plus"/>Create</button>
    <Link className="sh-nav-item" href="/products" prefetch={false} onClick={onNavigate}><StudioIcon name="folder"/>Product library</Link>
    <button className="sh-nav-item" type="button" disabled title="Explore is not available yet"><StudioIcon name="compass"/>Explore</button>
    <button className="sh-nav-item" type="button" disabled title="Settings are not available yet"><StudioIcon name="settings"/>Settings</button>
  </>;
}

export default function StudioHome({ workspace, userId, apiError, message, activeRunId, products, initialCreate = false, initialSelectedIds = [], initialOutputStep = false }: StudioHomeProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [uploadOpen, setUploadOpen] = useState(false);
  const createOpen = searchParams ? searchParams.get('view') === 'create' : initialCreate;
  const outputStep = searchParams ? createOpen && searchParams.get('step') === 'outputs' : initialOutputStep;
  const selectedProductIds = searchParams ? searchParams.getAll('product') : initialSelectedIds;
  const accountDetails = useRef<HTMLDetailsElement>(null);
  const mobileNavigation = useRef<HTMLDetailsElement>(null);

  useEffect(() => { setUploadOpen(false); }, [activeRunId, message]);

  useEffect(() => {
    function dismissOutside(event: PointerEvent) {
      if (!(event.target instanceof Node)) return;
      for (const details of [accountDetails.current, mobileNavigation.current]) {
        if (details?.open && !details.contains(event.target)) details.open = false;
      }
    }
    document.addEventListener('pointerdown', dismissOutside);
    return () => document.removeEventListener('pointerdown', dismissOutside);
  }, []);

  const openUpload = () => setUploadOpen(true);
  const openCreate = () => {
    const params = new URLSearchParams({ view:'create' });
    selectedProductIds.forEach(id => params.append('product', id));
    router.push('/studio?' + params.toString());
  };
  const closeMobileNavigation = () => {
    const navigation = mobileNavigation.current;
    if (!navigation) return;
    navigation.open = false;
    navigation.querySelector('summary')?.focus();
  };

  return <>
    <div className="sh-shell">
      <a className="sh-skip-link" href="#studio-content">Skip to content</a>
      <aside className="sh-sidebar" aria-label="Studio sidebar">
        <Link className="sh-logo" href="/studio" prefetch={false} aria-label="ProductFrame home"><span className="sh-logo-mark">P</span><span>productframe</span></Link>
        <nav className="sh-navigation" aria-label="Main navigation"><Navigation createOpen={createOpen} onCreate={openCreate}/></nav>
      </aside>

      <div className="sh-main">
        <header className="sh-topbar">
          <div className="sh-topbar-left">
            <details className="sh-mobile-navigation" ref={mobileNavigation} onKeyDown={event => {
              if (event.key === 'Escape') { event.currentTarget.open = false; event.currentTarget.querySelector('summary')?.focus(); }
            }}>
              <summary className="sh-icon-button" aria-label="Open navigation"><StudioIcon name="menu"/></summary>
              <nav className="sh-mobile-navigation-panel" aria-label="Mobile navigation"><Navigation createOpen={createOpen} onCreate={() => { openCreate(); closeMobileNavigation(); }} onNavigate={closeMobileNavigation}/></nav>
            </details>
            <div className="sh-crumb">Studio / <strong>{createOpen ? (outputStep ? 'Choose outputs' : 'Create') : 'Overview'}</strong></div>
          </div>

          <div className="sh-top-actions">
            <details className="sh-account-details" ref={accountDetails} onKeyDown={event => {
              if (event.key === 'Escape') { event.currentTarget.open = false; event.currentTarget.querySelector('summary')?.focus(); }
            }}>
              <summary className="sh-icon-button" aria-label="Workspace and account details" title="Workspace and account details"><StudioIcon name="details"/></summary>
              <div className="sh-account-panel">
                <p className="sh-account-heading">Your workspace</p>
                <dl>
                  <dt><StudioIcon name="workspace"/>Workspace</dt><dd>{workspace?.name ?? 'Unavailable'}</dd>
                  <dt><StudioIcon name="shield"/>Role</dt><dd>{workspace?.role ?? 'Unavailable'}</dd>
                  <dt><StudioIcon name="user"/>User ID</dt><dd className="sh-user-id">{userId ?? 'Not signed in'}</dd>
                </dl>
              </div>
            </details>
            {userId && <div className="sh-account-avatar"><UserButton/></div>}
          </div>
        </header>

        <main className={`sh-content${createOpen ? ' sh-create-content' : ''}`} id="studio-content" tabIndex={-1}>
          {apiError && <p className="sh-service-notice" role="status">The API is currently unavailable. Your workspace details and uploads may be temporarily unavailable.</p>}
          {message && !activeRunId && <p className="sh-service-notice" role="status">{message}</p>}
          {createOpen ? <CreateView products={products} onUpload={openUpload} initialSelectedIds={selectedProductIds} initialOutputStep={outputStep} /> : <>
          <section className="sh-intro" aria-labelledby="studio-home-title">
            <p className="sh-eyebrow">PRODUCTFRAME / CONTENT STUDIO</p>
            <h1 id="studio-home-title">One product.<br/><em>Everywhere it needs to go.</em></h1>
            <p className="sh-lede">Upload it once. Build the full product story from there.</p>
            <div className="sh-hero-actions">
              <button className="sh-upload-button" type="button" aria-haspopup="dialog" onClick={openUpload}><span aria-hidden="true">＋</span>Upload a product</button>
              <button className="sh-text-button" type="button" disabled title="Templates are not available yet">Browse templates<StudioIcon name="arrow"/></button>
            </div>
          </section>

          <section className="sh-how-board" aria-labelledby="studio-how-title">
            <h2 className="sh-how-label" id="studio-how-title">A simple way to make product content</h2>
            <ol className="sh-flow">
              <li className="sh-flow-step">
                <div className="sh-flow-visual sh-upload-visual">
                  <span className="sh-upload-plus" aria-hidden="true">＋</span>
                  <span className="sh-visual-caption">Your product</span>
                  <div className="sh-upload-example"><Image src={exampleImages.product} alt="A black leather jacket, an example product upload" fill sizes="(max-width: 640px) 65vw, 220px" unoptimized/></div>
                </div>
                <div className="sh-flow-copy"><span aria-hidden="true">01</span><h3>Upload once</h3><p>Start with the image you have.</p></div>
              </li>
              <li className="sh-flow-step">
                <div className="sh-flow-visual sh-make-visual" aria-label="Example shop, lifestyle and campaign imagery">
                  {[exampleImages.wardrobe, exampleImages.shopping, exampleImages.campaign, exampleImages.style].map(image => <div className="sh-mini-swatch" key={image}><Image src={image} alt="" fill sizes="(max-width: 640px) 35vw, 140px" unoptimized/></div>)}
                  <span className="sh-spark" aria-hidden="true"><StudioIcon name="sparkle"/></span>
                </div>
                <div className="sh-flow-copy"><span aria-hidden="true">02</span><h3>Choose the moments</h3><p>Shop, lifestyle or campaign.</p></div>
              </li>
              <li className="sh-flow-step">
                <div className="sh-flow-visual sh-outputs-visual" aria-label="Example product story in three visual formats">
                  {[exampleImages.campaign, exampleImages.shopping, exampleImages.wardrobe].map(image => <div className="sh-output-example" key={image}><Image src={image} alt="" fill sizes="(max-width: 640px) 25vw, 95px" unoptimized/></div>)}
                </div>
                <div className="sh-flow-copy"><span aria-hidden="true">03</span><h3>Review what fits</h3><p>Approve the assets you love.</p></div>
              </li>
            </ol>
          </section>

          <div className="sh-landing-foot"><span><i className="sh-green-dot" aria-hidden="true"/>Made for the way products are actually launched</span><span>See your product in every format <span aria-hidden="true">↘</span></span></div>
          </>}
        </main>
      </div>
    </div>
    <ProductForm key={activeRunId ?? 'new-upload'} open={uploadOpen && !activeRunId} onClose={() => setUploadOpen(false)} message={activeRunId ? undefined : message}/>
  </>;
}
