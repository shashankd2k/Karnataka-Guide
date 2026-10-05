import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  Server,
  Database,
  Cpu,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { fetchSystemHealth } from '../../services/adminApiClient';

export const AdminSystemPage: React.FC = () => {
  const { data, isLoading, isRefetching, refetch, error } = useQuery({
    queryKey: ['admin', 'system-health'],
    queryFn: fetchSystemHealth,
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-serif font-bold text-[var(--color-text)]">
            System Status & Health
          </h2>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1">
            Real-time health probes and platform deployment configuration.
          </p>
        </div>

        <button
          type="button"
          disabled={isRefetching || isLoading}
          onClick={() => refetch()}
          className="px-3.5 py-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text)] hover:border-[var(--color-gold)] transition-colors flex items-center gap-2 self-start sm:self-auto disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-[var(--color-gold)] ${isRefetching ? 'animate-spin' : ''}`} />
          <span>Refresh Probes</span>
        </button>
      </div>

      {isLoading ? (
        <div className="py-16 text-center text-[var(--color-text-secondary)]">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-[var(--color-gold)]" />
          <p className="text-xs">Executing health check telemetry...</p>
        </div>
      ) : error || !data ? (
        <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>Failed to communicate with the system health probe endpoint.</span>
        </div>
      ) : (
        <>
          {/* Main Health Status Banner */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[var(--color-gold)]/15 text-[var(--color-gold)] flex items-center justify-center">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-serif font-bold text-base text-[var(--color-text)]">
                    API v1 Telemetry Probe
                  </h3>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Server Timestamp: {new Date(data.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>

              <div>
                {data.status === 'healthy' ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>System Healthy (200 OK)</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>System Degraded (503 Service Unavailable)</span>
                  </span>
                )}
              </div>
            </div>

            {/* Platform Metadata (Server Authoritative) */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">Application Version</span>
                <span className="font-mono font-bold text-[var(--color-text)] text-sm">
                  {data.app_version}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">API Version</span>
                <span className="font-mono font-bold text-[var(--color-text)] text-sm">
                  {data.api_version}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">Deployment Profile</span>
                <span className="font-semibold text-[var(--color-gold)] uppercase tracking-wider text-xs">
                  {data.profile}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">Database Subsystem</span>
                <span
                  className={`font-semibold capitalize ${
                    data.subsystems.database === 'healthy' ? 'text-emerald-500' : 'text-red-500'
                  }`}
                >
                  {data.subsystems.database}
                </span>
              </div>
            </div>
          </div>

          {/* Subsystems Live Table */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-[var(--color-border)]">
              <h3 className="font-serif font-bold text-sm text-[var(--color-text)] flex items-center gap-2">
                <Server className="w-4 h-4 text-[var(--color-gold)]" />
                <span>Backend Subsystem Probes</span>
              </h3>
            </div>

            <div className="divide-y divide-[var(--color-border)] text-xs">
              <div className="p-4 flex items-center justify-between hover:bg-[var(--color-surface-hover)] transition-colors">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[var(--color-gold)]/10 text-[var(--color-gold)]">
                    <Server className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-semibold text-[var(--color-text)] block">
                      FastAPI Application Core
                    </span>
                    <span className="text-[11px] text-[var(--color-text-secondary)]">
                      ASGI request routing, authentication gateway, SSE streaming, and middleware
                    </span>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>{data.subsystems.app}</span>
                </span>
              </div>

              <div className="p-4 flex items-center justify-between hover:bg-[var(--color-surface-hover)] transition-colors">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[var(--color-gold)]/10 text-[var(--color-gold)]">
                    <Database className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-semibold text-[var(--color-text)] block">
                      MySQL 8.0 Primary Store
                    </span>
                    <span className="text-[11px] text-[var(--color-text-secondary)]">
                      Relational storage for admin accounts, session history, metadata, and audit events
                    </span>
                  </div>
                </div>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold ${
                    data.subsystems.database === 'healthy'
                      ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                      : 'bg-red-500/10 text-red-500 border border-red-500/20'
                  }`}
                >
                  {data.subsystems.database === 'healthy' ? (
                    <CheckCircle2 className="w-3 h-3" />
                  ) : (
                    <AlertTriangle className="w-3 h-3" />
                  )}
                  <span>{data.subsystems.database}</span>
                </span>
              </div>
            </div>
          </div>

          {/* Static Offline AI Stack Architectural Profile (Accurately documented as reference information) */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Cpu className="w-4 h-4 text-[var(--color-gold)]" />
              <h3 className="font-serif font-bold text-sm text-[var(--color-text)]">
                Platform Architecture — Configured AI Components
              </h3>
            </div>
            <p className="text-xs text-[var(--color-text-secondary)] mb-4">
              Reference information — not live health telemetry. Integrated offline multi-modal AI components:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-gold)] font-bold block mb-1">LLM Generation</span>
                <span className="font-semibold text-[var(--color-text)] block">Ollama (qwen2.5:3b)</span>
                <span className="text-[10px] text-[var(--color-text-secondary)] mt-0.5 block">
                  Local GGUF offline inference
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-gold)] font-bold block mb-1">Speech Recognition</span>
                <span className="font-semibold text-[var(--color-text)] block">Faster-Whisper</span>
                <span className="text-[10px] text-[var(--color-text-secondary)] mt-0.5 block">
                  CTranslate2 English/Kannada STT
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-gold)] font-bold block mb-1">English TTS</span>
                <span className="font-semibold text-[var(--color-text)] block">Piper TTS (22.05 kHz)</span>
                <span className="text-[10px] text-[var(--color-text-secondary)] mt-0.5 block">
                  Low-latency voice synthesis
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-gold)] font-bold block mb-1">Kannada TTS</span>
                <span className="font-semibold text-[var(--color-text)] block">Meta MMS-TTS (16.0 kHz)</span>
                <span className="text-[10px] text-[var(--color-text-secondary)] mt-0.5 block">
                  Native VITS synthesis for Kannada
                </span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
