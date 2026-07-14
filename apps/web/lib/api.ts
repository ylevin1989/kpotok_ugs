import type {
  AudienceSegmentCreateInput,
  AudienceSegmentListResponse,
  AudienceSegmentRead,
  BrandListResponse,
  BrandCreateInput,
  BrandUpdateInput,
  BrandRead,
  BriefListResponse,
  BriefRead,
  ContentPlanExportInput,
  ContentPlanGenerateInput,
  ContentPlanListResponse,
  ContentPlanRead,
  ContentScope,
  JobListResponse,
  JobRead,
  LoginResponse,
  MeResponse,
  MediaAssetCreateInput,
  OrganizationMemberCreateInput,
  OrganizationMemberListResponse,
  OrganizationMemberRead,
  OrganizationMemberUpdateInput,
  OrganizationPermissionEventListResponse,
  RegisterInput,
  MediaAssetListResponse,
  MediaAssetRead,
  OrganizationListResponse,
  ProductCreateInput,
  ProductListResponse,
  ProductRead,
  ProductUpdateInput,
  SubscriptionCreateInput,
  SubscriptionListResponse,
  SubscriptionRead,
  SupportUserLookupResponse,
  UsageRecordListResponse,
} from './types';

const DEFAULT_API_BASE_URL = 'https://apiha.uno-ai.pw';

function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_CF_API_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '');
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as T;
}

function authHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
  };
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(accessToken: string): Promise<MeResponse> {
  return apiFetch<MeResponse>('/api/v1/auth/me', {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function register(payload: RegisterInput): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getOrganizations(accessToken: string): Promise<OrganizationListResponse> {
  return apiFetch<OrganizationListResponse>('/api/v1/organizations', {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function getOrganizationMembers(
  accessToken: string,
  organizationId: string,
): Promise<OrganizationMemberListResponse> {
  return apiFetch<OrganizationMemberListResponse>(`/api/v1/organizations/${organizationId}/members`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function createOrganizationMember(
  accessToken: string,
  organizationId: string,
  payload: OrganizationMemberCreateInput,
): Promise<OrganizationMemberRead> {
  return apiFetch<OrganizationMemberRead>(`/api/v1/organizations/${organizationId}/members`, {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function updateOrganizationMember(
  accessToken: string,
  organizationId: string,
  memberId: string,
  payload: OrganizationMemberUpdateInput,
): Promise<OrganizationMemberRead> {
  return apiFetch<OrganizationMemberRead>(`/api/v1/organizations/${organizationId}/members/${memberId}`, {
    method: 'PATCH',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function deleteOrganizationMember(
  accessToken: string,
  organizationId: string,
  memberId: string,
): Promise<void> {
  return fetch(`${getApiBaseUrl()}/api/v1/organizations/${organizationId}/members/${memberId}`, {
    method: 'DELETE',
    headers: {
      ...authHeaders(accessToken),
    },
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }
  });
}

export function getOrganizationPermissionEvents(
  accessToken: string,
  organizationId: string,
): Promise<OrganizationPermissionEventListResponse> {
  return apiFetch<OrganizationPermissionEventListResponse>(`/api/v1/organizations/${organizationId}/permission-events`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function lookupSupportUser(accessToken: string, email: string): Promise<SupportUserLookupResponse> {
  const params = new URLSearchParams({ email });
  return apiFetch<SupportUserLookupResponse>(`/api/v1/support/users?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function getBrands(accessToken: string, organizationId: string): Promise<BrandListResponse> {
  const params = new URLSearchParams({ organization_id: organizationId });
  return apiFetch<BrandListResponse>(`/api/v1/brands?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function createBrand(accessToken: string, payload: BrandCreateInput): Promise<BrandRead> {
  return apiFetch<BrandRead>('/api/v1/brands', {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function updateBrand(accessToken: string, brandId: string, payload: BrandUpdateInput): Promise<BrandRead> {
  return apiFetch<BrandRead>(`/api/v1/brands/${brandId}`, {
    method: 'PATCH',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function generateBrandDna(accessToken: string, brandId: string): Promise<JobRead> {
  return apiFetch<JobRead>(`/api/v1/brands/${brandId}/generate-dna`, {
    method: 'POST',
    headers: authHeaders(accessToken),
  });
}

export function getProducts(
  accessToken: string,
  organizationId: string,
  brandId: string,
): Promise<ProductListResponse> {
  const params = new URLSearchParams({ organization_id: organizationId, brand_id: brandId });
  return apiFetch<ProductListResponse>(`/api/v1/products?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function createProduct(accessToken: string, payload: ProductCreateInput): Promise<ProductRead> {
  return apiFetch<ProductRead>('/api/v1/products', {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function updateProduct(accessToken: string, productId: string, payload: ProductUpdateInput): Promise<ProductRead> {
  return apiFetch<ProductRead>(`/api/v1/products/${productId}`, {
    method: 'PATCH',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function generateProductDna(accessToken: string, productId: string): Promise<JobRead> {
  return apiFetch<JobRead>(`/api/v1/products/${productId}/generate-dna`, {
    method: 'POST',
    headers: authHeaders(accessToken),
  });
}

export function getMediaAssets(
  accessToken: string,
  organizationId: string,
  brandId: string,
  scope?: ContentScope,
  productId?: string | null,
): Promise<MediaAssetListResponse> {
  const params = new URLSearchParams({ organization_id: organizationId, brand_id: brandId });
  if (scope) params.set('scope', scope);
  if (productId) params.set('product_id', productId);
  return apiFetch<MediaAssetListResponse>(`/api/v1/media-assets?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function createMediaAsset(accessToken: string, payload: MediaAssetCreateInput): Promise<MediaAssetRead> {
  return apiFetch<MediaAssetRead>('/api/v1/media-assets', {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function getAudienceSegments(
  accessToken: string,
  organizationId: string,
  brandId: string,
  scope?: ContentScope,
  productId?: string | null,
): Promise<AudienceSegmentListResponse> {
  const params = new URLSearchParams({ organization_id: organizationId, brand_id: brandId });
  if (scope) params.set('scope', scope);
  if (productId) params.set('product_id', productId);
  return apiFetch<AudienceSegmentListResponse>(`/api/v1/audience-segments?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function createAudienceSegment(
  accessToken: string,
  payload: AudienceSegmentCreateInput,
): Promise<AudienceSegmentRead> {
  return apiFetch<AudienceSegmentRead>('/api/v1/audience-segments', {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function getContentPlans(
  accessToken: string,
  organizationId: string,
  brandId: string,
  scope?: ContentScope,
  productId?: string | null,
  audienceSegmentId?: string | null,
): Promise<ContentPlanListResponse> {
  const params = new URLSearchParams({ organization_id: organizationId, brand_id: brandId });
  if (scope) params.set('scope', scope);
  if (productId) params.set('product_id', productId);
  if (audienceSegmentId) params.set('audience_segment_id', audienceSegmentId);
  return apiFetch<ContentPlanListResponse>(`/api/v1/content-plans?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function generateContentPlans(
  accessToken: string,
  payload: ContentPlanGenerateInput,
): Promise<ContentPlanListResponse> {
  return apiFetch<ContentPlanListResponse>('/api/v1/content-plans/generate', {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function exportContentPlans(
  accessToken: string,
  payload: ContentPlanExportInput,
): Promise<{ content: string; contentType: string }> {
  return fetch(`${getApiBaseUrl()}/api/v1/content-plans/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(accessToken),
    },
    body: JSON.stringify(payload),
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }
    return {
      content: await response.text(),
      contentType: response.headers.get('content-type') || 'application/octet-stream',
    };
  });
}

export function listSubscriptions(
  accessToken: string,
  organizationId: string,
): Promise<SubscriptionListResponse> {
  const params = new URLSearchParams({ organization_id: organizationId });
  return apiFetch<SubscriptionListResponse>(`/api/v1/subscriptions?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function upsertSubscription(
  accessToken: string,
  payload: SubscriptionCreateInput,
): Promise<SubscriptionRead> {
  return apiFetch<SubscriptionRead>('/api/v1/subscriptions', {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function getUsageRecords(
  accessToken: string,
  organizationId: string,
): Promise<UsageRecordListResponse> {
  const params = new URLSearchParams({ organization_id: organizationId });
  return apiFetch<UsageRecordListResponse>(`/api/v1/subscriptions/usage?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function getBriefs(
  accessToken: string,
  organizationId: string,
  brandId: string,
): Promise<BriefListResponse> {
  const params = new URLSearchParams({ organization_id: organizationId, brand_id: brandId });
  return apiFetch<BriefListResponse>(`/api/v1/briefs?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function createBrief(
  accessToken: string,
  payload: { organization_id: string; brand_id: string; title: string; content: string },
): Promise<BriefRead> {
  return apiFetch<BriefRead>('/api/v1/briefs', {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function getJobs(
  accessToken: string,
  organizationId: string,
  brandId: string,
  briefId: string,
): Promise<JobListResponse> {
  const params = new URLSearchParams({
    organization_id: organizationId,
    brand_id: brandId,
    brief_id: briefId,
  });
  return apiFetch<JobListResponse>(`/api/v1/jobs?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export function createJob(
  accessToken: string,
  payload: { organization_id: string; brand_id: string; brief_id: string; title: string; execution_profile?: string },
): Promise<JobRead> {
  return apiFetch<JobRead>('/api/v1/jobs', {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}

export function getJob(accessToken: string, jobId: string): Promise<JobRead> {
  return apiFetch<JobRead>(`/api/v1/jobs/${jobId}`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });
}

export async function getJobArtifactText(
  accessToken: string,
  jobId: string,
): Promise<{ content: string; contentType: string }> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/jobs/${jobId}/artifact`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return {
    content: await response.text(),
    contentType: response.headers.get('content-type') || 'application/octet-stream',
  };
}

export async function downloadJobArtifact(accessToken: string, jobId: string): Promise<{ blob: Blob; contentType: string }> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/jobs/${jobId}/artifact`, {
    method: 'GET',
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return {
    blob: await response.blob(),
    contentType: response.headers.get('content-type') || 'application/octet-stream',
  };
}

// ---------- Admin (platform) ----------
export interface AdminOrg { id: string; name: string; slug: string; status: string; brands: number; products: number; members: number; owners: string[]; created_at: string | null; }
export interface AdminUser { id: string; email: string; full_name: string | null; platform_role: string | null; is_active: boolean; organizations: number; created_at: string | null; }

export function adminOverview(accessToken: string): Promise<{ organizations: number; brands: number; products: number; users: number }> {
  return apiFetch('/api/v1/admin/overview', { method: 'GET', headers: authHeaders(accessToken) });
}
export function adminListOrganizations(accessToken: string): Promise<{ items: AdminOrg[] }> {
  return apiFetch('/api/v1/admin/organizations', { method: 'GET', headers: authHeaders(accessToken) });
}
export function adminListUsers(accessToken: string): Promise<{ items: AdminUser[] }> {
  return apiFetch('/api/v1/admin/users', { method: 'GET', headers: authHeaders(accessToken) });
}
export function adminCreateOrganization(accessToken: string, payload: { name: string; slug: string; owner_email: string }): Promise<unknown> {
  return apiFetch('/api/v1/admin/organizations', { method: 'POST', headers: authHeaders(accessToken), body: JSON.stringify(payload) });
}
export function adminCreateBrand(accessToken: string, payload: { organization_id: string; name: string; slug: string }): Promise<unknown> {
  return apiFetch('/api/v1/admin/brands', { method: 'POST', headers: authHeaders(accessToken), body: JSON.stringify(payload) });
}
export function adminAddMember(accessToken: string, payload: { organization_id: string; user_email: string; role: string }): Promise<unknown> {
  return apiFetch('/api/v1/admin/memberships', { method: 'POST', headers: authHeaders(accessToken), body: JSON.stringify(payload) });
}
export function adminSetPlatformRole(accessToken: string, userId: string, platform_role: string | null): Promise<unknown> {
  return apiFetch(`/api/v1/admin/users/${userId}/platform-role`, { method: 'POST', headers: authHeaders(accessToken), body: JSON.stringify({ platform_role }) });
}
