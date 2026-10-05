import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Sun, Moon, Laptop, Menu, Loader2 } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';
import { useAdminAuthStore } from '../../stores/adminAuthStore';
import { adminLogout } from '../../services/adminApiClient';

interface AdminHeaderProps {
  onOpenMobileMenu?: () => void;
}

export const AdminHeader: React.FC<AdminHeaderProps> = ({ onOpenMobileMenu }) => {
  const navigate = useNavigate();
  const { theme, setTheme } = useTouristStore();
  const { adminUser } = useAdminAuthStore();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const cycleTheme = () => {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await adminLogout();
    } finally {
      setIsLoggingOut(false);
      navigate('/admin/login');
    }
  };

  return (
    <header className="h-16 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 sm:px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        {/* Mobile Hamburger */}
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="md:hidden p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
          aria-label="Open Navigation Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <span className="hidden sm:inline-block text-xs font-medium text-[var(--color-text-secondary)]">
          Karnataka Smart Tourist Guide Platform
        </span>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Theme Toggle */}
        <button
          type="button"
          onClick={cycleTheme}
          aria-label="Toggle visual theme"
          className="p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)] transition-colors border border-[var(--color-border)]"
          title={`Theme: ${theme}`}
        >
          {theme === 'dark' ? (
            <Moon className="w-4 h-4" />
          ) : theme === 'light' ? (
            <Sun className="w-4 h-4" />
          ) : (
            <Laptop className="w-4 h-4" />
          )}
        </button>

        {/* Admin Identifier */}
        {adminUser && (
          <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-[var(--color-border)]">
            <span className="text-xs font-semibold text-[var(--color-text)]">
              {adminUser.username}
            </span>
          </div>
        )}

        {/* Logout Button */}
        <button
          type="button"
          disabled={isLoggingOut}
          onClick={handleLogout}
          aria-label="Log Out of Admin Console"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-500/10 border border-red-500/20 transition-colors disabled:opacity-50"
        >
          {isLoggingOut ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <LogOut className="w-3.5 h-3.5" />
          )}
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
};
