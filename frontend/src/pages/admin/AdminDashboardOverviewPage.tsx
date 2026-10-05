import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Database,
  FileText,
  Languages,
  Activity,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  SearchCode,
  Upload,
  Layers,
  Sparkles,
} from 'lucide-react';
import {
  fetchDocuments,
  fetchGenerations,
  fetchSystemHealth,
  fetchTranslationRegistry,
} from '../../services/adminApiClient';
import { StatusBadge } from '../../components/admin/StatusBadge';
import { useAdminAuthStore } from '../../stores/adminAuthStore';

export const AdminDashboardOverviewPage: React.FC = () => {
  const { adminUser, canManageKnowledge } = useAdminAuthStore();

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['admin', 'health'],
    queryFn: fetchSystemHealth,
    refetchInterval: 30000,
  });

  const { data: docData, isLoading: docsLoading } = useQuery({
    queryKey: ['admin', 'documents', 'count'],
    queryFn: () => fetchDocuments(0, 1),
  });

  const { data: genData, isLoading: genLoading } = useQuery({
    queryKey: ['admin', 'generations'],
    queryFn: () => fetchGenerations(0, 50),
  });

  const { data: transData, isLoading: transLoading } = useQuery({
    queryKey: ['admin', 'translations'],
    queryFn: fetchTranslationRegistry,
  });

  const activeGeneration = genData?.items.find((g) => g.is_active);

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-gold)]">
              Operations Center
            </span>
            <span className="text-[var(--color-border)]">•</span>
            <span className="text-xs text-[var(--color-text-secondary)]">
              Profile: {health?.profile || 'Loading...'}
            </span>
          </div>
          <h2 className="text-2xl font-serif font-bold text-[var(--color-text)]">
            Welcome back, {adminUser?.username}
          </h2>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1">
            Manage heritage documents, supervise knowledge base generations, and monitor retrieval diagnostics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/admin/documents"
            className="px-3.5 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text)] hover:border-[var(--color-gold)] transition-colors flex items-center gap-2"
          >
            <Upload className="w-3.5 h-3.5 text-[var(--color-gold)]" />
            <span>Upload PDF</span>
          </Link>
          {canManageKnowledge() && (
            <Link
              to="/admin/knowledge"
              className="px-3.5 py-2 rounded-xl bg-[var(--color-gold)] hover:bg-[var(--color-gold-dark)] text-stone-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Build Knowledge</span>
            </Link>
          )}
        </div>
      </div>

      {/* Primary KPI Grid (All Real Data) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* System Health */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
              System Gateway
            </span>
            <Activity className="w-4 h-4 text-[var(--color-gold)]" />
          </div>
          <div className="flex items-center gap-2">
            {health?.status === 'healthy' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-amber-500" />
            )}
            <span className="text-xl font-bold font-serif text-[var(--color-text)] capitalize">
              {healthLoading ? '...' : health?.status || 'Unknown'}
            </span>
          </div>
          <p className="text-[11px] text-[var(--color-text-secondary)] mt-2">
            App: {health?.subsystems.app} • DB: {health?.subsystems.database}
          </p>
        </div>

        {/* Total Documents */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
              Heritage Documents
            </span>
            <FileText className="w-4 h-4 text-[var(--color-gold)]" />
          </div>
          <div className="text-2xl font-bold font-serif text-[var(--color-text)]">
            {docsLoading ? '...' : docData?.total ?? 0}
          </div>
          <p className="text-[11px] text-[var(--color-text-secondary)] mt-2">
            Source PDF guidelines indexed
          </p>
        </div>

        {/* Active Knowledge Generation */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
              Active Generation
            </span>
            <Database className="w-4 h-4 text-[var(--color-gold)]" />
          </div>
          <div className="text-lg font-bold font-mono text-[var(--color-gold)] truncate">
            {genLoading
              ? '...'
              : activeGeneration?.generation_version || 'None Active'}
          </div>
          <p className="text-[11px] text-[var(--color-text-secondary)] mt-2">
            {activeGeneration
              ? `${activeGeneration.chunk_count} chunks • ${activeGeneration.embedding_count} vectors`
              : 'No active generation selected'}
          </p>
        </div>

        {/* Translation Engine */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
              Translation Engine
            </span>
            <Languages className="w-4 h-4 text-[var(--color-gold)]" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold font-serif text-[var(--color-text)]">
              {transLoading ? '...' : transData?.provider_engine || 'NLLB-200'}
            </span>
            {transData?.provider_healthy && (
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            )}
          </div>
          <p className="text-[11px] text-[var(--color-text-secondary)] mt-2">
            Languages: {transData?.supported_languages.join(', ') || 'en, kn'}
          </p>
        </div>
      </div>

      {/* Active Generation Detailed Spotlight */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4 border-b border-[var(--color-border)] pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--color-gold)]/10 text-[var(--color-gold)]">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-serif font-bold text-[var(--color-text)]">
                Authoritative Knowledge Index
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Currently serving grounded retrieval for all tourist inquiries
              </p>
            </div>
          </div>
          {activeGeneration && <StatusBadge status="ACTIVE" isActive={true} />}
        </div>

        {activeGeneration ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
              <span className="text-[var(--color-text-secondary)] block mb-1">Version</span>
              <span className="font-mono font-semibold text-[var(--color-text)] text-sm">
                {activeGeneration.generation_version}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
              <span className="text-[var(--color-text-secondary)] block mb-1">Embedding Model</span>
              <span className="font-medium text-[var(--color-text)]">
                {activeGeneration.embedding_model}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
              <span className="text-[var(--color-text-secondary)] block mb-1">Indexed Content</span>
              <span className="font-semibold text-[var(--color-text)]">
                {activeGeneration.document_count} PDFs ({activeGeneration.chunk_count} chunks)
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
              <span className="text-[var(--color-text-secondary)] block mb-1">Promoted At</span>
              <span className="font-medium text-[var(--color-text)]">
                {activeGeneration.promoted_at
                  ? new Date(activeGeneration.promoted_at).toLocaleString()
                  : 'Initial'}
              </span>
            </div>
          </div>
        ) : (
          <div className="p-8 text-center bg-[var(--color-bg)] rounded-xl border border-dashed border-[var(--color-border)]">
            <Database className="w-8 h-8 text-[var(--color-text-secondary)] mx-auto mb-2 opacity-50" />
            <p className="text-xs text-[var(--color-text-secondary)]">
              No knowledge generation is currently marked ACTIVE.
            </p>
          </div>
        )}

        <div className="mt-4 pt-3 border-t border-[var(--color-border)] flex items-center justify-between text-xs">
          <Link
            to="/admin/knowledge"
            className="text-[var(--color-gold-dark)] dark:text-[var(--color-gold)] font-medium hover:underline flex items-center gap-1.5"
          >
            <span>Manage All Generations</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <Link
            to="/admin/retrieval-test"
            className="text-[var(--color-text-secondary)] hover:text-[var(--color-text)] flex items-center gap-1.5"
          >
            <SearchCode className="w-3.5 h-3.5" />
            <span>Test Retrieval Engine</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
