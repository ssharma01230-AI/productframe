'use client';

import { UserButton } from '@clerk/nextjs';
import Link from 'next/link';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import StudioIcon from '../studio/StudioIcon';
import '../studio/studio-home.css';

type LibraryShellProps = {
  breadcrumb?: string;
  userId: string | null;
  children: ReactNode;
  active?: 'library' | 'explore';
};

function LibraryNavigation({ onNavigate, active = 'library' }: { onNavigate?: () => void; active?: 'library' | 'explore' }) {
  return <>
    <Link className="sh-nav-item" href="/studio" prefetch={false} onClick={onNavigate}><StudioIcon name="home"/>Home</Link>
    <Link className="sh-nav-item" href="/studio?view=create" prefetch={false} onClick={onNavigate}><StudioIcon name="plus"/>Create</Link>
    <Link className={`sh-nav-item${active === 'library' ? ' sh-nav-active' : ''}`} href="/products" prefetch={false} aria-current={active === 'library' ? 'page' : undefined} onClick={onNavigate}><StudioIcon name="folder"/>Product library</Link>
    <Link className={`sh-nav-item${active === 'explore' ? ' sh-nav-active' : ''}`} href="/explore" prefetch={false} aria-current={active === 'explore' ? 'page' : undefined} onClick={onNavigate}><StudioIcon name="compass"/>Explore</Link>
    <button className="sh-nav-item" type="button" disabled title="Settings are not available yet"><StudioIcon name="settings"/>Settings</button>
  </>;
}

export default function LibraryShell({ breadcrumb = 'Catalogue', userId, children, active = 'library' }: LibraryShellProps) {
  const mobileNavigation = useRef<HTMLDetailsElement>(null);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  useEffect(() => {
    function dismissOutside(event: PointerEvent) {
      const navigation = mobileNavigation.current;
      if (navigation?.open && event.target instanceof Node && !navigation.contains(event.target)) navigation.open = false;
    }
    function dismissWithEscape(event: KeyboardEvent) {
      const navigation = mobileNavigation.current;
      if (event.key !== 'Escape' || !navigation?.open) return;
      navigation.open = false;
      navigation.querySelector('summary')?.focus();
    }
    document.addEventListener('pointerdown', dismissOutside);
    document.addEventListener('keydown', dismissWithEscape);
    return () => {
      document.removeEventListener('pointerdown', dismissOutside);
      document.removeEventListener('keydown', dismissWithEscape);
    };
  }, []);

  const closeMobileNavigation = () => {
    const navigation = mobileNavigation.current;
    if (navigation) navigation.open = false;
  };

  return <div className="sh-shell pl-shell">
    <a className="sh-skip-link" href="#product-library-content">Skip to content</a>
    <aside className="sh-sidebar" aria-label="Studio sidebar">
      <Link className="sh-logo" href="/studio" prefetch={false} aria-label="ProductFrame home"><span className="sh-logo-mark">P</span><span>productframe</span></Link>
      <nav className="sh-navigation" aria-label="Main navigation"><LibraryNavigation active={active}/></nav>
    </aside>

    <div className="sh-main">
      <header className="sh-topbar">
        <div className="sh-topbar-left">
          <details className="sh-mobile-navigation" ref={mobileNavigation}>
            <summary className="sh-icon-button" aria-label="Open navigation"><StudioIcon name="menu"/></summary>
            <nav className="sh-mobile-navigation-panel" aria-label="Mobile navigation"><LibraryNavigation active={active} onNavigate={closeMobileNavigation}/></nav>
          </details>
          <div className="sh-crumb">Studio / <strong>{breadcrumb}</strong></div>
        </div>
        {userId && mounted && <div className="sh-top-actions"><div className="sh-account-avatar"><UserButton/></div></div>}
      </header>
      <main className="pl-content" id="product-library-content" tabIndex={-1}>{children}</main>
    </div>
  </div>;
}
