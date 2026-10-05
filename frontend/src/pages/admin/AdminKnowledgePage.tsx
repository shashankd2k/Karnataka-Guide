import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Database,
  Sparkles,
  ArrowUpCircle,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Layers,
  FileText,
  ChevronRight,
  Loader2,
  Calendar,
} from 'lucide-react';
import {
  fetchGenerations,
  fetchDocuments,
  buildKnowledgeGeneration,
  promoteGeneration,
  rollbackGeneration,
} from '../../services/adminApiClient';
import { KnowledgeGeneration } from '../../types/admin';
import { StatusBadge } from '../../components/admin/StatusBadge';
import { ConfirmDialog } from '../../components/admin/ConfirmDialog';
import { useAdminAuthStore } from '../../stores/adminAuthStore';

export const AdminKnowledgePage: React.FC = () => {
  const queryClient = useQueryClient();
  const { canManageKnowledge } = useAdminAuthStore();

  const [isBuildModalOpen, setIsBuildModalOpen] = useState(false);
  const [description, setDescription] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [genToPromote, setGenToPromote] = useState<KnowledgeGeneration | null>(null);
  const [genToRollback, setGenToRollback] = useState<KnowledgeGeneration | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: genData, isLoading: genLoading } = useQuery({
    queryKey: ['admin', 'generations'],
    queryFn: () => fetchGenerations(0, 50),
  });

  const { data: docData } = useQuery({
    queryKey: ['admin', 'documents', 'selector'],
    queryFn: () => fetchDocuments(0, 100),
    enabled: isBuildModalOpen,
  });

  const buildMutation = useMutation({
    mutationFn: () =>
      buildKnowledgeGeneration({
        description: description.trim() || undefined,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      }),
    onSuccess: (res) => {
      setSuccessMessage(`Knowledge generation ${res.generation_version} build initiated successfully.`);
      setIsBuildModalOpen(false);
      setDescription('');
      setSelectedDocIds([]);
      queryClient.invalidateQueries({ queryKey: ['admin', 'generations'] });
    },
    onError: (err: Error) => {
      setErrorMessage(err.message);
    },
  });

  const promoteMutation = useMutation({
    mutationFn: (id: string) => promoteGeneration(id),
    onSuccess: (res) => {
      setSuccessMessage(res.message);
      setGenToPromote(null);
      queryClient.invalidateQueries({ queryKey: ['admin', 'generations'] });
    },
    onError: (err: Error) => {
      setErrorMessage(err.message);
      setGenToPromote(null);
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: (id: string) => rollbackGeneration(id),
    onSuccess: (res) => {
      setSuccessMessage(res.message);
      setGenToRollback(null);
      queryClient.invalidateQueries({ queryKey: ['admin', 'generations'] });
    },
    onError: (err: Error) => {
      setErrorMessage(err.message);
      setGenToRollback(null);
    },
  });

  const activeGen = genData?.items.find((g) => g.is_active);

  const toggleDocSelection = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-serif font-bold text-[var(--color-text)]">
            Knowledge Base Generations
          </h2>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1">
            Immutable, versioned multi-stage vector and BM25 search indices.
          </p>
        </div>

        {canManageKnowledge() && (
          <button
            type="button"
            onClick={() => setIsBuildModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-[var(--color-gold)] hover:bg-[var(--color-gold-dark)] text-stone-950 font-semibold text-xs transition-all flex items-center gap-2 shadow-sm"
          >
            <Sparkles className="w-4 h-4" />
            <span>Build New Generation</span>
          </button>
        )}
      </div>

      {/* Notifications */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-red-500 hover:underline text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            className="text-emerald-500 hover:underline text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Authoritative Active Generation Banner */}
      {activeGen && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-gold)]/40 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-3 border-b border-[var(--color-border)] pb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-[var(--color-gold)]/15 text-[var(--color-gold)]">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-[var(--color-gold)] block">
                  Authoritative Active Corpus
                </span>
                <span className="font-mono text-base font-bold text-[var(--color-text)]">
                  {activeGen.generation_version}
                </span>
              </div>
            </div>
            <StatusBadge status="ACTIVE" isActive={true} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
              <span className="text-[var(--color-text-secondary)] block mb-1">Source PDFs</span>
              <span className="font-semibold text-[var(--color-text)]">
                {activeGen.document_count} Documents
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
              <span className="text-[var(--color-text-secondary)] block mb-1">Total Chunks</span>
              <span className="font-semibold text-[var(--color-text)]">
                {activeGen.chunk_count} Chunks
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
              <span className="text-[var(--color-text-secondary)] block mb-1">Embedding Engine</span>
              <span className="font-medium text-[var(--color-text)]">
                {activeGen.embedding_model}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
              <span className="text-[var(--color-text-secondary)] block mb-1">Promoted At</span>
              <span className="font-medium text-[var(--color-text)]">
                {activeGen.promoted_at ? new Date(activeGen.promoted_at).toLocaleString() : 'Initial'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Generations Table */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between">
          <h3 className="font-serif font-bold text-sm text-[var(--color-text)]">
            Generation History
          </h3>
          <span className="text-xs text-[var(--color-text-secondary)]">
            {genData?.items.length ?? 0} Recorded Generations
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[var(--color-bg)] border-b border-[var(--color-border)] text-[var(--color-text-secondary)] font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3 px-4">Version</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Documents</th>
                <th className="py-3 px-4">Chunks</th>
                <th className="py-3 px-4">Created</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {genLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[var(--color-text-secondary)]">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-[var(--color-gold)]" />
                    Loading knowledge generations...
                  </td>
                </tr>
              ) : (genData?.items || []).length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[var(--color-text-secondary)]">
                    <Layers className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    No knowledge generations found.
                  </td>
                </tr>
              ) : (
                (genData?.items || []).map((gen) => (
                  <tr key={gen.id} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                    <td className="py-3.5 px-4 font-mono font-medium text-[var(--color-text)]">
                      <div className="flex items-center gap-2">
                        <span>{gen.generation_version}</span>
                        {gen.is_active && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                            ACTIVE
                          </span>
                        )}
                      </div>
                      {gen.description && (
                        <p className="text-[11px] font-sans text-[var(--color-text-secondary)] truncate max-w-xs mt-0.5">
                          {gen.description}
                        </p>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={gen.status} />
                    </td>
                    <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                      {gen.document_count}
                    </td>
                    <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                      {gen.chunk_count}
                    </td>
                    <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3 h-3 text-[var(--color-text-secondary)]/60" />
                        <span>{new Date(gen.created_at).toLocaleDateString()}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Inspect Stages */}
                        <Link
                          to={`/admin/knowledge/${gen.id}`}
                          title="View build stages"
                          aria-label={`Inspect ${gen.generation_version}`}
                          className="p-1.5 rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg)] transition-colors"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </Link>

                        {/* Promote to Active */}
                        {canManageKnowledge() && !gen.is_active && gen.status === 'VALIDATED' && (
                          <button
                            type="button"
                            onClick={() => setGenToPromote(gen)}
                            title="Promote to Active"
                            aria-label={`Promote ${gen.generation_version}`}
                            className="px-2.5 py-1 rounded-lg text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 font-medium text-[11px] transition-colors flex items-center gap-1"
                          >
                            <ArrowUpCircle className="w-3 h-3" />
                            <span>Promote</span>
                          </button>
                        )}

                        {/* Rollback to previous valid generation */}
                        {canManageKnowledge() && !gen.is_active && (gen.status === 'ACTIVE' || gen.status === 'VALIDATED') && (
                          <button
                            type="button"
                            onClick={() => setGenToRollback(gen)}
                            title="Rollback to this generation"
                            aria-label={`Rollback to ${gen.generation_version}`}
                            className="px-2.5 py-1 rounded-lg text-amber-600 dark:text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 font-medium text-[11px] transition-colors flex items-center gap-1"
                          >
                            <RotateCcw className="w-3 h-3" />
                            <span>Rollback</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Build Generation Modal */}
      {isBuildModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
        >
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-lg w-full p-6 shadow-2xl animate-scale-in text-left">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-[var(--color-gold)]/15 text-[var(--color-gold)] flex items-center justify-center">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-serif font-bold text-[var(--color-text)]">
                  Trigger Knowledge Build
                </h3>
                <p className="text-xs text-[var(--color-text-secondary)]">
                  Extracts text, builds semantic chunks, generates embeddings, and verifies index.
                </p>
              </div>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label
                  htmlFor="gen-desc"
                  className="block text-xs font-semibold text-[var(--color-text)] mb-1"
                >
                  Version Description (Optional)
                </label>
                <input
                  id="gen-desc"
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Hoysala architecture expansion v2"
                  className="w-full px-3 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs text-[var(--color-text)] focus:outline-none focus:border-[var(--color-gold)]"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-[var(--color-text)]">
                    Select Target Documents
                  </label>
                  <span className="text-[11px] text-[var(--color-text-secondary)]">
                    {selectedDocIds.length === 0
                      ? 'All eligible PDFs'
                      : `${selectedDocIds.length} selected`}
                  </span>
                </div>
                <div className="max-h-48 overflow-y-auto space-y-1.5 border border-[var(--color-border)] rounded-xl p-2 bg-[var(--color-bg)]">
                  {(docData?.items || []).map((doc) => (
                    <label
                      key={doc.id}
                      className="flex items-center gap-2 p-2 rounded-lg hover:bg-[var(--color-surface)] cursor-pointer text-xs transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={selectedDocIds.includes(doc.id)}
                        onChange={() => toggleDocSelection(doc.id)}
                        className="rounded border-[var(--color-border)] text-[var(--color-gold)] focus:ring-0"
                      />
                      <FileText className="w-3.5 h-3.5 text-[var(--color-gold)] shrink-0" />
                      <span className="truncate flex-1 text-[var(--color-text)]">
                        {doc.original_name}
                      </span>
                      <span className="text-[10px] text-[var(--color-text-secondary)] shrink-0">
                        {(doc.file_size_bytes / (1024 * 1024)).toFixed(1)} MB
                      </span>
                    </label>
                  ))}
                </div>
                <p className="text-[11px] text-[var(--color-text-secondary)] mt-1">
                  If no documents are selected, all valid uploaded PDF guidebooks will be indexed.
                </p>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={buildMutation.isPending}
                onClick={() => setIsBuildModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={buildMutation.isPending}
                onClick={() => buildMutation.mutate()}
                className="px-4 py-2 rounded-xl bg-[var(--color-gold)] hover:bg-[var(--color-gold-dark)] text-stone-950 text-xs font-semibold flex items-center gap-2 shadow-sm disabled:opacity-50"
              >
                {buildMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Initiating Build...</span>
                  </>
                ) : (
                  <span>Start Knowledge Build</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Promotion Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!genToPromote}
        title="Promote Knowledge Generation to Active?"
        message={
          genToPromote
            ? `Promote generation ${genToPromote.generation_version} to ACTIVE? All tourist inquiries will immediately use this knowledge base for grounded retrieval.`
            : ''
        }
        confirmLabel="Promote to Active"
        isLoading={promoteMutation.isPending}
        onConfirm={() => {
          if (genToPromote) promoteMutation.mutate(genToPromote.id);
        }}
        onCancel={() => setGenToPromote(null)}
      />

      {/* Rollback Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!genToRollback}
        title="Rollback Active Knowledge Base?"
        message={
          genToRollback
            ? `Rollback the active knowledge base to generation ${genToRollback.generation_version}?`
            : ''
        }
        confirmLabel="Rollback Index"
        isDestructive={false}
        isLoading={rollbackMutation.isPending}
        onConfirm={() => {
          if (genToRollback) rollbackMutation.mutate(genToRollback.id);
        }}
        onCancel={() => setGenToRollback(null)}
      />
    </div>
  );
};
