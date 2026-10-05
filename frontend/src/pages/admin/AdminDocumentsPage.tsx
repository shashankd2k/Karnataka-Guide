import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Upload,
  Download,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Search,
  FileCheck,
  Loader2,
  Eye,
} from 'lucide-react';
import {
  fetchDocuments,
  uploadDocument,
  downloadDocumentPdf,
  deleteDocument,
} from '../../services/adminApiClient';
import { DocumentItem } from '../../types/admin';
import { StatusBadge } from '../../components/admin/StatusBadge';
import { ConfirmDialog } from '../../components/admin/ConfirmDialog';
import { useAdminAuthStore } from '../../stores/adminAuthStore';

export const AdminDocumentsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { canManageDocuments } = useAdminAuthStore();

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [docToDelete, setDocToDelete] = useState<DocumentItem | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDownloadingId, setIsDownloadingId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'documents'],
    queryFn: () => fetchDocuments(0, 100),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      setSuccessMessage('Document deleted successfully.');
      setDocToDelete(null);
      queryClient.invalidateQueries({ queryKey: ['admin', 'documents'] });
    },
    onError: (err: Error) => {
      setErrorMessage(err.message);
      setDocToDelete(null);
    },
  });

  const handleFileUpload = async (file: File) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    // Client-side validations
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Validation Error: Only PDF documents are supported.');
      return;
    }

    const MAX_SIZE = 50 * 1024 * 1024; // 50 MB
    if (file.size > MAX_SIZE) {
      setErrorMessage('Validation Error: File size exceeds the 50 MB limit.');
      return;
    }

    setIsUploading(true);
    try {
      const result = await uploadDocument(file);
      setSuccessMessage(`Document "${result.original_name}" uploaded successfully.`);
      queryClient.invalidateQueries({ queryKey: ['admin', 'documents'] });
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to upload document.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownload = async (doc: DocumentItem) => {
    setIsDownloadingId(doc.id);
    try {
      await downloadDocumentPdf(doc.id, doc.original_name);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      }
    } finally {
      setIsDownloadingId(null);
    }
  };

  const filteredDocs = (data?.items || []).filter(
    (d) =>
      d.original_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.sha256_hash.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-serif font-bold text-[var(--color-text)]">
            Heritage Documents
          </h2>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1">
            Source PDF guidebooks and historical texts for knowledge base ingestion.
          </p>
        </div>
        <div className="text-xs font-semibold text-[var(--color-text-secondary)]">
          Total Documents: <span className="text-[var(--color-text)]">{data?.total ?? 0}</span>
        </div>
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

      {/* Upload Zone (Curators and Super Admin only) */}
      {canManageDocuments() && (
        <div className="bg-[var(--color-surface)] border border-dashed border-[var(--color-border)] rounded-2xl p-6 text-center hover:border-[var(--color-gold)] transition-colors">
          <input
            type="file"
            id="pdf-upload"
            accept=".pdf,application/pdf"
            disabled={isUploading}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileUpload(file);
              e.target.value = '';
            }}
            className="hidden"
          />
          <label
            htmlFor="pdf-upload"
            className="cursor-pointer flex flex-col items-center justify-center gap-2"
          >
            <div className="w-12 h-12 rounded-2xl bg-[var(--color-gold)]/10 text-[var(--color-gold)] flex items-center justify-center">
              {isUploading ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <Upload className="w-6 h-6" />
              )}
            </div>
            <div>
              <span className="text-xs font-semibold text-[var(--color-text)] hover:underline">
                {isUploading ? 'Uploading PDF Document...' : 'Click to select or drag a heritage PDF guidebook'}
              </span>
              <p className="text-[11px] text-[var(--color-text-secondary)] mt-0.5">
                Maximum file size: 50 MB • Validated cryptographic SHA-256 deduplication
              </p>
            </div>
          </label>
        </div>
      )}

      {/* Search Bar */}
      <div className="flex items-center gap-3 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-3 py-2">
        <Search className="w-4 h-4 text-[var(--color-text-secondary)]" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Filter documents by filename or checksum..."
          className="bg-transparent border-none text-xs text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)]/50 focus:outline-none w-full"
        />
      </div>

      {/* Documents Table */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[var(--color-bg)] border-b border-[var(--color-border)] text-[var(--color-text-secondary)] font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3 px-4">Document Title</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">Pages</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Uploaded</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[var(--color-text-secondary)]">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-[var(--color-gold)]" />
                    Loading documents...
                  </td>
                </tr>
              ) : filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[var(--color-text-secondary)]">
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    No documents found.
                  </td>
                </tr>
              ) : (
                filteredDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                    <td className="py-3.5 px-4 font-medium text-[var(--color-text)]">
                      <div className="flex items-center gap-2">
                        <FileCheck className="w-4 h-4 text-[var(--color-gold)] shrink-0" />
                        <span className="truncate max-w-xs">{doc.original_name}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                      {(doc.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                    </td>
                    <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                      {doc.page_count > 0 ? doc.page_count : '—'}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Details Modal Trigger */}
                        <button
                          type="button"
                          onClick={() => setSelectedDoc(doc)}
                          title="View metadata"
                          aria-label={`Inspect ${doc.original_name}`}
                          className="p-1.5 rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg)] transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>

                        {/* Authenticated Download */}
                        <button
                          type="button"
                          disabled={isDownloadingId === doc.id}
                          onClick={() => handleDownload(doc)}
                          title="Download PDF"
                          aria-label={`Download ${doc.original_name}`}
                          className="p-1.5 rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-gold)] hover:bg-[var(--color-bg)] transition-colors disabled:opacity-50"
                        >
                          {isDownloadingId === doc.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Download className="w-3.5 h-3.5" />
                          )}
                        </button>

                        {/* Delete Trigger (Curators/SuperAdmin only) */}
                        {canManageDocuments() && (
                          <button
                            type="button"
                            onClick={() => setDocToDelete(doc)}
                            title="Delete document"
                            aria-label={`Delete ${doc.original_name}`}
                            className="p-1.5 rounded-lg text-[var(--color-text-secondary)] hover:text-red-500 hover:bg-red-500/10 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
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

      {/* Metadata Slide-over / Modal */}
      {selectedDoc && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
        >
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-lg w-full p-6 shadow-2xl animate-scale-in">
            <h3 className="text-lg font-serif font-bold text-[var(--color-text)] mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-[var(--color-gold)]" />
              <span>Document Metadata</span>
            </h3>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">Original Filename</span>
                <span className="font-semibold text-[var(--color-text)] break-all">
                  {selectedDoc.original_name}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">SHA-256 Checksum</span>
                <span className="font-mono text-[11px] text-[var(--color-text)] break-all">
                  {selectedDoc.sha256_hash}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                  <span className="text-[var(--color-text-secondary)] block mb-1">Size</span>
                  <span className="font-semibold text-[var(--color-text)]">
                    {(selectedDoc.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                  <span className="text-[var(--color-text-secondary)] block mb-1">Status</span>
                  <StatusBadge status={selectedDoc.status} />
                </div>
              </div>
              <div className="p-3 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)] block mb-1">System Storage Identifier</span>
                <span className="font-mono text-[11px] text-[var(--color-text)] break-all">
                  {selectedDoc.id}
                </span>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedDoc(null)}
                className="px-4 py-2 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs font-semibold text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!docToDelete}
        title="Delete Heritage Document?"
        message={
          docToDelete
            ? `Are you sure you want to delete "${docToDelete.original_name}"? If this document belongs to an ACTIVE knowledge generation, deletion will be rejected to protect index integrity.`
            : ''
        }
        confirmLabel="Delete Document"
        isDestructive={true}
        isLoading={deleteMutation.isPending}
        onConfirm={() => {
          if (docToDelete) deleteMutation.mutate(docToDelete.id);
        }}
        onCancel={() => setDocToDelete(null)}
      />
    </div>
  );
};
