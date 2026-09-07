export type MediaEvidence = {
  views?: string[];
  evidence?: string[];
};

export type SourceUpload = {
  id: string;
  filename: string;
  content_type: string;
  image_url: string;
  created_at: string;
  media_evidence?: MediaEvidence | null;
};

export type GeneratedAsset = {
  id: string;
  name: string;
  filename: string;
  content_type: string;
  image_url: string;
  created_at: string;
  status: 'pending' | 'generating' | 'ready' | 'approved' | 'rejected' | 'failed';
};

export type ProductSummary = {
  id: string;
  name: string;
  image_url: string | null;
  category: string | null;
  created_at: string;
  upload_count: number;
  generated_count: number;
  preview_images: { id: string; image_url: string; filename: string; media_evidence?: MediaEvidence | null }[];
};

export type ProductDetail = {
  id: string;
  name: string;
  category: string | null;
  created_at: string;
  uploads: SourceUpload[];
  generated_assets: GeneratedAsset[];
};

export type GalleryAsset = GeneratedAsset & { product_id: string; product_name: string };
export type LibraryMode = 'catalogue' | 'gallery';
