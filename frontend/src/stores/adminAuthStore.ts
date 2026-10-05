/**
 * Administrative Authentication Store (Zustand).
 * 
 * Token Security Architecture:
 * - access_token: In-memory only (never written to localStorage or sessionStorage).
 * - refresh_token: sessionStorage (transient across active tab lifetime, purged on logout/expiry).
 * - JavaScript-accessible note: sessionStorage is accessible to JS and not HttpOnly; mitigated
 *   by token rotation, unique JTI tracking, in-memory access tokens, and absence of console logging.
 */

import { create } from 'zustand';
import { AdminUser, TokenResponse } from '../types/admin';

export const REFRESH_TOKEN_SESSION_KEY = 'karnataka_admin_refresh_token';

interface AdminAuthState {
  accessToken: string | null;
  adminUser: AdminUser | null;
  isAuthenticated: boolean;
  isBootstrapped: boolean;

  setAuth: (tokens: TokenResponse, user: AdminUser) => void;
  setAccessToken: (token: string) => void;
  setAdminUser: (user: AdminUser) => void;
  setBootstrapped: (bootstrapped: boolean) => void;
  clearAuth: () => void;

  // RBAC Permission Helpers
  canManageDocuments: () => boolean;
  canManageKnowledge: () => boolean;
  isSuperAdmin: () => boolean;
}

export const useAdminAuthStore = create<AdminAuthState>((set, get) => ({
  accessToken: null,
  adminUser: null,
  isAuthenticated: false,
  isBootstrapped: false,

  setAuth: (tokens: TokenResponse, user: AdminUser) => {
    try {
      sessionStorage.setItem(REFRESH_TOKEN_SESSION_KEY, tokens.refresh_token);
    } catch {
      // Ignore storage errors in restricted contexts
    }
    set({
      accessToken: tokens.access_token,
      adminUser: user,
      isAuthenticated: true,
      isBootstrapped: true,
    });
  },

  setAccessToken: (token: string) => {
    set({ accessToken: token, isAuthenticated: true });
  },

  setAdminUser: (user: AdminUser) => {
    set({ adminUser: user, isAuthenticated: true });
  },

  setBootstrapped: (bootstrapped: boolean) => {
    set({ isBootstrapped: bootstrapped });
  },

  clearAuth: () => {
    try {
      sessionStorage.removeItem(REFRESH_TOKEN_SESSION_KEY);
    } catch {
      // Ignore storage errors
    }
    set({
      accessToken: null,
      adminUser: null,
      isAuthenticated: false,
      isBootstrapped: true,
    });
  },

  canManageDocuments: () => {
    const role = get().adminUser?.role;
    return role === 'SUPER_ADMIN' || role === 'SITE_CURATOR';
  },

  canManageKnowledge: () => {
    const role = get().adminUser?.role;
    return role === 'SUPER_ADMIN' || role === 'SITE_CURATOR';
  },

  isSuperAdmin: () => {
    return get().adminUser?.role === 'SUPER_ADMIN';
  },
}));
