import { auth } from '@clerk/nextjs/server';
import StudioHome from './StudioHome';
import RunReview from './RunReview';
import type { OutputProduct } from './OutputSelection';

type AnalysisResults = { id: string; status: string; total_images: number; processed_images: number; unique_product_count: number; progress: { stage: string; message: string | null; completed: number; total: number; percent: number }; images: { id: string; image_number: number; filename: string | null; image_url: string | null; status: string; passed: boolean | null; product_number: number | null; rejection_reason: string | null }[]; products: { id: string; final_product_id: string | null; product_number: number; product_name: string; category: string; product_type: string; colours: string; materials: string; features: string[]; description: string; confidence: number; confirmation_status: string }[] };

export default async function StudioPage({ searchParams }: { searchParams: Promise<{ message?: string; job_id?: string; image_count?: string; view?: string; step?: string; product?: string | string[]; run?: string }> }) {
  const { message, job_id: jobId, image_count: imageCount, view, step, product, run } = await searchParams;
  const { userId, getToken } = await auth();
  const token = await getToken();
  let workspace: { name: string; role: string } | null = null;
  let results: AnalysisResults | null = null;
  let apiError = false;
  let products: OutputProduct[] = [];
  if (token) {
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
      const response = await fetch(`${base}/workspaces/current`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
      if (response.ok) workspace = await response.json(); else apiError = true;
      const productsResponse = await fetch(`${base}/products`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
      if (productsResponse.ok) products = await productsResponse.json(); else apiError = true;
      if (jobId) {
        const resultResponse = await fetch(`${base}/analysis-jobs/${jobId}/results`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
        if (resultResponse.ok) results = await resultResponse.json();
      }
    } catch { apiError = true; }
  }
  const requestedProductIds = new Set(Array.isArray(product) ? product : product ? [product] : []);
  const selectedProductIds = products.filter(item => requestedProductIds.has(item.id)).map(item => item.id);
  return <>
    <StudioHome workspace={workspace} userId={userId} apiError={apiError} message={message} activeRunId={jobId} products={products} initialCreate={view === 'create'} initialSelectedIds={selectedProductIds} initialOutputStep={view === 'create' && step === 'outputs'} initialGenerationRunId={view === 'create' && step === 'generation' ? run : undefined} />
    {jobId && <RunReview jobId={jobId} imageCount={Number(imageCount ?? results?.total_images ?? 0)} initial={results} />}
  </>;
}
