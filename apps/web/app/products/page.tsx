import { auth } from '@clerk/nextjs/server';
import ProductLibrary from './ProductLibrary';
import type { GalleryAsset, ProductDetail, ProductSummary } from './library-types';

type LibraryParams = { view?: string; product?: string };

export default async function ProductsPage({ searchParams }: { searchParams: Promise<LibraryParams> }) {
  const params = await searchParams;
  const mode = params.view === 'gallery' ? 'gallery' : 'catalogue';
  const selectedId = mode === 'catalogue' ? params.product : undefined;
  const { userId, getToken } = await auth();
  const token = await getToken();
  let products: ProductSummary[] = [];
  let detail: ProductDetail | null = null;
  let gallery: GalleryAsset[] = [];
  let error = '';
  let detailError = '';
  const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

  if (token) {
    const headers = { Authorization: `Bearer ${token}` };
    const [listResult, detailResult] = await Promise.allSettled([
      fetch(`${base}/products`, { headers, cache: 'no-store' }),
      selectedId ? fetch(`${base}/products/${encodeURIComponent(selectedId)}`, { headers, cache: 'no-store' }) : Promise.resolve(null),
    ]);
    if (listResult.status === 'fulfilled' && listResult.value.ok) {
      products = await listResult.value.json();
    } else {
      error = 'Your product library could not be loaded. Please try again.';
    }
    if (selectedId) {
      if (detailResult.status === 'fulfilled' && detailResult.value?.ok) {
        detail = await detailResult.value.json();
      } else {
        detailError = detailResult.status === 'fulfilled' && detailResult.value?.status === 404
          ? 'This product is no longer available in your workspace.'
          : 'This product folder could not be loaded. Please try again.';
      }
    }
    if (mode === 'gallery' && !error) {
      // Only products with persisted generations need a detail read. Uploads never enter Gallery.
      const results = await Promise.allSettled(products.filter(product => product.generated_count > 0).map(async product => {
        const response = await fetch(`${base}/products/${encodeURIComponent(product.id)}`, { headers, cache: 'no-store' });
        if (!response.ok) throw new Error('Generation lookup failed');
        const folder: ProductDetail = await response.json();
        return folder.generated_assets.filter(asset => asset.status === 'approved').map(asset => ({ ...asset, product_id: product.id, product_name: product.name }));
      }));
      gallery = results.flatMap(result => result.status === 'fulfilled' ? result.value : []);
      if (results.some(result => result.status === 'rejected')) error = 'Some approved outputs could not be loaded. Please try again.';
    }
  } else {
    error = 'Sign in to view your product library.';
  }

  return <ProductLibrary initial={products} userId={userId} mode={mode} selectedId={selectedId} detail={detail} gallery={gallery} loadError={error} detailError={detailError}/>;
}
