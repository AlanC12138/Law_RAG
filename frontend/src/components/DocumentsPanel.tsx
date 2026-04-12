import { useEffect, useState } from 'react'
import { documentsApi } from '../api/documents'
import UploadDropzone from './UploadDropzone'
import type { Document, Matter } from '../types'

interface DocumentsPanelProps {
  matter: Matter
}

const STATUS_CONFIG = {
  pending:    { label: 'Pending',    className: 'bg-slate-100 text-slate-500' },
  processing: { label: 'Processing', className: 'bg-blue-100 text-blue-600 animate-pulse' },
  ready:      { label: 'Ready',      className: 'bg-green-100 text-green-700' },
  failed:     { label: 'Failed',     className: 'bg-red-100 text-red-600' },
}

export default function DocumentsPanel({ matter }: DocumentsPanelProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    loadDocuments()
  }, [matter.id])

  // Poll for status updates while any document is still processing
  useEffect(() => {
    const hasActive = documents.some(
      (d) => d.status === 'pending' || d.status === 'processing'
    )
    if (!hasActive) return
    const timer = setInterval(loadDocuments, 3000)
    return () => clearInterval(timer)
  }, [documents])

  const loadDocuments = async () => {
    try {
      const docs = await documentsApi.list(matter.id)
      setDocuments(docs)
      setError('')
    } catch {
      setError('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (files: File[]) => {
    setUploading(true)
    setError('')
    try {
      await Promise.all(files.map((f) => documentsApi.upload(matter.id, f)))
      await loadDocuments()
    } catch {
      setError('Upload failed. Check file type and try again.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (docId: string) => {
    if (!confirm('Remove this document? This cannot be undone.')) return
    try {
      await documentsApi.remove(matter.id, docId)
      setDocuments((prev) => prev.filter((d) => d.id !== docId))
    } catch {
      setError('Failed to delete document')
    }
  }

  const ready = documents.filter((d) => d.status === 'ready').length

  return (
    <div className="flex flex-col h-full overflow-y-auto px-6 py-6 space-y-6">
      {/* Upload zone */}
      <UploadDropzone onUpload={handleUpload} uploading={uploading} />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 rounded-xl">
          {error}
        </div>
      )}

      {/* Document list */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-700">
            Documents
          </h3>
          {!loading && (
            <span className="text-xs text-slate-400">
              {ready} of {documents.length} indexed
            </span>
          )}
        </div>

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 bg-blue-50 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-10">
            <p className="text-sm text-slate-400">No documents yet — upload some above</p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => {
              const cfg = STATUS_CONFIG[doc.status] ?? STATUS_CONFIG.pending
              return (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 bg-white border border-blue-100 rounded-xl px-4 py-3 group hover:border-blue-300 transition-colors"
                >
                  {/* File icon */}
                  <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
                    <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                  </div>

                  {/* Name + meta */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-700 truncate">{doc.filename}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {doc.file_type.toUpperCase()}
                      {doc.page_count > 0 && ` · ${doc.page_count} pages`}
                    </p>
                  </div>

                  {/* Status badge */}
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full shrink-0 ${cfg.className}`}>
                    {cfg.label}
                  </span>

                  {/* Delete */}
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="shrink-0 w-6 h-6 flex items-center justify-center rounded text-slate-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                    title="Remove document"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
