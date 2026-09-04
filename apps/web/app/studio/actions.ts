'use server';

import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import { validateUploadImages } from './upload-constraints';

const api = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function createProductAnalysisJob(formData: FormData) {
  const { getToken } = await auth();
  const token = await getToken();
  const name = String(formData.get('name') ?? '').trim() || 'Unconfirmed product upload';
  const files = formData.getAll('images').filter((value): value is File => value instanceof File);
  if (!token) redirect('/studio?message=Your sign-in session has expired.');
  const validation = validateUploadImages(files);
  if (validation) redirect('/studio?message=' + encodeURIComponent(validation));

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  const productResponse = await fetch(`${api}/products`, { method: 'POST', headers, body: JSON.stringify({ name }) });
  if (!productResponse.ok) redirect(`/studio?message=Could not create the upload (${productResponse.status}).`);
  const product = await productResponse.json();
  const assetIds: string[] = [];
  for (const file of files) {
    const uploadResponse = await fetch(`${api}/products/${product.id}/source-assets/upload-url`, {
      method: 'POST', headers, body: JSON.stringify({ filename: file.name, content_type: file.type }),
    });
    if (!uploadResponse.ok) redirect(`/studio?message=Could not prepare ${file.name} for upload.`);
    const upload = await uploadResponse.json();
    const putResponse = await fetch(upload.upload_url, { method: 'PUT', headers: { 'Content-Type': file.type }, body: await file.arrayBuffer() });
    if (!putResponse.ok) redirect(`/studio?message=${encodeURIComponent(`Could not upload ${file.name}.`)}`);
    assetIds.push(upload.asset_id);
  }
  const jobResponse = await fetch(`${api}/analysis-jobs`, { method: 'POST', headers, body: JSON.stringify({ source_asset_ids: assetIds }) });
  if (!jobResponse.ok) redirect('/studio?message=Images saved, but analysis could not be started.');
  const job = await jobResponse.json();
  redirect(`/studio?job_id=${job.id}&image_count=${files.length}&message=${encodeURIComponent(`${files.length} image${files.length === 1 ? '' : 's'} uploaded. Analysis is now queued for screening, grouping and review.`)}`);
}
