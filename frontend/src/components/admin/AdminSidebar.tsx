import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Database,
  SearchCode,
  Languages,
  Activity,
  ArrowLeft,
  Shield,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useAdminAuthStore } from '../../stores/adminAuthStore';
import { StatusBadge } from './StatusBadge';

interface AdminSidebarProps {
  onCloseMobile?: () => void;
}

export const AdminSidebar: React.FC<AdminSidebarProps> = ({ onCloseMobile }) => {
  const { adminUser } = useAdminAuthStore();

  const navItems = [
    { to: '/admin', label: 'Overview', icon: LayoutDashboard, end: true },
    { to: '/admin/documents', label: 'PDF Documents', icon: FileText },
    { to: '/admin/knowledge', label: 'Knowledge Base', icon: Database },
    { to: '/admin/retrieval-test', label: 'Retrieval Diagnostic', icon: SearchCode },
    { to: '/admin/translations', label: 'Translation Registry', icon: Languages },
    { to: '/admin/system', label: 'System & Health', icon: Activity },
  ];

  return (
    <aside className="w-64 bg-[var(--color-surface)] border-r border-[var(--color-border)] flex flex-col h-full shrink-0">
      {/* Brand & Platform Header */}
      <div className="p-5 border-b border-[var(--color-border)] flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-[var(--color-gold)]/15 border border-[var(--color-gold)]/30 flex items-center justify-center text-[var(--color-gold)] font-serif font-bold text-lg">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-serif font-bold text-sm text-[var(--color-text)] tracking-tight">
            Karnataka Guide
          </h1>
          <p className="text-[11px] text-[var(--color-gold)] font-medium tracking-wide uppercase">
            Admin Console
          </p>
        </div>
      </div>

      {/* User Mini Profile */}
      {adminUser && (
        <div className="p-4 mx-3 my-3 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-[var(--color-text)] truncate max-w-[130px]">
              {adminUser.username}
            </span>
            <StatusBadge status={adminUser.role} />
          </div>
          <p className="text-[11px] text-[var(--color-text-secondary)] truncate">
            {adminUser.email}
          </p>
        </div>
      )}

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all duration-150',
                  isActive
                    ? 'bg-[var(--color-gold)]/15 text-[var(--color-gold-dark)] dark:text-[var(--color-gold)] font-semibold border border-[var(--color-gold)]/20'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)]'
                )
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Tourist Portal Return Link */}
      <div className="p-3 border-t border-[var(--color-border)]">
        <NavLink
          to="/"
          className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Exit to Tourist Portal</span>
        </NavLink>
      </div>
    </aside>
  );
};
