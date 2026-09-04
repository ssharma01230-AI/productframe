export const MAX_UPLOAD_IMAGES = 50;
export const MAX_UPLOAD_BYTES = 500_000_000;
export const UPLOAD_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

type UploadFile = { name: string; type: string; size: number };

export function validateUploadImages(files: readonly UploadFile[]): string | null {
  if (!files.length) return 'Choose at least one image to continue.';
  if (files.length > MAX_UPLOAD_IMAGES) return 'Choose up to 50 images at a time.';
  if (files.some(file => !UPLOAD_IMAGE_TYPES.includes(file.type))) return 'Please use JPG, PNG or WebP images.';
  if (files.some(file => file.size === 0)) return 'One of these files is empty. Remove it and choose another image.';
  if (files.reduce((total, file) => total + file.size, 0) > MAX_UPLOAD_BYTES) return 'Keep your selected images under 500 MB in total.';
  return null;
}
