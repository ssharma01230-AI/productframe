/** Typed contract for the Ecommerce generation workflow. */

export type GenerationProgress = {
  stage: string;
  message: string | null;
  completed: number;
  total: number;
  percent: number;
  completed_jobs?: number;
  failed_jobs?: number;
  active_jobs?: number;
};

export type GenerationJobStatus =
  | 'pending'
  | 'generating'
  | 'awaiting_review'
  | 'validating'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type GenerationRunStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'partially_failed'
  | 'cancelled';

export type GenerationPresentation = 'male' | 'female' | 'unisex';

export type GenerationSelection = {
  product_id: string;
  template_id: string;
  channel: 'ecommerce';
  presentation?: GenerationPresentation;
};

export type GenerationRunRequest = {
  selections: GenerationSelection[];
  // Legacy fields remain optional for older API clients.
  product_id?: string;
  template_id?: string;
  channel?: 'ecommerce';
};

export type GenerationRunResponse = {
  run_id: string;
  job_id: string;
  status: GenerationRunStatus;
  total_jobs: number;
  graph_thread_id: string;
  progress?: GenerationProgress;
};

export type GenerationAsset = {
  id: string;
  filename: string;
  content_type: string;
  status: 'ready' | 'approved' | 'rejected' | 'failed';
  image_url: string;
};

export type GenerationProduct = {
  id: string;
  name: string;
  category: string | null;
  image_url: string | null;
};

export type GenerationJobResponse = {
  id: string;
  run_id: string;
  status: GenerationJobStatus;
  template_id: string;
  graph_thread_id: string;
  attempt_count: number;
  preview_url: string | null;
  error_message: string | null;
  template_name: string;
  template_channel: string;
  review_decision: 'approved' | 'rejected' | null;
  product: GenerationProduct;
  asset: GenerationAsset | null;
  progress?: GenerationProgress;
};

export type GenerationReviewRequest = {
  approved: boolean;
};

export type GenerationDecisionRequest = {
  decision: 'approved' | 'rejected';
};

export type GenerationRunCounts = {
  products: number;
  in_progress: number;
  ready: number;
  reviewed: number;
  approved: number;
  rejected: number;
  failed: number;
};

export type GenerationRunDetail = {
  id: string;
  status: GenerationRunStatus;
  total_jobs: number;
  created_at: string;
  progress: GenerationProgress;
  counts: GenerationRunCounts;
  jobs: GenerationJobResponse[];
};

/** Backend readiness response used before generation submission. */
export type OutputReadiness = {
  template_id: string;
  status: 'ready' | 'needs_image';
  required_evidence: string[];
  missing_evidence: string[];
};

export type OutputReadinessResponse = {
  product_id: string;
  templates: OutputReadiness[];
};
