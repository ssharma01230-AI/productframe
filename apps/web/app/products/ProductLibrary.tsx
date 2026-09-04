'use client';

import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

type Product = { id:string; name:string; image_url:string|null };
export default function ProductLibrary({ initial }: { initial:Product[] }) {
  const [products,setProducts] = useState(initial);
  const [error,setError] = useState('');
  const { getToken } = useAuth();
  const router = useRouter();
  async function remove(product:Product) {
    if (!window.confirm(`Delete “${product.name}” from your Product Library? This cannot be undone.`)) return;
    const token = await getToken();
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/products/${product.id}`, { method:'DELETE', headers:{ Authorization:`Bearer ${token}` } });
    if (!response.ok) { setError('The product could not be deleted. Please try again.'); return; }
    setProducts(items => items.filter(item => item.id !== product.id)); router.refresh();
  }
  return <><div className="product-shelf"><a className="upload-card" href="/studio"><span className="upload-plus">＋</span><b>Upload a product</b><small>Drop an image or browse</small></a>{products.map(product => <article className="real-product-card" key={product.id}><a href="/studio"><div className="real-product-photo">{product.image_url ? <img src={product.image_url} alt={product.name} /> : <span>No image</span>}</div><div className="real-product-info"><div><b>{product.name}</b><span className="product-status"><i />Ready</span></div><small>Source images</small></div></a><button className="delete-product" onClick={() => remove(product)} aria-label={`Delete ${product.name}`} title="Delete product">×</button></article>)}</div>{error && <p className="error-note" role="alert">{error}</p>}<div className="library-footer"><span>{products.length} approved product{products.length === 1 ? '' : 's'} in Studio</span><span>Last synced just now ↗</span></div></>;
}
