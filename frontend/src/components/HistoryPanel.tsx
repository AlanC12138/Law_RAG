import { useEffect, useState } from 'react'
import { queryApi } from '../api/query'
import type { Matter, QueryLog } from '../types'

interface HistoryPanelProps {
  matter: Matter
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) +
    '  ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export default function HistoryPanel({ matter }: HistoryPanelProps) {
  const [logs, setLogs] = useState<QueryLog[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setExpanded(null)
    queryApi
      .fetchLogs(matter.id)
      .then(setLogs)
      .catch(() => setError('Failed to load history'))
      .finally(() => setLoading(false))
  }, [matter.id])

  if (loading) {
    return (
      <div className="px-6 py-6 space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-blue-50 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-6 py-6">
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 rounded-xl">{error}</div>
      </div>
    )
  }

  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center py-16 px-6">
        <div className="w-14 h-14 rounded-2xl bg-blue-100 flex items-center justify-center mb-4">
          <svg className="w-7 h-7 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <h3 className="text-base font-semibold text-slate-700 mb-1">No queries yet</h3>
        <p className="text-sm text-slate-400 max-w-xs">
          Questions you ask in the Chat tab are saved here for future reference.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto px-6 py-6 space-y-3">
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-1">
        {logs.length} past quer{logs.length === 1 ? 'y' : 'ies'} — most recent first
      </p>

      {logs.map((log) => (
        <div
          key={log.id}
          className="bg-white border border-blue-100 rounded-xl overflow-hidden hover:border-blue-300 transition-colors"
        >
          {/* Question row — always visible, click to expand */}
          <button
            onClick={() => setExpanded(expanded === log.id ? null : log.id)}
            className="w-full text-left px-4 py-3 flex items-start gap-3 bg-white hover:bg-blue-50 transition-colors"
          >
            <div className="shrink-0 w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center mt-0.5">
              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 line-clamp-2">{log.query}</p>
              <p className="text-xs text-slate-400 mt-0.5">{formatDate(log.created_at)}</p>
            </div>
            <svg
              className={`shrink-0 w-4 h-4 text-slate-400 transition-transform mt-1 ${expanded === log.id ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Answer — expanded */}
          {expanded === log.id && (
            <div className="border-t border-blue-50 bg-blue-50 px-4 py-3">
              <div className="flex items-start gap-3">
                <div className="shrink-0 w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center mt-0.5">
                  <svg className="w-3 h-3 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                </div>
                <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{log.answer}</p>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
