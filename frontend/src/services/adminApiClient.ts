/**
 * Typed Administrative API Client with automated token rotation and single-flight refresh mutex.
 * Consumes existing Phase 4, Phase 5, Phase 6, Phase 7, Phase 11, and Phase 2 endpoints.
 */

import { ApiError } from './apiClient';
import {
  REFRESH_TOKEN_SESSION_KEY,
  useAdminAuthStore,
} from '../stores/adminAuthStore';
import {
  AdminUser,
  BuildGenerationPayload,
  DocumentItem,
  DocumentListResponse,
  GenerationDetailResponse,
  GenerationListResponse,
  HealthProbeResponse,
  KnowledgeGeneration,
  PromoteRollbackResponse,
  RetrievalDiagnosticRequest,
  RetrievalDiagnosticResponse,
  TokenResponse,
  TranslationRegistryResponse,
} from '../types/admin';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Single-flight refresh Promise to prevent multiple simultaneous refresh requests
let inFlightRefreshPromise: Promise<string | null> | null = null;

async function executeTokenRefresh(): Promise<string | null> {
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_SESSION_KEY);
  if (!refreshToken) {
    useAdminAuthStore.getState().clearAuth();
    return null;
  }

  try {
    const res = await fetch(`${API_BASE}/admin/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      useAdminAuthStore.getState().clearAuth();
      return null;
    }

    const data: TokenResponse = await res.json();
    useAdminAuthStore.getState().setAccessToken(data.access_token);
    try {
      sessionStorage.setItem(REFRESH_TOKEN_SESSION_KEY, data.refresh_token);
    } catch {
      // Ignore sessionStorage errors
    }
    return data.access_token;
  } catch {
    useAdminAuthStore.getState().clearAuth();
    return null;
  } finally {
    inFlightRefreshPromise = null;
  }
}

/**
 * Authenticated fetch wrapper with automated 401 refresh and retry.
 * 403 Forbidden is NOT refreshed and does NOT log out the admin.
 */
export async function authenticatedFetch<T>(
  url: string,
  options: RequestInit = {},
  isRetry = false
): Promise<T> {
  let token = useAdminAuthStore.getState().accessToken;

  // If no token in memory but refresh token exists and not retried yet, bootstrap refresh
  if (!token && !isRetry) {
    if (!inFlightRefreshPromise) {
      inFlightRefreshPromise = executeTokenRefresh();
    }
    token = await inFlightRefreshPromise;
  }

  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Set default JSON Content-Type unless body is FormData
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized (Expired or Invalid Access Token)
  if (response.status === 401 && !isRetry) {
    if (!inFlightRefreshPromise) {
      inFlightRefreshPromise = executeTokenRefresh();
    }
    const newToken = await inFlightRefreshPromise;
    if (newToken) {
      // Retry original request ONCE with new access token
      return authenticatedFetch<T>(url, options, true);
    } else {
      // Refresh failed or revoked
      useAdminAuthStore.getState().clearAuth();
      if (typeof window !== 'undefined' && window.location.pathname.startsWith('/admin')) {
        if (!window.location.pathname.includes('/admin/login')) {
          window.location.href = '/admin/login?expired=1';
        }
      }
      throw new ApiError(401, 'UNAUTHORIZED', 'Session expired. Please log in again.');
    }
  }

  // Handle other HTTP error statuses
  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    let requestId: string | undefined;
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorJson.message || errorDetail;
      requestId = errorJson.request_id;
    } catch {
      // Ignore JSON parse errors on non-JSON error pages
    }
    throw new ApiError(response.status, 'HTTP_ERROR', errorDetail, requestId);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// 1. Administrative Auth Service Functions
// ---------------------------------------------------------------------------

export async function adminLogin(
  username: string,
  password: string
): Promise<{ tokens: TokenResponse; user: AdminUser }> {
  const res = await fetch(`${API_BASE}/admin/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    let errorDetail = 'Invalid username or password.';
    try {
      const err = await res.json();
      errorDetail = err.detail || errorDetail;
    } catch {
      // Ignore
    }
    throw new ApiError(res.status, 'AUTH_FAILED', errorDetail);
  }

  const tokens: TokenResponse = await res.json();

  // Fetch admin profile
  const meRes = await fetch(`${API_BASE}/admin/auth/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });

  if (!meRes.ok) {
    throw new ApiError(meRes.status, 'PROFILE_FETCH_FAILED', 'Failed to fetch admin profile after authentication');
  }

  const user: AdminUser = await meRes.json();
  useAdminAuthStore.getState().setAuth(tokens, user);
  return { tokens, user };
}

export async function adminLogout(): Promise<void> {
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_SESSION_KEY);
  const token = useAdminAuthStore.getState().accessToken;

  try {
    if (token) {
      await fetch(`${API_BASE}/admin/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ refresh_token: refreshToken || undefined }),
      });
    }
  } catch (e) {
    console.warn('Server logout call failed; clearing local credentials.', e);
  } finally {
    useAdminAuthStore.getState().clearAuth();
  }
}

export async function adminBootstrapAuth(): Promise<AdminUser | null> {
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_SESSION_KEY);
  if (!refreshToken) {
    useAdminAuthStore.getState().clearAuth();
    return null;
  }

  if (!inFlightRefreshPromise) {
    inFlightRefreshPromise = executeTokenRefresh();
  }
  const token = await inFlightRefreshPromise;
  if (!token) {
    useAdminAuthStore.getState().clearAuth();
    return null;
  }

  try {
    const user = await authenticatedFetch<AdminUser>('/admin/auth/me');
    useAdminAuthStore.getState().setAdminUser(user);
    useAdminAuthStore.getState().setBootstrapped(true);
    return user;
  } catch {
    useAdminAuthStore.getState().clearAuth();
    return null;
  }
}

// ---------------------------------------------------------------------------
// 2. Document Management APIs
// ---------------------------------------------------------------------------

export async function fetchDocuments(skip = 0, limit = 50): Promise<DocumentListResponse> {
  return authenticatedFetch<DocumentListResponse>(`/admin/documents?skip=${skip}&limit=${limit}`);
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append('file', file);
  return authenticatedFetch<DocumentItem>('/admin/documents', {
    method: 'POST',
    body: formData,
  });
}

export async function downloadDocumentPdf(documentId: string, fallbackFilename = 'document.pdf'): Promise<void> {
  let token = useAdminAuthStore.getState().accessToken;
  if (!token) {
    if (!inFlightRefreshPromise) {
      inFlightRefreshPromise = executeTokenRefresh();
    }
    token = await inFlightRefreshPromise;
  }

  const res = await fetch(`${API_BASE}/admin/documents/${documentId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    throw new ApiError(res.status, 'DOWNLOAD_FAILED', `Failed to download document: ${res.statusText}`);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fallbackFilename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function deleteDocument(documentId: string): Promise<{ message: string; document_id: string }> {
  return authenticatedFetch<{ message: string; document_id: string }>(`/admin/documents/${documentId}`, {
    method: 'DELETE',
  });
}

// ---------------------------------------------------------------------------
// 3. Knowledge Base Generation APIs
// ---------------------------------------------------------------------------

export async function fetchGenerations(skip = 0, limit = 50): Promise<GenerationListResponse> {
  return authenticatedFetch<GenerationListResponse>(`/admin/knowledge/generations?skip=${skip}&limit=${limit}`);
}

export async function fetchGenerationDetail(generationId: string): Promise<GenerationDetailResponse> {
  return authenticatedFetch<GenerationDetailResponse>(`/admin/knowledge/generations/${generationId}`);
}

export async function buildKnowledgeGeneration(payload: BuildGenerationPayload): Promise<KnowledgeGeneration> {
  return authenticatedFetch<KnowledgeGeneration>('/admin/knowledge/generations/build', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function promoteGeneration(generationId: string): Promise<PromoteRollbackResponse> {
  return authenticatedFetch<PromoteRollbackResponse>(`/admin/knowledge/generations/${generationId}/promote`, {
    method: 'POST',
  });
}

export async function rollbackGeneration(generationId: string): Promise<PromoteRollbackResponse> {
  return authenticatedFetch<PromoteRollbackResponse>(`/admin/knowledge/generations/${generationId}/rollback`, {
    method: 'POST',
  });
}

// ---------------------------------------------------------------------------
// 4. RAG Retrieval Diagnostics APIs
// ---------------------------------------------------------------------------

export async function testRetrievalDiagnostic(
  request: RetrievalDiagnosticRequest
): Promise<RetrievalDiagnosticResponse> {
  return authenticatedFetch<RetrievalDiagnosticResponse>('/admin/knowledge/retrieval-test', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// ---------------------------------------------------------------------------
// 5. Translation Registry APIs
// ---------------------------------------------------------------------------

export async function fetchTranslationRegistry(): Promise<TranslationRegistryResponse> {
  return authenticatedFetch<TranslationRegistryResponse>(`/admin/translations`);
}

// ---------------------------------------------------------------------------
// 6. System Probes & Health APIs
// ---------------------------------------------------------------------------

export async function fetchSystemHealth(): Promise<HealthProbeResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok && res.status !== 503) {
    throw new ApiError(res.status, 'HEALTH_CHECK_FAILED', 'Failed to fetch system health probe');
  }
  return res.json();
}
