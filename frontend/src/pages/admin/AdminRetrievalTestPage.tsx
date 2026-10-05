import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  SearchCode,
  Sliders,
  Zap,
  Layers,
  FileText,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { testRetrievalDiagnostic } from '../../services/adminApiClient';
import {
  RetrievalDiagnosticRequest,
  RetrievalDiagnosticResponse,
  RetrievalCandidate,
} from '../../types/admin';

export const AdminRetrievalTestPage: React.FC = () => {
  const [query, setQuery] = useState('Who commissioned the Belur Chennakeshava temple?');
  const [topK, setTopK] = useState(5);
  const [enableReranker, setEnableReranker] = useState(true);
  const [filterNoise, setFilterNoise] = useState(true);
  const [suppressDuplicates, setSuppressDuplicates] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [denseTopK, setDenseTopK] = useState(25);
  const [bm25TopK, setBm25TopK] = useState(25);
  const [rerankCandidates, setRerankCandidates] = useState(15);

  const [diagnosticResult, setDiagnosticResult] = useState<RetrievalDiagnosticResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const diagnosticMutation = useMutation({
    mutationFn: (payload: RetrievalDiagnosticRequest) => testRetrievalDiagnostic(payload),
    onSuccess: (data) => {
      setDiagnosticResult(data);
      setErrorMessage(null);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message);
    },
  });

  const handleRunTest = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    diagnosticMutation.mutate({
      query: query.trim(),
      top_k: topK,
      enable_reranker: enableReranker,
      filter_noise: filterNoise,
      suppress_duplicates: suppressDuplicates,
      dense_top_k: showAdvanced ? denseTopK : undefined,
      bm25_top_k: showAdvanced ? bm25TopK : undefined,
      rerank_candidates: showAdvanced ? rerankCandidates : undefined,
    });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-serif font-bold text-[var(--color-text)]">
          RAG Retrieval Diagnostics
        </h2>
        <p className="text-xs text-[var(--color-text-secondary)] mt-1">
          Simulate multi-stage hybrid search against the active knowledge generation.
        </p>
      </div>

      {/* Query Control Panel */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
        <form onSubmit={handleRunTest} className="space-y-4">
          <div>
            <label
              htmlFor="diagnostic-query"
              className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-text)] mb-1.5"
            >
              Test Query (English or Kannada)
            </label>
            <div className="relative">
              <input
                id="diagnostic-query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. Madanika figures in Belur or ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ"
                className="w-full px-4 py-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)]/50 focus:outline-none focus:border-[var(--color-gold)]"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
            <div className="flex flex-wrap items-center gap-4 text-xs">
              <div>
                <label htmlFor="top-k" className="font-semibold text-[var(--color-text)] mr-2">
                  Top-K:
                </label>
                <input
                  id="top-k"
                  type="number"
                  min={1}
                  max={50}
                  value={topK}
                  onChange={(e) => setTopK(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-16 px-2 py-1 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-xs text-center"
                />
              </div>

              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableReranker}
                  onChange={(e) => setEnableReranker(e.target.checked)}
                  className="rounded border-[var(--color-border)] text-[var(--color-gold)]"
                />
                <span className="text-[var(--color-text-secondary)]">Cross-Encoder</span>
              </label>

              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filterNoise}
                  onChange={(e) => setFilterNoise(e.target.checked)}
                  className="rounded border-[var(--color-border)] text-[var(--color-gold)]"
                />
                <span className="text-[var(--color-text-secondary)]">Noise Filter</span>
              </label>

              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={suppressDuplicates}
                  onChange={(e) => setSuppressDuplicates(e.target.checked)}
                  className="rounded border-[var(--color-border)] text-[var(--color-gold)]"
                />
                <span className="text-[var(--color-text-secondary)]">Deduplicate</span>
              </label>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)] flex items-center gap-1"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>{showAdvanced ? 'Hide Advanced' : 'Advanced'}</span>
                {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>

              <button
                type="submit"
                disabled={diagnosticMutation.isPending || !query.trim()}
                className="px-5 py-2.5 rounded-xl bg-[var(--color-gold)] hover:bg-[var(--color-gold-dark)] text-stone-950 font-semibold text-xs transition-all flex items-center gap-2 shadow-sm disabled:opacity-50"
              >
                {diagnosticMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Retrieving...</span>
                  </>
                ) : (
                  <>
                    <SearchCode className="w-4 h-4" />
                    <span>Run Diagnostic</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Advanced Pipeline Tuning */}
          {showAdvanced && (
            <div className="p-4 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs animate-fade-in">
              <div>
                <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">
                  Dense Candidates (k):
                </label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={denseTopK}
                  onChange={(e) => setDenseTopK(parseInt(e.target.value) || 25)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs"
                />
              </div>
              <div>
                <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">
                  BM25 Candidates (k):
                </label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={bm25TopK}
                  onChange={(e) => setBm25TopK(parseInt(e.target.value) || 25)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs"
                />
              </div>
              <div>
                <label className="block text-[11px] text-[var(--color-text-secondary)] mb-1">
                  Rerank Candidates:
                </label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={rerankCandidates}
                  onChange={(e) => setRerankCandidates(parseInt(e.target.value) || 15)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs"
                />
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Results View */}
      {diagnosticResult && (
        <div className="space-y-6">
          {/* Telemetry Stage Breakdown */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4 border-b border-[var(--color-border)] pb-3">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-[var(--color-gold)]" />
                <h3 className="font-serif font-bold text-sm text-[var(--color-text)]">
                  Pipeline Telemetry & Stage Metrics
                </h3>
              </div>
              <span className="text-xs font-mono text-[var(--color-text-secondary)]">
                Generation: {diagnosticResult.active_generation_version || 'None'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-4">
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">Dense Vector</span>
                <span className="text-base font-bold text-[var(--color-text)]">
                  {diagnosticResult.dense_candidates_count} Candidates
                </span>
                <span className="text-[10px] text-[var(--color-text-secondary)] block mt-0.5">
                  {diagnosticResult.timings_ms.dense_ms.toFixed(1)} ms
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">BM25 Sparse</span>
                <span className="text-base font-bold text-[var(--color-text)]">
                  {diagnosticResult.bm25_candidates_count} Candidates
                </span>
                <span className="text-[10px] text-[var(--color-text-secondary)] block mt-0.5">
                  {diagnosticResult.timings_ms.bm25_ms.toFixed(1)} ms
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">RRF Fused</span>
                <span className="text-base font-bold text-[var(--color-text)]">
                  {diagnosticResult.fused_candidates_count} Candidates
                </span>
                <span className="text-[10px] text-[var(--color-text-secondary)] block mt-0.5">
                  {diagnosticResult.timings_ms.fusion_ms.toFixed(1)} ms
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">Total Latency</span>
                <span className="text-base font-bold text-[var(--color-gold)]">
                  {diagnosticResult.timings_ms.total_ms.toFixed(1)} ms
                </span>
                <span className="text-[10px] text-[var(--color-text-secondary)] block mt-0.5">
                  Rerank: {diagnosticResult.timings_ms.rerank_ms.toFixed(1)} ms
                </span>
              </div>
            </div>

            {diagnosticResult.diagnostic_notes && diagnosticResult.diagnostic_notes.length > 0 && (
              <div className="p-3 rounded-xl bg-[var(--color-bg)] text-[11px] text-[var(--color-text-secondary)] space-y-1">
                {diagnosticResult.diagnostic_notes.map((note, i) => (
                  <p key={i}>• {note}</p>
                ))}
              </div>
            )}
          </div>

          {/* Ranked Evidence Results */}
          <div className="space-y-3">
            <h3 className="font-serif font-bold text-sm text-[var(--color-text)] flex items-center gap-2">
              <Layers className="w-4 h-4 text-[var(--color-gold)]" />
              <span>Ranked Evidence Chunks ({diagnosticResult.results.length})</span>
            </h3>

            {diagnosticResult.results.length === 0 ? (
              <div className="p-8 text-center bg-[var(--color-surface)] rounded-2xl border border-[var(--color-border)] text-xs text-[var(--color-text-secondary)]">
                No matching evidence chunks passed retrieval criteria.
              </div>
            ) : (
              diagnosticResult.results.map((candidate: RetrievalCandidate) => (
                <div
                  key={candidate.chunk_id}
                  className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 shadow-sm space-y-2.5 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border)] pb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-[var(--color-gold)]/15 text-[var(--color-gold)] font-bold font-mono text-xs flex items-center justify-center">
                        #{candidate.final_rank}
                      </span>
                      <div className="flex items-center gap-1.5 font-medium text-[var(--color-text)]">
                        <FileText className="w-3.5 h-3.5 text-[var(--color-gold)]" />
                        <span>{candidate.source_filename}</span>
                        <span className="text-[var(--color-text-secondary)] font-normal">
                          (Page {candidate.page_number})
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 font-mono text-[10px] text-[var(--color-text-secondary)]">
                      {candidate.reranker_score !== null && candidate.reranker_score !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-[var(--color-bg)] border border-[var(--color-border)]">
                          Reranker: {candidate.reranker_score.toFixed(3)}
                        </span>
                      )}
                      {candidate.dense_score !== null && candidate.dense_score !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-[var(--color-bg)] border border-[var(--color-border)]">
                          Dense: {candidate.dense_score.toFixed(3)}
                        </span>
                      )}
                      {candidate.bm25_score !== null && candidate.bm25_score !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-[var(--color-bg)] border border-[var(--color-border)]">
                          BM25: {candidate.bm25_score.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </div>

                  {candidate.section && (
                    <div className="text-[11px] font-semibold text-[var(--color-gold)] uppercase tracking-wide">
                      Section: {candidate.section}
                    </div>
                  )}

                  <p className="text-xs text-[var(--color-text)] leading-relaxed bg-[var(--color-bg)] p-3 rounded-lg border border-[var(--color-border)] font-serif">
                    {candidate.text}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
