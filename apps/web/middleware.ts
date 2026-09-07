import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isProtectedRoute = createRouteMatcher(['/studio(.*)']);

export default clerkMiddleware(async (auth, request) => {
  if (isProtectedRoute(request)) {
    // Client-side navigations can be classified as non-document requests by
    // Clerk. Without an explicit fallback, auth.protect() turns those signed-
    // out requests into a 404 instead of returning the user to sign-in.
    await auth.protect({ unauthenticatedUrl: new URL('/', request.url).toString() });
  }
});

export const config = {
  matcher: ['/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|png|jpg|jpeg|gif|svg|ico|webp|woff2?|ttf)).*)', '/(api|trpc)(.*)'],
};
