/**
 * Strict TypeScript types for the administrative interface (/admin).
 * Grounded directly in backend Pydantic schemas and MySQL models.
 */

export type AdminRole = 'SUPER_ADMIN' | 'SITE_CURATOR' | 'OPERATOR' | 'VIEWER';

export type DocumentStatus = 'UPLOADED' | 'PARSED' | 'PROCESSED' | 'FAILED';

export type GenerationLifecycleStatus =
  | 'BUILD'
  | 'PARSE'
  | 'CHUNK'
  | 'EMBED'
  | 'INDEX'
  | 'VALIDATED'
  | 'ACTIVE'
  | 'ARCHIVED'
  | 'FAILED';

export type GenerationStage =
  | 'INIT'
  | 'EXTRACTION'
  | 'CHUNKING'
  | 'EMBEDDING'
  | 'INDEXING'
  | 'EVALUATION'
  | 'COMPLETED'
  | 'ERROR';

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: AdminRole;
  is_active: boolean;
  last_login_at?: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface DocumentItem {
  id: string;
  filename: string;
  original_name: string;
  file_size_bytes: number;
  sha256_hash: string;
  mime_type: string;
  status: DocumentStatus;
  page_count: number;
  uploaded_by_admin_id: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface KnowledgeGeneration {
  id: string;
  generation_version: string;
  status: GenerationLifecycleStatus;
  description?: string | null;
  document_count: number;
  chunk_count: number;
  embedding_count: number;
  embedding_model: string;
  is_active: boolean;
  created_by_admin_id: string;
  created_at: string;
  promoted_at?: string | null;
}

export interface GenerationStatusItem {
  id: string;
  generation_id: string;
  stage: GenerationStage;
  progress_pct: number;
  message?: string | null;
  error_details?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface GenerationDetailResponse {
  generation: KnowledgeGeneration;
  stages: GenerationStatusItem[];
}

export interface GenerationListResponse {
  items: KnowledgeGeneration[];
  total: number;
}

export interface PromoteRollbackResponse {
  message: string;
  generation_id: string;
  is_active: boolean;
  promoted_at?: string | null;
}

export interface BuildGenerationPayload {
  document_ids?: string[];
  description?: string;
}

export interface RetrievalCandidate {
  chunk_id: string;
  document_id: string;
  generation_id: string;
  text: string;
  page_number: number;
  section?: string | null;
  source_filename: string;
  dense_rank?: number | null;
  dense_score?: number | null;
  bm25_rank?: number | null;
  bm25_score?: number | null;
  rrf_score?: number | null;
  reranker_score?: number | null;
  final_rank: number;
  metadata_json?: Record<string, unknown>;
}

export interface TimingMetrics {
  dense_ms: number;
  bm25_ms: number;
  fusion_ms: number;
  rerank_ms: number;
  total_ms: number;
}

export interface RetrievalDiagnosticRequest {
  query: string;
  top_k?: number;
  dense_top_k?: number;
  bm25_top_k?: number;
  rerank_candidates?: number;
  enable_reranker?: boolean;
  filter_noise?: boolean;
  suppress_duplicates?: boolean;
}

export interface RetrievalDiagnosticResponse {
  query: string;
  normalized_query: string;
  active_generation_id?: string | null;
  active_generation_version?: string | null;
  dense_candidates_count: number;
  bm25_candidates_count: number;
  fused_candidates_count: number;
  final_count: number;
  results: RetrievalCandidate[];
  timings_ms: TimingMetrics;
  diagnostic_notes: string[];
}

export interface TranslationRegistryItem {
  id: string;
  source_lang: string;
  target_lang: string;
  engine: string;
  package_version: string;
  is_active: boolean;
}

export interface TranslationRegistryResponse {
  provider_engine: string;
  provider_healthy: boolean;
  supported_languages: string[];
  translations: TranslationRegistryItem[];
}

export interface HealthProbeResponse {
  status: 'healthy' | 'degraded';
  api_version: string;
  app_version: string;
  profile: string;
  timestamp: string;
  subsystems: {
    app: string;
    database: string;
  };
}
