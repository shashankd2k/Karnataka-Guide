import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { StatusBadge } from '../src/components/admin/StatusBadge';
import { ConfirmDialog } from '../src/components/admin/ConfirmDialog';
import { AdminSidebar } from '../src/components/admin/AdminSidebar';
import { useAdminAuthStore } from '../src/stores/adminAuthStore';

describe('Admin UI Components', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAdminAuthStore.getState().clearAuth();
  });

  it('StatusBadge renders ACTIVE status with distinct styling', () => {
    render(<StatusBadge status="ACTIVE" isActive={true} />);
    expect(screen.getByText('ACTIVE INDEX')).toBeDefined();
  });

  it('StatusBadge renders standard lifecycle statuses correctly', () => {
    const { rerender } = render(<StatusBadge status="VALIDATED" />);
    expect(screen.getByText('VALIDATED')).toBeDefined();

    rerender(<StatusBadge status="FAILED" />);
    expect(screen.getByText('FAILED')).toBeDefined();

    rerender(<StatusBadge status="BUILD" />);
    expect(screen.getByText('BUILD')).toBeDefined();
  });

  it('ConfirmDialog displays title, message, and handles callbacks', () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();

    render(
      <ConfirmDialog
        isOpen={true}
        title="Promote Generation to ACTIVE?"
        message="Tourist queries will immediately use this index."
        confirmLabel="Promote Index"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );

    expect(screen.getByText('Promote Generation to ACTIVE?')).toBeDefined();
    expect(
      screen.getByText('Tourist queries will immediately use this index.')
    ).toBeDefined();

    fireEvent.click(screen.getByText('Promote Index'));
    expect(onConfirm).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('Cancel'));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('AdminSidebar displays navigation links and authenticated admin profile', () => {
    useAdminAuthStore.getState().setAuth(
      {
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer',
        expires_in: 3600,
      },
      {
        id: 'admin-1',
        username: 'masteradmin',
        email: 'master@karnataka.gov',
        role: 'SUPER_ADMIN',
        is_active: true,
        created_at: new Date().toISOString(),
      }
    );

    render(
      <MemoryRouter>
        <AdminSidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Overview')).toBeDefined();
    expect(screen.getByText('PDF Documents')).toBeDefined();
    expect(screen.getByText('Knowledge Base')).toBeDefined();
    expect(screen.getByText('Retrieval Diagnostic')).toBeDefined();
    expect(screen.getByText('Translation Registry')).toBeDefined();
    expect(screen.getByText('System & Health')).toBeDefined();
    expect(screen.getByText('masteradmin')).toBeDefined();
    expect(screen.getByText('SUPER_ADMIN')).toBeDefined();
  });
});
