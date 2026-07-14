export interface UserRead {
  id: string;
  email: string;
  full_name: string | null;
  platform_role: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MembershipRead {
  organization_id: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserRead;
}

export interface MeResponse {
  user: UserRead;
  memberships: MembershipRead[];
}

export interface RegisterInput {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface OrganizationMemberRead {
  id: string;
  user_id: string;
  email: string;
  full_name: string | null;
  role: string;
  created_at: string;
}

export interface OrganizationMemberListResponse {
  items: OrganizationMemberRead[];
}

export interface OrganizationMemberCreateInput {
  email: string;
  role: string;
}

export interface OrganizationMemberUpdateInput {
  role: string;
}

export interface OrganizationPermissionEventRead {
  id: string;
  organization_id: string;
  actor_user_id: string;
  actor_membership_role: string;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface OrganizationPermissionEventListResponse {
  items: OrganizationPermissionEventRead[];
}

export interface SupportMembershipRead {
  organization_id: string;
  organization_name: string;
  organization_slug: string;
  organization_status: string;
  role: string;
  created_at: string;
}

export interface SupportUserLookupResponse {
  user: UserRead;
  memberships: SupportMembershipRead[];
}

export interface OrganizationRead {
  id: string;
  name: string;
  slug: string;
  status: string;
  membership_role: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationListResponse {
  items: OrganizationRead[];
}

export type ContentScope = 'brand' | 'product' | 'campaign' | 'comparison';

export interface BrandRead {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  status: string;
  dna_json: Record<string, unknown> | null;
  positioning: string | null;
  tone_of_voice: string[] | null;
  mission: string | null;
  values: string[] | null;
  forbidden_claims: string[] | null;
  allowed_claims: string[] | null;
  competitors: string[] | null;
  good_examples: string[] | null;
  bad_examples: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface BrandListResponse {
  items: BrandRead[];
}

export interface BrandCreateInput {
  organization_id: string;
  name: string;
  slug: string;
  status?: string;
  positioning?: string | null;
  tone_of_voice?: string[] | null;
  mission?: string | null;
  values?: string[] | null;
  forbidden_claims?: string[] | null;
  allowed_claims?: string[] | null;
  competitors?: string[] | null;
  good_examples?: string[] | null;
  bad_examples?: string[] | null;
}

export interface BrandUpdateInput {
  name?: string;
  slug?: string;
  status?: string;
  positioning?: string | null;
  tone_of_voice?: string[] | null;
  mission?: string | null;
  values?: string[] | null;
  forbidden_claims?: string[] | null;
  allowed_claims?: string[] | null;
  competitors?: string[] | null;
  good_examples?: string[] | null;
  bad_examples?: string[] | null;
}

export interface ProductRead {
  id: string;
  organization_id: string;
  brand_id: string;
  sku: string;
  name: string;
  category: string;
  description: string;
  features: string[];
  benefits: string[];
  proofs: string[];
  objections: string[];
  restrictions: string[];
  dna_json: Record<string, unknown> | null;
  status: string;
  readiness_score: number;
  created_at: string;
  updated_at: string;
}

export interface ProductListResponse {
  items: ProductRead[];
}

export interface ProductCreateInput {
  organization_id: string;
  brand_id: string;
  sku: string;
  name: string;
  category: string;
  description: string;
  features?: string[];
  benefits?: string[];
  proofs?: string[];
  objections?: string[];
  restrictions?: string[];
  status?: string;
  readiness_score?: number;
}

export interface ProductUpdateInput {
  sku?: string;
  name?: string;
  category?: string;
  description?: string;
  features?: string[];
  benefits?: string[];
  proofs?: string[];
  objections?: string[];
  restrictions?: string[];
  status?: string;
  readiness_score?: number;
}

export interface MediaAssetRead {
  id: string;
  organization_id: string;
  brand_id: string;
  product_id: string | null;
  scope: ContentScope;
  name: string;
  description: string;
  asset_key: string;
  source_url: string | null;
  content_type: string;
  size_bytes: number | null;
  checksum: string | null;
  created_at: string;
  updated_at: string;
}

export interface MediaAssetListResponse {
  items: MediaAssetRead[];
}

export interface MediaAssetCreateInput {
  organization_id: string;
  brand_id: string;
  product_id?: string | null;
  scope: ContentScope;
  name: string;
  description: string;
  asset_key: string;
  source_url?: string | null;
  content_type: string;
  size_bytes?: number | null;
  checksum?: string | null;
}

export interface AudienceSegmentRead {
  id: string;
  organization_id: string;
  brand_id: string;
  product_id: string | null;
  scope: ContentScope;
  name: string;
  description: string;
  pain_points: string[];
  goals: string[];
  objections: string[];
  keywords: string[];
  created_at: string;
  updated_at: string;
}

export interface AudienceSegmentListResponse {
  items: AudienceSegmentRead[];
}

export interface AudienceSegmentCreateInput {
  organization_id: string;
  brand_id: string;
  product_id?: string | null;
  scope: ContentScope;
  name: string;
  description: string;
  pain_points?: string[];
  goals?: string[];
  objections?: string[];
  keywords?: string[];
}

export interface ContentPlanRead {
  id: string;
  organization_id: string;
  brand_id: string;
  product_id: string | null;
  audience_segment_id: string | null;
  scope: ContentScope;
  date: string;
  title: string;
  platform: string;
  content_type: string;
  goal: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ContentPlanListResponse {
  items: ContentPlanRead[];
}

export interface ContentPlanGenerateInput {
  organization_id: string;
  brand_id: string;
  product_id?: string | null;
  audience_segment_id?: string | null;
  scope: ContentScope;
  start_date: string;
  end_date: string;
  title_prefix?: string;
  platform: string;
  content_type: string;
  goal: string;
  status?: string;
}

export interface ContentPlanExportInput {
  organization_id: string;
  brand_id: string;
  scope?: ContentScope | null;
  product_id?: string | null;
  audience_segment_id?: string | null;
  format?: 'csv' | 'json';
}

export interface SubscriptionRead {
  id: string;
  organization_id: string;
  plan_name: string;
  monthly_content_plan_limit: number;
  monthly_export_limit: number;
  is_active: boolean;
  current_period_start: string;
  current_period_end: string;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionCreateInput {
  organization_id: string;
  plan_name: string;
  monthly_content_plan_limit: number;
  monthly_export_limit: number;
  is_active: boolean;
  current_period_start: string;
  current_period_end: string;
}

export interface SubscriptionListResponse {
  items: SubscriptionRead[];
}

export interface UsageRecordRead {
  id: string;
  organization_id: string;
  subscription_id: string | null;
  metric: string;
  quantity: number;
  window_start: string;
  window_end: string;
  metadata_json: string | null;
  created_at: string;
}

export interface UsageRecordListResponse {
  items: UsageRecordRead[];
}

export interface BriefRead {
  id: string;
  organization_id: string;
  brand_id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface BriefListResponse {
  items: BriefRead[];
}

export interface JobScopeRead {
  organization_id: string;
  brand_id: string;
  brief_id: string;
}

export interface JobExecutionTraceCompactSummaryRead {
  current_stage?: string | null;
  final_status?: string | null;
  attempt_number?: number | null;
  dominant_stage_name?: string | null;
  heartbeat_count?: number | null;
  reclaim_count?: number | null;
  has_progress?: boolean | null;
  progress_span_percent?: number | null;
  last_stage_label?: string | null;
  average_progress_percent?: number | null;
  unique_transition_tag_count?: number | null;
  latest_transition_tag?: string | null;
  first_transition_tag?: string | null;
  transition_tag_total_count?: number | null;
  progress_history_sample_count?: number | null;
  first_progress_percent?: number | null;
  unique_stage_count?: number | null;
  worker_count?: number | null;
  worker_metadata_key_count?: number | null;
  latest_worker_metadata_keys?: string[] | null;
  max_progress_percent?: number | null;
  stage_label_entry_count?: number | null;
}

export interface JobExecutionTraceRead {
  final_status?: string | null;
  failure_reason?: string | null;
  failure_stage?: string | null;
  last_progress?: {
    stage_name?: string | null;
    stage_label?: string | null;
    progress_percent?: number | null;
    progress_message?: string | null;
    transition_tag?: string | null;
    progress_sequence?: number | null;
  } | null;
  trace_compact_summary?: JobExecutionTraceCompactSummaryRead | null;
}

export interface InternalRolePlanItemRead {
  role_id: string;
  label: string;
  purpose: string;
}

export interface JobRead {
  id: string;
  organization_id: string;
  brand_id: string;
  brief_id: string;
  kind: string;
  target_brand_id: string | null;
  target_product_id: string | null;
  target_content_item_id: string | null;
  target_ticket_id: string | null;
  scope: JobScopeRead;
  execution_profile: string;
  internal_role_plan: InternalRolePlanItemRead[];
  execution_trace: JobExecutionTraceRead | null;
  title: string;
  status: string;
  worker_id: string | null;
  attempt_count: number;
  lease_expires_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  output_text: string | null;
  output_artifact_key: string | null;
  output_artifact_url: string | null;
  output_artifact_content_type: string | null;
  output_artifact_size_bytes: number | null;
  output_artifact_etag: string | null;
  last_stage: string | null;
  last_heartbeat_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobListResponse {
  items: JobRead[];
}
