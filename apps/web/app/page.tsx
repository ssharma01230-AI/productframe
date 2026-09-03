import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/nextjs';
import Link from 'next/link';

export default function Home() {
  const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  return <main className="page">
    <nav><strong><span>P</span> productframe</strong><SignedIn><UserButton /></SignedIn></nav>
    <section className="hero">
      <p className="eyebrow">PRODUCTFRAME / CONTENT STUDIO</p>
      <h1>One product.<br /><em>Everywhere it needs to go.</em></h1>
      <p>Upload it once. Build the full product story from there.</p>
      {clerkConfigured ? <>
        <SignedOut><SignInButton mode="modal"><button className="primary">Sign in to get started →</button></SignInButton></SignedOut>
        <SignedIn><Link href="/studio" className="primary">Create a product →</Link></SignedIn>
      </> : <p className="setup-note">Add your Clerk publishable key to `.env.local` to enable sign-in.</p>}
    </section>
  </main>;
}
