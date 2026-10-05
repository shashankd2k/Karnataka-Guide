import { describe, it, expect, beforeEach } from 'vitest';
import { useAdminAuthStore, REFRESH_TOKEN_SESSION_KEY } from '../src/stores/adminAuthStore';
import { AdminUser, TokenResponse } from '../src/types/admin';

describe('AdminAuthStore', () => {
  beforeEach(() => {
    useAdminAuthStore.getState().clearAuth();
    sessionStorage.clear();
  });

  it('initializes with unauthenticated state', () => {
    const state = useAdminAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.accessToken).toBeNull();
    expect(state.adminUser).toBeNull();
    expect(state.isBootstrapped).toBe(true);
  });

  it('setAuth stores access_token in memory and refresh_token in sessionStorage', () => {
    const mockTokens: TokenResponse = {
      access_token: 'mock-access-token-jwt',
      refresh_token: 'mock-refresh-token-jwt',
      token_type: 'bearer',
      expires_in: 3600,
    };
    const mockUser: AdminUser = {
      id: 'admin-123',
      username: 'testcurator',
      email: 'curator@karnataka.gov',
      role: 'SITE_CURATOR',
      is_active: true,
      created_at: new Date().toISOString(),
    };

    useAdminAuthStore.getState().setAuth(mockTokens, mockUser);

    const state = useAdminAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.accessToken).toBe('mock-access-token-jwt');
    expect(state.adminUser?.username).toBe('testcurator');
    expect(sessionStorage.getItem(REFRESH_TOKEN_SESSION_KEY)).toBe('mock-refresh-token-jwt');
  });

  it('role permissions: SUPER_ADMIN and SITE_CURATOR have mutation rights', () => {
    const mockTokens: TokenResponse = {
      access_token: 'token',
      refresh_token: 'refresh',
      token_type: 'bearer',
      expires_in: 3600,
    };

    // SITE_CURATOR
    useAdminAuthStore.getState().setAuth(mockTokens, {
      id: 'curator-1',
      username: 'curator',
      email: 'curator@test.com',
      role: 'SITE_CURATOR',
      is_active: true,
      created_at: new Date().toISOString(),
    });
    expect(useAdminAuthStore.getState().canManageDocuments()).toBe(true);
    expect(useAdminAuthStore.getState().canManageKnowledge()).toBe(true);
    expect(useAdminAuthStore.getState().isSuperAdmin()).toBe(false);

    // VIEWER
    useAdminAuthStore.getState().setAuth(mockTokens, {
      id: 'viewer-1',
      username: 'viewer',
      email: 'viewer@test.com',
      role: 'VIEWER',
      is_active: true,
      created_at: new Date().toISOString(),
    });
    expect(useAdminAuthStore.getState().canManageDocuments()).toBe(false);
    expect(useAdminAuthStore.getState().canManageKnowledge()).toBe(false);
    expect(useAdminAuthStore.getState().isSuperAdmin()).toBe(false);

    // OPERATOR
    useAdminAuthStore.getState().setAuth(mockTokens, {
      id: 'op-1',
      username: 'operator',
      email: 'op@test.com',
      role: 'OPERATOR',
      is_active: true,
      created_at: new Date().toISOString(),
    });
    expect(useAdminAuthStore.getState().canManageDocuments()).toBe(false);
    expect(useAdminAuthStore.getState().canManageKnowledge()).toBe(false);
  });

  it('clearAuth wipes memory and sessionStorage credentials', () => {
    sessionStorage.setItem(REFRESH_TOKEN_SESSION_KEY, 'some-refresh-token');
    useAdminAuthStore.getState().setAccessToken('some-access-token');

    useAdminAuthStore.getState().clearAuth();

    const state = useAdminAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.adminUser).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem(REFRESH_TOKEN_SESSION_KEY)).toBeNull();
  });
});
