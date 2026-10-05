import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Database,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  Loader2,
} from 'lucide-react';
import { fetchGenerationDetail } from '../../services/adminApiClient';
import { StatusBadge } from '../../components/admin/StatusBadge';

export const AdminGenerationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'generation', id],
    queryFn: () => fetchGenerationDetail(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      // Poll while building or pending
      const status = query.state.data?.generation.status;
      return status && ['BUILD', 'PARSE', 'CHUNK', 'EMBED', 'INDEX'].includes(status)
        ? 3000
        : false;
    },
  });

  if (isLoading) {
    return (
      <div className="py-16 text-center text-[var(--color-text-secondary)]">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-[var(--color-gold)]" />
        <p className="text-xs">Loading generation details and pipeline stages...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center bg-[var(--color-surface)] rounded-2xl border border-[var(--color-border)]">
        <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-3" />
        <h3 className="text-base font-serif font-bold text-[var(--color-text)]">
          Failed to Load Generation
        </h3>
        <p className="text-xs text-[var(--color-text-secondary)] mt-1 mb-4">
          The requested knowledge generation ID could not be found or retrieved.
        </p>
        <Link
          to="/admin/knowledge"
          className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--color-gold)] hover:underline"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Knowledge Base</span>
        </Link>
      </div>
    );
  }

  const { generation, stages } = data;

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Actions */}
      <div className="flex items-center justify-between">
        <Link
          to="/admin/knowledge"
          className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Generations</span>
        </Link>

        {generation.is_active && <StatusBadge status="ACTIVE" isActive={true} />}
      </div>

      {/* Generation Overview Banner */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4 border-b border-[var(--color-border)] pb-4">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-gold)]/15 text-[var(--color-gold)] flex items-center justify-center">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-serif font-bold text-[var(--color-text)]">
              Generation {generation.generation_version}
            </h2>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Identifier: <span className="font-mono">{generation.id}</span>
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
            <span className="text-[var(--color-text-secondary)] block mb-1">Status</span>
            <StatusBadge status={generation.status} />
          </div>
          <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
            <span className="text-[var(--color-text-secondary)] block mb-1">Documents Indexed</span>
            <span className="font-semibold text-[var(--color-text)]">{generation.document_count} PDFs</span>
          </div>
          <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
            <span className="text-[var(--color-text-secondary)] block mb-1">Chunks & Embeddings</span>
            <span className="font-semibold text-[var(--color-text)]">
              {generation.chunk_count} Chunks ({generation.embedding_count} Vectors)
            </span>
          </div>
          <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
            <span className="text-[var(--color-text-secondary)] block mb-1">Created At</span>
            <span className="font-medium text-[var(--color-text)]">
              {new Date(generation.created_at).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Execution Stages Timeline */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-6">
          <Layers className="w-4 h-4 text-[var(--color-gold)]" />
          <h3 className="font-serif font-bold text-sm text-[var(--color-text)]">
            Pipeline Execution Stages
          </h3>
        </div>

        {stages.length === 0 ? (
          <p className="text-xs text-[var(--color-text-secondary)]">
            No stage telemetry recorded for this generation.
          </p>
        ) : (
          <div className="space-y-4">
            {stages.map((stage, idx) => {
              const isCompleted = stage.progress_pct === 100 || !!stage.completed_at;
              const isError = stage.stage === 'ERROR' || !!stage.error_details;

              return (
                <div
                  key={stage.id || idx}
                  className="p-4 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {isError ? (
                        <AlertTriangle className="w-4 h-4 text-red-500" />
                      ) : isCompleted ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      ) : (
                        <Clock className="w-4 h-4 text-[var(--color-gold)]" />
                      )}
                    </div>
                    <div>
                      <span className="font-semibold text-xs text-[var(--color-text)] uppercase tracking-wider block">
                        {stage.stage}
                      </span>
                      {stage.message && (
                        <p className="text-[11px] text-[var(--color-text-secondary)] mt-0.5">
                          {stage.message}
                        </p>
                      )}
                      {stage.error_details && (
                        <p className="text-[11px] text-red-500 mt-1 font-mono break-all">
                          {stage.error_details}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0 sm:text-right">
                    <div>
                      <div className="w-24 bg-[var(--color-surface)] rounded-full h-1.5 border border-[var(--color-border)] overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            isError ? 'bg-red-500' : isCompleted ? 'bg-emerald-500' : 'bg-[var(--color-gold)]'
                          }`}
                          style={{ width: `${stage.progress_pct}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-[var(--color-text-secondary)] mt-0.5 block">
                        {stage.progress_pct}% complete
                      </span>
                    </div>

                    <div className="text-[10px] text-[var(--color-text-secondary)] min-w-[70px]">
                      {stage.completed_at
                        ? new Date(stage.completed_at).toLocaleTimeString()
                        : 'Running...'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
