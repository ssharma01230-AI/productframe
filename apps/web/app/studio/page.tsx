import { UserButton } from '@clerk/nextjs';
import { auth } from '@clerk/nextjs/server';
import Link from 'next/link';
import ProductForm from './ProductForm';

export default async function StudioPage({ searchParams }: { searchParams: Promise<{ message?: string }> }) {
  const { message } = await searchParams;
  const { userId, getToken } = await auth();
  const token = await getToken();
  let workspace: { name: string; role: string } | null = null;
  let apiError = false;
  if (token) {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/workspaces/current`, {
        headers: { Authorization: `Bearer ${token}` }, cache: 'no-store',
      });
      if (response.ok) workspace = await response.json();
      else apiError = true;
    } catch { apiError = true; }
  }
  return <main className="page">
    <nav><strong><span>P</span> productframe</strong><UserButton /></nav>
    <section className="hero">
      <p className="eyebrow">STUDIO</p>
      <h1>Welcome back.</h1>
      <p>Your authenticated workspace is ready to connect to the ProductFrame API.</p>
      <small>User: {userId}</small>
      {workspace && <p className="workspace-card">Workspace: <strong>{workspace.name}</strong><br />Role: {workspace.role}</p>}
      {apiError && <p className="setup-note">The API could not be reached yet.</p>}
      <ProductForm message={message} />
      <br /><Link href="/" className="back-link">← Back home</Link>
    </section>
  </main>;
}
