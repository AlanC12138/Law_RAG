import { useEffect, useRef, useState } from 'react'
import { documentsApi } from '../api/documents'
import UploadDropzone from './UploadDropzone'
import type { Document, Matter } from '../types'

interface DocumentsPanelProps {
  matter: Matter
}

// Friendly display labels for extracted clause keys
const CLAUSE_LABELS: Record<string, string> = {
  document_type:   'Type',
  parties:         'Parties',
  effective_date:  'Effective',
  expiry_date:     'Expires',
  governing_law:   'Law',
  termination:     'Termination',
  key_obligations: 'Obligations',
}

function ClausePills({ clauses }: { clauses: Record<string, string | string[]> }) {
  const entries = Object.entries(clauses).filter(([, v]) =>
    Array.isArray(v) ? v.length > 0 : Boolean(v)
  )
  if (entries.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([key, value]) => {
        const label = CLAUSE_LABELS[key] ?? key
        const display = Array.isArray(value) ? value.join(', ') : String(value)
        return (
          <span
            key={key}
            className="inline-flex items-center gap-1 text-xs bg-blue-50 text-blue-700 border border-blue-100 rounded-full px-2.5 py-0.5 max-w-[260px]"
            title={display}
          >
            <span className="font-semibold shrink-0">{label}:</span>
            <span className="truncate">{display}</span>
          </span>
        )
      })}
    </div>
  )
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
  // Tracks whether we've already fired the post-processing grace poll
  const gracePolled = useRef(false)

  useEffect(() => {
    gracePolled.current = false
    loadDocuments()
  }, [matter.id])

  // Poll while any document is pending/processing, then do one grace poll
  // 5 s after processing finishes to capture summary/clauses written after
  // the status flips to 'ready'.
  useEffect(() => {
    const hasActive = documents.some(
      (d) => d.status === 'pending' || d.status === 'processing'
    )
    if (hasActive) {
      gracePolled.current = false
      const timer = setInterval(loadDocuments, 3000)
      return () => clearInterval(timer)
    }
    if (!gracePolled.current) {
      gracePolled.current = true
      const timer = setTimeout(loadDocuments, 5000)
      return () => clearTimeout(timer)
    }
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
                  className="bg-white border border-blue-100 rounded-xl px-4 py-3 group hover:border-blue-300 transition-colors"
                >
                  {/* Top row: icon + name + status + delete */}
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
                      <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-700 truncate">{doc.filename}</p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {doc.file_type.toUpperCase()}
                        {doc.page_count > 0 && ` · ${doc.page_count} pages`}
                      </p>
                    </div>

                    <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full shrink-0 ${cfg.className}`}>
                      {cfg.label}
                    </span>

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

                  {/* Enrichment — shown once the document is ready */}
                  {doc.status === 'ready' && (doc.summary || doc.clauses) && (
                    <div className="mt-2 border-t border-slate-100 pt-2 space-y-2">
                      {doc.summary && (
                        <p className="text-xs text-slate-500 leading-relaxed">{doc.summary}</p>
                      )}
                      {doc.clauses && Object.keys(doc.clauses).length > 0 && (
                        <ClausePills clauses={doc.clauses} />
                      )}
                    </div>
                  )}
                  {doc.status === 'processing' && (
                    <p className="mt-2 text-xs text-blue-400 animate-pulse border-t border-slate-100 pt-2">
                      Analysing document…
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
