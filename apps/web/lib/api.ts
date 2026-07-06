import type {
  BrandListResponse,
  BriefListResponse,
  BriefRead,
  JobListResponse,
  JobRead,
  LoginResponse,
  MeResponse,
  OrganizationListResponse,
  ProductCreateInput,
  ProductListResponse,
  ProductRead,
  ProductUpdateInput,
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

export function getOrganizations(accessToken: string): Promise<OrganizationListResponse> {
  return apiFetch<OrganizationListResponse>('/api/v1/organizations', {
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
