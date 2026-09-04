import { UserButton } from '@clerk/nextjs';
import { auth } from '@clerk/nextjs/server';
import Link from 'next/link';
import ProductLibrary from './ProductLibrary';

type Product = { id: string; name: string; image_url: string | null };

export default async function ProductsPage() {
  const { getToken } = await auth();
  const token = await getToken();
  let products: Product[] = [];
  let error = false;
  if (token) {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/products`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
      if (response.ok) products = await response.json(); else error = true;
    } catch { error = true; }
  }

  return <main className="library-shell">
    <aside className="library-sidebar">
      <Link href="/" className="brand"><span>P</span> productframe</Link>
      <nav><Link href="/studio">⌂ <span>Home</span></Link><Link className="active" href="/products">▦ <span>Products</span></Link><Link href="/studio">⌂ <span>Brand</span></Link><Link href="/studio">◇ <span>Packs</span></Link></nav>
      <div className="library-bottom"><Link href="/studio">? <span>Help</span></Link><div className="account"><UserButton /><span>Studio</span></div></div>
    </aside>
    <section className="library-main">
      <header className="library-topbar"><span>Studio / <b>Product content</b></span><div className="top-user"><UserButton /></div></header>
      <div className="library-view">
        <div className="library-heading"><div><div className="eyebrow">PRODUCT CATALOGUE</div><h1>Choose the moments worth making</h1></div><Link className="dark-button" href="/studio">＋ New product</Link></div>
        {error && <p className="error-note">The product library could not be loaded.</p>}
        <ProductLibrary initial={products} />
      </div>
    </section>
  </main>;
}
