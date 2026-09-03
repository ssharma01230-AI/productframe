import { UserButton } from '@clerk/nextjs';
import { auth } from '@clerk/nextjs/server';
import Link from 'next/link';

export default async function StudioPage() {
  const { userId } = await auth();
  return <main className="page">
    <nav><strong><span>P</span> productframe</strong><UserButton /></nav>
    <section className="hero">
      <p className="eyebrow">STUDIO</p>
      <h1>Welcome back.</h1>
      <p>Your authenticated workspace is ready to connect to the ProductFrame API.</p>
      <small>User: {userId}</small>
      <br /><Link href="/" className="back-link">← Back home</Link>
    </section>
  </main>;
}
