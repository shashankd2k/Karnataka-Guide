import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Languages,
  CheckCircle2,
  AlertTriangle,
  Info,
  Layers,
  ArrowRightLeft,
  Loader2,
} from 'lucide-react';
import { fetchTranslationRegistry } from '../../services/adminApiClient';
import { StatusBadge } from '../../components/admin/StatusBadge';

export const AdminTranslationsPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'translations'],
    queryFn: fetchTranslationRegistry,
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-serif font-bold text-[var(--color-text)]">
          Translation Model Registry
        </h2>
        <p className="text-xs text-[var(--color-text-secondary)] mt-1">
          Registered offline machine translation engines and language pairs.
        </p>
      </div>

      {isLoading ? (
        <div className="py-16 text-center text-[var(--color-text-secondary)]">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-[var(--color-gold)]" />
          <p className="text-xs">Checking translation provider health...</p>
        </div>
      ) : error || !data ? (
        <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>Failed to load translation registry and provider health status.</span>
        </div>
      ) : (
        <>
          {/* Provider Overview Card */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[var(--color-gold)]/15 text-[var(--color-gold)] flex items-center justify-center">
                  <Languages className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-serif font-bold text-base text-[var(--color-text)]">
                    NMT Engine: {data.provider_engine}
                  </h3>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Local neural machine translation for query and grounded response synthesis
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {data.provider_healthy ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Provider Healthy</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Provider Degraded</span>
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">
                  Supported Language Tags
                </span>
                <div className="flex items-center gap-2">
                  {data.supported_languages.map((lang) => (
                    <span
                      key={lang}
                      className="px-2 py-0.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] font-mono font-bold text-[var(--color-gold)]"
                    >
                      {lang}
                    </span>
                  ))}
                  <span className="text-[11px] text-[var(--color-text-secondary)]">
                    (English, Kannada)
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">
                  Model Checkpoint
                </span>
                <span className="font-mono text-[11px] text-[var(--color-text)]">
                  facebook/nllb-200-distilled-600M
                </span>
              </div>
            </div>
          </div>

          {/* Registered Translation Pairs Table */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between">
              <h3 className="font-serif font-bold text-sm text-[var(--color-text)] flex items-center gap-2">
                <Layers className="w-4 h-4 text-[var(--color-gold)]" />
                <span>Registered Language Directions ({data.translations.length})</span>
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--color-bg)] border-b border-[var(--color-border)] text-[var(--color-text-secondary)] font-semibold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Direction</th>
                    <th className="py-3 px-4">Engine</th>
                    <th className="py-3 px-4">Version</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Registry ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]">
                  {data.translations.map((pair) => (
                    <tr key={pair.id} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-[var(--color-text)]">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-[var(--color-bg)] border border-[var(--color-border)] font-mono text-[var(--color-gold)]">
                            {pair.source_lang}
                          </span>
                          <ArrowRightLeft className="w-3 h-3 text-[var(--color-text-secondary)]" />
                          <span className="px-2 py-0.5 rounded bg-[var(--color-bg)] border border-[var(--color-border)] font-mono text-[var(--color-gold)]">
                            {pair.target_lang}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-text-secondary)] font-mono">
                        {pair.engine}
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                        {pair.package_version}
                      </td>
                      <td className="py-3.5 px-4">
                        <StatusBadge
                          status={pair.is_active ? 'ACTIVE' : 'ARCHIVED'}
                          isActive={pair.is_active}
                        />
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[10px] text-[var(--color-text-secondary)] truncate max-w-xs">
                        {pair.id}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Academic / Research Scope Notice */}
          <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex items-start gap-3 text-xs text-[var(--color-text-secondary)]">
            <Info className="w-5 h-5 text-[var(--color-gold)] shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <span className="font-semibold text-[var(--color-text)] block mb-0.5">
                Licensing & Model Scope Notice
              </span>
              The NLLB-200 distilled 600M neural machine translation engine is provided under the CC-BY-NC 4.0 license and is intended for academic, research, and non-commercial development use. It operates entirely offline without external cloud translation API dependencies.
            </div>
          </div>
        </>
      )}
    </div>
  );
};
