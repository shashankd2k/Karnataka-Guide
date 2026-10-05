import React from 'react';
import { clsx } from 'clsx';
import { GenerationLifecycleStatus, DocumentStatus, AdminRole } from '../../types/admin';

interface StatusBadgeProps {
  status: GenerationLifecycleStatus | DocumentStatus | AdminRole | string;
  className?: string;
  isActive?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className,
  isActive,
}) => {
  let badgeStyles = 'bg-stone-500/10 text-stone-500 border-stone-500/20';

  if (isActive) {
    badgeStyles = 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
  } else {
    switch (status) {
      case 'ACTIVE':
      case 'PROCESSED':
      case 'SUPER_ADMIN':
        badgeStyles = 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
        break;
      case 'VALIDATED':
      case 'PARSED':
      case 'SITE_CURATOR':
        badgeStyles = 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30';
        break;
      case 'BUILD':
      case 'PARSE':
      case 'CHUNK':
      case 'EMBED':
      case 'INDEX':
      case 'UPLOADED':
      case 'OPERATOR':
        badgeStyles = 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30';
        break;
      case 'FAILED':
        badgeStyles = 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30';
        break;
      case 'ARCHIVED':
      case 'VIEWER':
      default:
        badgeStyles = 'bg-stone-500/10 text-stone-600 dark:text-stone-400 border-stone-500/20';
        break;
    }
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border uppercase tracking-wider',
        badgeStyles,
        className
      )}
    >
      {isActive ? 'ACTIVE INDEX' : status}
    </span>
  );
};
