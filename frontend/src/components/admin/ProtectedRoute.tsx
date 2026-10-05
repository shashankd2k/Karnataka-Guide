import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAdminAuthStore } from '../../stores/adminAuthStore';
import { adminBootstrapAuth } from '../../services/adminApiClient';
import { AdminRole } from '../../types/admin';
import { ShieldAlert, Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactElement;
  requiredRoles?: AdminRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRoles,
}) => {
  const location = useLocation();
  const { isAuthenticated, isBootstrapped, adminUser } = useAdminAuthStore();
  const [isInitializing, setIsInitializing] = useState(!isBootstrapped);

  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      if (!isBootstrapped) {
        try {
          await adminBootstrapAuth();
        } catch {
          // Handled inside bootstrap
        } finally {
          if (isMounted) {
            setIsInitializing(false);
          }
        }
      } else {
        setIsInitializing(false);
      }
    }

    initAuth();

    return () => {
      isMounted = false;
    };
  }, [isBootstrapped]);

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)] flex flex-col items-center justify-center p-6 text-center">
        <Loader2 className="w-10 h-10 text-[var(--color-gold)] animate-spin mb-4" />
        <h2 className="text-lg font-serif font-bold text-[var(--color-text)]">
          Authenticating Administrator Session...
        </h2>
        <p className="text-xs text-[var(--color-text-secondary)] mt-1">
          Validating cryptographic token rotation with security gateway.
        </p>
      </div>
    );
  }

  if (!isAuthenticated || !adminUser) {
    return <Navigate to={`/admin/login?redirect=${encodeURIComponent(location.pathname)}`} replace />;
  }

  if (requiredRoles && requiredRoles.length > 0 && !requiredRoles.includes(adminUser.role)) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center">
        <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center text-red-500 mb-4 border border-red-500/20">
          <ShieldAlert className="w-7 h-7" />
        </div>
        <h2 className="text-2xl font-serif font-bold text-[var(--color-text)]">
          Access Forbidden (403)
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)] max-w-md mt-2">
          Your current role (<span className="font-semibold text-[var(--color-gold)]">{adminUser.role}</span>) does not have sufficient permissions to access this administrative view.
        </p>
      </div>
    );
  }

  return children;
};
