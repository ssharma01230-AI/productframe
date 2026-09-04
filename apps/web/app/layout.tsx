import { ClerkProvider } from '@clerk/nextjs';
import type { Metadata } from 'next';
import { DM_Sans, Playfair_Display } from 'next/font/google';
import './globals.css';

const reviewSans = DM_Sans({ subsets: ['latin'], weight: ['400', '500', '600', '700'], variable: '--font-pf-sans', display: 'swap' });
const reviewDisplay = Playfair_Display({ subsets: ['latin'], weight: ['500', '600'], variable: '--font-pf-display', display: 'swap' });

export const metadata: Metadata = { title: 'ProductFrame', description: 'Product content studio' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const content = <html lang="en" className={`${reviewSans.variable} ${reviewDisplay.variable}`}><body>{children}</body></html>;
  return publishableKey ? <ClerkProvider publishableKey={publishableKey}>{content}</ClerkProvider> : content;
}
