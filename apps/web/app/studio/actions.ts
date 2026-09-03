'use server';

import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';

const api = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function createProduct(formData: FormData) {
  const { getToken } = await auth();
  const token = await getToken();
  const name = String(formData.get('name') ?? '').trim();
  const file = formData.get('image');
  if (!token) redirect('/studio?message=Your sign-in session has expired.');
  if (!name || !(file instanceof File) || !file.size) redirect('/studio?message=Please enter a name and choose an image.');

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  const productResponse = await fetch(`${api}/products`, { method: 'POST', headers, body: JSON.stringify({ name }) });
  if (!productResponse.ok) redirect(`/studio?message=Could not save product (${productResponse.status}).`);
  const product = await productResponse.json();
  const uploadResponse = await fetch(`${api}/products/${product.id}/source-assets/upload-url`, {
    method: 'POST', headers, body: JSON.stringify({ filename: file.name, content_type: file.type }),
  });
  if (!uploadResponse.ok) redirect(`/studio?message=Could not prepare image upload (${uploadResponse.status}).`);
  const upload = await uploadResponse.json();
  const putResponse = await fetch(upload.upload_url, { method: 'PUT', headers: { 'Content-Type': file.type }, body: await file.arrayBuffer() });
  redirect(`/studio?message=${encodeURIComponent(putResponse.ok ? 'Product and image saved.' : 'Product saved, but image upload failed.')}`);
}
