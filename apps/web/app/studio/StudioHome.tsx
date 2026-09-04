'use client';

import { UserButton } from '@clerk/nextjs';
import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import ProductForm from './ProductForm';
import CreateView from './CreateView';
import './studio-home.css';

type StudioHomeProps = {
  workspace: { name: string; role: string } | null;
  userId: string | null;
  apiError: boolean;
  message?: string;
  activeRunId?: string;
  products: { id:string; name:string; image_url:string|null }[];
};

const exampleImages = {
  product: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500&q=85',
  wardrobe: 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=300&q=80',
  shopping: 'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=300&q=80',
  campaign: 'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=300&q=80',
  style: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=300&q=80',
};

type IconName = 'home' | 'plus' | 'folder' | 'compass' | 'settings' | 'menu' | 'details' | 'arrow' | 'sparkle';

function StudioIcon({ name }: { name: IconName }) {
  const paths = {
    home: <><path d="M2.75 11.35 12 3.5l9.25 7.85"/><path d="M5.25 9.3v9.95a1.25 1.25 0 0 0 1.25 1.25h11a1.25 1.25 0 0 0 1.25-1.25V9.3M9.6 20.5v-4.7a2.4 2.4 0 0 1 4.8 0v4.7"/></>,
    plus: <><rect x="3.5" y="3.5" width="17" height="17" rx="4.75"/><path d="M12 8.5v7M8.5 12h7"/></>,
    folder: <><path d="M5.5 7.5V6a1.5 1.5 0 0 1 1.5-1.5h4l2 2h4a1.5 1.5 0 0 1 1.5 1.5v2"/><path d="M4 9a1.5 1.5 0 0 1 1.5-1.5H9l2 2h7.5A1.5 1.5 0 0 1 20 11v6.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5Z"/></>,
    compass: <><circle cx="12" cy="12" r="8.6"/><path d="m15.55 8.45-2.2 4.9-4.9 2.2 2.2-4.9Z"/></>,
    settings: <><path d="m9.5 4 .7-2h3.6l.7 2 2.1 1.2 2.1-.4 1.8 3.1-1.4 1.6v2.5l1.4 1.6-1.8 3.1-2.1-.4-2.1 1.2-.7 2h-3.6l-.7-2-2.1-1.2-2.1.4L3.5 14l1.4-1.6V9.9L3.5 8.3l1.8-3.1 2.1.4Z" transform="translate(0 1)"/><circle cx="12" cy="12" r="3"/></>,
    menu: <path d="M4 6h16M4 12h16M4 18h16"/>,
    details: <><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></>,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6"/>,
    sparkle: <path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z"/>,
  };
  return <svg className="sh-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Navigation({ onUpload, onCreate, onNavigate }: { onUpload: () => void; onCreate: () => void; onNavigate?: () => void }) {
  return <>
    <Link className="sh-nav-item sh-nav-active" href="/studio" prefetch={false} aria-current="page" onClick={onNavigate}><StudioIcon name="home"/>Home</Link>
    <button className="sh-nav-item" type="button" onClick={() => { onNavigate?.(); onCreate(); }}><StudioIcon name="plus"/>Create</button>
    <Link className="sh-nav-item" href="/products" prefetch={false} onClick={onNavigate}><StudioIcon name="folder"/>Product library</Link>
    <button className="sh-nav-item" type="button" disabled title="Explore is not available yet"><StudioIcon name="compass"/>Explore</button>
    <button className="sh-nav-item" type="button" disabled title="Settings are not available yet"><StudioIcon name="settings"/>Settings</button>
  </>;
}

export default function StudioHome({ workspace, userId, apiError, message, activeRunId, products }: StudioHomeProps) {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
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
        <nav className="sh-navigation" aria-label="Main navigation"><Navigation onUpload={openUpload} onCreate={() => setCreateOpen(true)} onNavigate={() => setCreateOpen(false)}/></nav>
      </aside>

      <div className="sh-main">
        <header className="sh-topbar">
          <div className="sh-topbar-left">
            <details className="sh-mobile-navigation" ref={mobileNavigation} onKeyDown={event => {
              if (event.key === 'Escape') { event.currentTarget.open = false; event.currentTarget.querySelector('summary')?.focus(); }
            }}>
              <summary className="sh-icon-button" aria-label="Open navigation"><StudioIcon name="menu"/></summary>
              <nav className="sh-mobile-navigation-panel" aria-label="Mobile navigation"><Navigation onUpload={openUpload} onCreate={() => { setCreateOpen(true); closeMobileNavigation(); }} onNavigate={() => { setCreateOpen(false); closeMobileNavigation(); }}/></nav>
            </details>
            <div className="sh-crumb">Studio / <strong>Overview</strong></div>
          </div>

          <div className="sh-top-actions">
            <details className="sh-account-details" ref={accountDetails} onKeyDown={event => {
              if (event.key === 'Escape') { event.currentTarget.open = false; event.currentTarget.querySelector('summary')?.focus(); }
            }}>
              <summary className="sh-icon-button" aria-label="Workspace and account details" title="Workspace and account details"><StudioIcon name="details"/></summary>
              <div className="sh-account-panel">
                <p className="sh-account-heading">Your workspace</p>
                <dl>
                  <dt>Workspace</dt><dd>{workspace?.name ?? 'Unavailable'}</dd>
                  <dt>Role</dt><dd>{workspace?.role ?? 'Unavailable'}</dd>
                  <dt>User ID</dt><dd className="sh-user-id">{userId ?? 'Not signed in'}</dd>
                </dl>
              </div>
            </details>
            {userId && <div className="sh-account-avatar"><UserButton/></div>}
          </div>
        </header>

        <main className="sh-content" id="studio-content" tabIndex={-1}>
          {apiError && <p className="sh-service-notice" role="status">The API is currently unavailable. Your workspace details and uploads may be temporarily unavailable.</p>}
          {message && !activeRunId && <p className="sh-service-notice" role="status">{message}</p>}
          {createOpen ? <CreateView products={products} onUpload={openUpload} /> : <>
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
