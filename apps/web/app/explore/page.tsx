import { auth } from '@clerk/nextjs/server';
import ExploreLibrary from './ExploreLibrary';

export default async function ExplorePage() {
  const { userId } = await auth();
  return <ExploreLibrary userId={userId} />;
}
