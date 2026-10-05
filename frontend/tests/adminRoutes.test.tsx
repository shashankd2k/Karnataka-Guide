import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../src/components/admin/ProtectedRoute';
import { useAdminAuthStore } from '../src/stores/adminAuthStore';

describe('ProtectedRoute Guard', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAdminAuthStore.getState().clearAuth();
    sessionStorage.clear();
  });

  it('redirects unauthenticated visitor to /admin/login', async () => {
    useAdminAuthStore.getState().setBootstrapped(true);

    render(
      <MemoryRouter initialEntries={['/admin/documents']}>
        <Routes>
          <Route
            path="/admin/documents"
            element={
              <ProtectedRoute>
                <div>Protected Admin Documents View</div>
              </ProtectedRoute>
            }
          />
          <Route path="/admin/login" element={<div>Admin Login View</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Admin Login View')).toBeDefined();
  });

  it('renders children when authenticated with valid role', () => {
    useAdminAuthStore.getState().setAuth(
      {
        access_token: 'valid-token',
        refresh_token: 'valid-refresh',
        token_type: 'bearer',
        expires_in: 3600,
      },
      {
        id: 'admin-1',
        username: 'superadmin',
        email: 'super@karnataka.gov',
        role: 'SUPER_ADMIN',
        is_active: true,
        created_at: new Date().toISOString(),
      }
    );

    render(
      <MemoryRouter initialEntries={['/admin/documents']}>
        <Routes>
          <Route
            path="/admin/documents"
            element={
              <ProtectedRoute requiredRoles={['SUPER_ADMIN']}>
                <div>Protected Admin Documents View</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Protected Admin Documents View')).toBeDefined();
  });

  it('renders 403 Forbidden when user role is not permitted', () => {
    useAdminAuthStore.getState().setAuth(
      {
        access_token: 'valid-token',
        refresh_token: 'valid-refresh',
        token_type: 'bearer',
        expires_in: 3600,
      },
      {
        id: 'viewer-1',
        username: 'guestviewer',
        email: 'viewer@karnataka.gov',
        role: 'VIEWER',
        is_active: true,
        created_at: new Date().toISOString(),
      }
    );

    render(
      <MemoryRouter initialEntries={['/admin/documents']}>
        <Routes>
          <Route
            path="/admin/documents"
            element={
              <ProtectedRoute requiredRoles={['SUPER_ADMIN', 'SITE_CURATOR']}>
                <div>Protected Mutation View</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/Access Forbidden \(403\)/i)).toBeDefined();
    expect(screen.getByText(/VIEWER/i)).toBeDefined();
  });

  it('renders loading state during initial bootstrap when refresh token exists in sessionStorage', () => {
    sessionStorage.setItem('karnataka_admin_refresh_token', 'valid-refresh-token');
    useAdminAuthStore.getState().setBootstrapped(false);

    render(
      <MemoryRouter initialEntries={['/admin/documents']}>
        <Routes>
          <Route
            path="/admin/documents"
            element={
              <ProtectedRoute>
                <div>Protected Admin Documents View</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    // Shows loading spinner rather than premature redirect to login
    expect(screen.getByText('Authenticating Administrator Session...')).toBeDefined();
  });
});

