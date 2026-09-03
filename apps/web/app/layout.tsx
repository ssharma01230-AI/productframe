import { ClerkProvider } from '@clerk/nextjs';
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'ProductFrame', description: 'Product content studio' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const content = <html lang="en"><body>{children}</body></html>;
  return publishableKey ? <ClerkProvider publishableKey={publishableKey}>{content}</ClerkProvider> : content;
}
