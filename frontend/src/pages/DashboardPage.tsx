import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { mattersApi } from '../api/matters'
import { usersApi } from '../api/users'
import ChatPanel from '../components/ChatPanel'
import DocumentsPanel from '../components/DocumentsPanel'
import HistoryPanel from '../components/HistoryPanel'
import Sidebar from '../components/Sidebar'
import type { Matter, SourceReference, User } from '../types'

type Tab = 'chat' | 'documents' | 'history'

// ---------------------------------------------------------------------------
// New Matter modal (inline, partner only)
// ---------------------------------------------------------------------------
interface NewMatterModalProps {
  onCreated: (m: Matter) => void
  onClose: () => void
}

function NewMatterModal({ onCreated, onClose }: NewMatterModalProps) {
  const [form, setForm] = useState({ name: '', client_name: '', jurisdiction: '', description: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const overlayRef = useRef<HTMLDivElement>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const matter = await mattersApi.create(form)
      onCreated(matter)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to create matter')
      setSaving(false)
    }
  }

  return (
    <div
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose() }}
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4"
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-base font-semibold text-slate-800 mb-4">New Matter</h2>
        {error && <p className="text-xs text-red-500 mb-3">{error}</p>}
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            required
            placeholder="Matter name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
          />
          <input
            required
            placeholder="Client name"
            value={form.client_name}
            onChange={(e) => setForm({ ...form, client_name: e.target.value })}
            className="w-full text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
          />
          <input
            placeholder="Jurisdiction (optional)"
            value={form.jurisdiction}
            onChange={(e) => setForm({ ...form, jurisdiction: e.target.value })}
            className="w-full text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
          />
          <textarea
            placeholder="Description (optional)"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={2}
            className="w-full text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white resize-none"
          />
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 text-sm bg-blue-600 text-white py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium transition-colors"
            >
              {saving ? 'Creating…' : 'Create Matter'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="text-sm bg-white text-slate-500 hover:text-slate-700 px-4 py-2.5 rounded-lg border border-slate-200 hover:border-slate-300 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// DashboardPage
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [matters, setMatters] = useState<Matter[]>([])
  const [selectedMatter, setSelectedMatter] = useState<Matter | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [loadingMatters, setLoadingMatters] = useState(true)
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [showNewMatter, setShowNewMatter] = useState(false)
  const [highlightDocId, setHighlightDocId] = useState<string | null>(null)
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const init = async () => {
      try {
        const [me, matterList] = await Promise.all([usersApi.me(), mattersApi.list()])
        setCurrentUser(me)
        setMatters(matterList)
      } catch (err: any) {
        if (err?.response?.status === 401) navigate('/login')
      } finally {
        setLoadingMatters(false)
      }
    }
    init()
  }, [navigate])

  const handleSelectMatter = (matter: Matter) => {
    setSelectedMatter(matter)
    setActiveTab('chat')
  }

  const handleMatterCreated = (matter: Matter) => {
    setMatters((prev) => [...prev, matter])
    setSelectedMatter(matter)
    setShowNewMatter(false)
    setActiveTab('chat')
  }

  const handleSourceClick = (src: SourceReference) => {
    setActiveTab('documents')
    setHighlightDocId(src.doc_id)
    if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current)
    highlightTimerRef.current = setTimeout(() => setHighlightDocId(null), 3000)
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/login')
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    {
      id: 'chat',
      label: 'Chat',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      ),
    },
    {
      id: 'documents',
      label: 'Documents',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      ),
    },
    {
      id: 'history',
      label: 'History',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
    },
  ]

  return (
    <div className="flex flex-col h-screen bg-blue-50 overflow-hidden">

      {/* Header */}
      <header className="shrink-0 bg-blue-900 text-white px-5 h-14 flex items-center justify-between shadow-md z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"
              />
            </svg>
          </div>
          <span className="font-bold text-lg tracking-tight">Law RAG</span>
        </div>

        <div className="flex items-center gap-3">
          {currentUser && (
            <span className="hidden sm:block text-xs text-blue-300">
              {currentUser.full_name} · <span className="capitalize">{currentUser.role}</span>
            </span>
          )}
          <button
            onClick={handleLogout}
            className="text-xs text-blue-200 hover:text-white border border-blue-600 hover:border-white hover:bg-blue-800 px-3 py-1.5 rounded-lg transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          matters={matters}
          selectedMatter={selectedMatter}
          onSelect={handleSelectMatter}
          onNewMatter={() => setShowNewMatter(true)}
          currentUser={currentUser}
          loading={loadingMatters}
        />

        <main className="flex-1 flex flex-col overflow-hidden">
          {!selectedMatter ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-sm px-8">
                <div className="w-16 h-16 rounded-2xl bg-white border border-blue-200 shadow-sm flex items-center justify-center mx-auto mb-5">
                  <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-slate-700 mb-2">Select a matter</h2>
                <p className="text-sm text-slate-400">
                  Choose a matter from the sidebar to start querying documents.
                  {currentUser?.role === 'partner' && (
                    <> Partners can create new matters with the <strong>+</strong> button.</>
                  )}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col overflow-hidden bg-white rounded-tl-2xl shadow-inner">
              {/* Tab bar */}
              <div className="shrink-0 flex items-center gap-1 px-5 pt-4 pb-0 border-b border-blue-100">
                <div className="flex-1 min-w-0 mr-4">
                  <h2 className="text-base font-semibold text-slate-600 truncate">
                    {selectedMatter.name}
                  </h2>
                  <p className="text-xs text-slate-400 truncate">
                    {selectedMatter.client_name}
                    {selectedMatter.jurisdiction && ` · ${selectedMatter.jurisdiction}`}
                  </p>
                </div>

                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-blue-600 text-blue-700 bg-blue-50'
                        : 'border-transparent bg-white text-slate-500 hover:text-blue-600 hover:bg-blue-50 hover:border-blue-200'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      {tab.icon}
                      {tab.label}
                    </span>
                  </button>
                ))}
              </div>

              {/* Panel content — all three stay mounted so ChatPanel
                  preserves unsent input when the user switches tabs. */}
              <div className="flex-1 overflow-hidden">
                <div className={`h-full ${activeTab === 'chat'      ? '' : 'hidden'}`}><ChatPanel      matter={selectedMatter} onSourceClick={handleSourceClick} /></div>
                <div className={`h-full ${activeTab === 'documents' ? '' : 'hidden'}`}><DocumentsPanel matter={selectedMatter} highlightDocId={highlightDocId} /></div>
                <div className={`h-full ${activeTab === 'history'   ? '' : 'hidden'}`}><HistoryPanel   matter={selectedMatter} /></div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* New Matter modal */}
      {showNewMatter && (
        <NewMatterModal
          onCreated={handleMatterCreated}
          onClose={() => setShowNewMatter(false)}
        />
      )}
    </div>
  )
}
