import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  adminLogin,
  adminLogout,
  adminBootstrapAuth,
  fetchDocuments,
  deleteDocument,
  fetchGenerations,
  testRetrievalDiagnostic,
  fetchTranslationRegistry,
  fetchSystemHealth,
} from '../src/services/adminApiClient';
import { useAdminAuthStore, REFRESH_TOKEN_SESSION_KEY } from '../src/stores/adminAuthStore';
import { ApiError } from '../src/services/apiClient';

describe('AdminApiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAdminAuthStore.getState().clearAuth();
    sessionStorage.clear();
  });

  it('adminLogin authenticates, fetches profile, and stores session tokens', async () => {
    const mockTokens = {
      access_token: 'valid-access-token',
      refresh_token: 'valid-refresh-token',
      token_type: 'bearer',
      expires_in: 3600,
    };
    const mockUser = {
      id: 'admin-1',
      username: 'admin',
      email: 'admin@karnataka.gov',
      role: 'SUPER_ADMIN',
      is_active: true,
      created_at: new Date().toISOString(),
    };

    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

    const result = await adminLogin('admin', 'password123');

    expect(result.tokens.access_token).toBe('valid-access-token');
    expect(result.user.username).toBe('admin');
    expect(useAdminAuthStore.getState().isAuthenticated).toBe(true);
    expect(sessionStorage.getItem(REFRESH_TOKEN_SESSION_KEY)).toBe('valid-refresh-token');
  });

  it('adminLogin throws ApiError on invalid credentials', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid username or password.' }),
    } as Response);

    await expect(adminLogin('admin', 'wrongpass')).rejects.toThrow(ApiError);
    expect(useAdminAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('adminLogout sends revoke request and clears local tokens', async () => {
    useAdminAuthStore.getState().setAccessToken('token');
    sessionStorage.setItem(REFRESH_TOKEN_SESSION_KEY, 'refresh');

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ message: 'Successfully logged out.' }),
    } as Response);

    await adminLogout();

    expect(useAdminAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAdminAuthStore.getState().accessToken).toBeNull();
    expect(sessionStorage.getItem(REFRESH_TOKEN_SESSION_KEY)).toBeNull();
  });

  it('adminBootstrapAuth restores session using sessionStorage refresh token', async () => {
    sessionStorage.setItem(REFRESH_TOKEN_SESSION_KEY, 'valid-session-refresh');

    const mockTokens = {
      access_token: 'new-rotated-access',
      refresh_token: 'new-rotated-refresh',
      token_type: 'bearer',
      expires_in: 3600,
    };
    const mockUser = {
      id: 'admin-1',
      username: 'admin',
      email: 'admin@karnataka.gov',
      role: 'SUPER_ADMIN',
      is_active: true,
      created_at: new Date().toISOString(),
    };

    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      } as Response);

    const user = await adminBootstrapAuth();

    expect(user?.username).toBe('admin');
    expect(useAdminAuthStore.getState().accessToken).toBe('new-rotated-access');
    expect(sessionStorage.getItem(REFRESH_TOKEN_SESSION_KEY)).toBe('new-rotated-refresh');
    expect(useAdminAuthStore.getState().isBootstrapped).toBe(true);
  });

  it('authenticatedFetch automatically refreshes token on 401 and retries original request', async () => {
    useAdminAuthStore.getState().setAccessToken('expired-access-token');
    sessionStorage.setItem(REFRESH_TOKEN_SESSION_KEY, 'valid-refresh-token');

    const mockNewTokens = {
      access_token: 'fresh-access-token',
      refresh_token: 'fresh-refresh-token',
      token_type: 'bearer',
      expires_in: 3600,
    };
    const mockDocList = {
      items: [],
      total: 0,
      skip: 0,
      limit: 50,
    };

    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Token has expired.' }),
      } as Response) // First request fails with 401
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockNewTokens,
      } as Response) // Refresh endpoint succeeds
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockDocList,
      } as Response); // Retried original request succeeds

    const result = await fetchDocuments();
    expect(result.total).toBe(0);
    expect(useAdminAuthStore.getState().accessToken).toBe('fresh-access-token');
  });

  it('single-flight refresh: concurrent protected requests on 401 execute exactly ONE refresh call', async () => {
    useAdminAuthStore.getState().setAccessToken('expired-token');
    sessionStorage.setItem(REFRESH_TOKEN_SESSION_KEY, 'valid-refresh-token');

    const mockNewTokens = {
      access_token: 'fresh-single-flight-token',
      refresh_token: 'fresh-single-flight-refresh',
      token_type: 'bearer',
      expires_in: 3600,
    };

    let refreshCallCount = 0;

    global.fetch = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes('/admin/auth/refresh')) {
        refreshCallCount++;
        return {
          ok: true,
          status: 200,
          json: async () => mockNewTokens,
        } as Response;
      }
      if (url.includes('/admin/documents')) {
        const token = useAdminAuthStore.getState().accessToken;
        if (token === 'expired-token') {
          return {
            ok: false,
            status: 401,
            json: async () => ({ detail: 'Token expired' }),
          } as Response;
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ items: [], total: 0 }),
        } as Response;
      }
      if (url.includes('/admin/knowledge/generations')) {
        const token = useAdminAuthStore.getState().accessToken;
        if (token === 'expired-token') {
          return {
            ok: false,
            status: 401,
            json: async () => ({ detail: 'Token expired' }),
          } as Response;
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ items: [], total: 0 }),
        } as Response;
      }
      return { ok: true, status: 200, json: async () => ({}) } as Response;
    });

    // Fire 2 protected calls concurrently
    const [docsRes, gensRes] = await Promise.all([
      fetchDocuments(),
      fetchGenerations(),
    ]);

    expect(docsRes.total).toBe(0);
    expect(gensRes.total).toBe(0);
    // CRITICAL: Exactly ONE refresh call occurred despite 2 concurrent 401s
    expect(refreshCallCount).toBe(1);
    expect(useAdminAuthStore.getState().accessToken).toBe('fresh-single-flight-token');
  });

  it('authenticatedFetch on 403 Forbidden does NOT call refresh and throws ApiError', async () => {
    useAdminAuthStore.getState().setAccessToken('valid-viewer-token');
    sessionStorage.setItem(REFRESH_TOKEN_SESSION_KEY, 'valid-refresh-token');

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: 'Insufficient permissions. Required role: SUPER_ADMIN.' }),
    } as Response);

    global.fetch = fetchSpy;

    await expect(deleteDocument('doc-123')).rejects.toThrow(ApiError);
    // Crucial check: Fetch was called exactly ONCE (no attempt to call /auth/refresh)
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(useAdminAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('fetchGenerations returns knowledge generations list', async () => {
    useAdminAuthStore.getState().setAccessToken('valid-token');
    const mockGens = {
      items: [
        {
          id: 'gen-1',
          generation_version: 'v_20260901',
          status: 'ACTIVE',
          is_active: true,
          document_count: 6,
          chunk_count: 524,
          embedding_count: 524,
          embedding_model: 'all-MiniLM-L6-v2',
          created_by_admin_id: 'admin-1',
          created_at: new Date().toISOString(),
        },
      ],
      total: 1,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockGens,
    } as Response);

    const result = await fetchGenerations();
    expect(result.items[0].generation_version).toBe('v_20260901');
    expect(result.items[0].is_active).toBe(true);
  });

  it('testRetrievalDiagnostic sends diagnostic request and returns candidate rankings', async () => {
    useAdminAuthStore.getState().setAccessToken('valid-token');
    const mockDiag = {
      query: 'Who built Belur?',
      normalized_query: 'who built belur',
      active_generation_id: 'gen-1',
      active_generation_version: 'v_20260901',
      dense_candidates_count: 22,
      bm25_candidates_count: 22,
      fused_candidates_count: 15,
      final_count: 5,
      results: [
        {
          chunk_id: 'c1',
          document_id: 'd1',
          generation_id: 'gen-1',
          text: 'King Vishnuvardhana commissioned Belur in 1117 CE.',
          page_number: 2,
          source_filename: 'Belur_Guide.pdf',
          final_rank: 1,
          reranker_score: 10.5,
        },
      ],
      timings_ms: {
        dense_ms: 12.5,
        bm25_ms: 5.2,
        fusion_ms: 1.1,
        rerank_ms: 45.3,
        total_ms: 64.1,
      },
      diagnostic_notes: ['Dense and sparse retrieval fused via RRF'],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockDiag,
    } as Response);

    const result = await testRetrievalDiagnostic({ query: 'Who built Belur?' });
    expect(result.results.length).toBe(1);
    expect(result.timings_ms.total_ms).toBe(64.1);
  });

  it('fetchTranslationRegistry returns NLLB engine health and language pairs', async () => {
    useAdminAuthStore.getState().setAccessToken('valid-token');
    const mockTrans = {
      provider_engine: 'nllb-200',
      provider_healthy: true,
      supported_languages: ['en', 'kn'],
      translations: [
        {
          id: 'trans-1',
          source_lang: 'kn',
          target_lang: 'en',
          engine: 'nllb-200',
          package_version: 'v1.0.0',
          is_active: true,
        },
      ],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockTrans,
    } as Response);

    const result = await fetchTranslationRegistry();
    expect(result.provider_healthy).toBe(true);
    expect(result.translations.length).toBe(1);
  });

  it('fetchSystemHealth returns real platform probes', async () => {
    const mockHealth = {
      status: 'healthy',
      api_version: 'v1',
      app_version: '0.1.0',
      profile: 'dev',
      timestamp: new Date().toISOString(),
      subsystems: {
        app: 'healthy',
        database: 'healthy',
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth,
    } as Response);

    const result = await fetchSystemHealth();
    expect(result.status).toBe('healthy');
    expect(result.app_version).toBe('0.1.0');
    expect(result.profile).toBe('dev');
  });
});
