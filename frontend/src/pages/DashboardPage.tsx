import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { mattersApi } from '../api/matters'
import ChatPanel from '../components/ChatPanel'
import DocumentsPanel from '../components/DocumentsPanel'
import Sidebar from '../components/Sidebar'
import type { Matter } from '../types'

type Tab = 'chat' | 'documents'

export default function DashboardPage() {
  const [matters, setMatters] = useState<Matter[]>([])
  const [selectedMatter, setSelectedMatter] = useState<Matter | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [loadingMatters, setLoadingMatters] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    mattersApi
      .list()
      .then(setMatters)
      .catch((err) => {
        if (err?.response?.status === 401) navigate('/login')
      })
      .finally(() => setLoadingMatters(false))
  }, [navigate])

  const handleSelectMatter = (matter: Matter) => {
    setSelectedMatter(matter)
    setActiveTab('chat')   // always open on chat when switching matter
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/login')
  }

  return (
    <div className="flex flex-col h-screen bg-blue-50 overflow-hidden">

      {/* ── Header ── */}
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
          {selectedMatter && (
            <span className="hidden sm:block text-sm text-blue-300 truncate max-w-xs">
              {selectedMatter.name}
            </span>
          )}
          <button
            onClick={handleLogout}
            className="text-xs text-blue-300 hover:text-white border border-blue-700 hover:border-blue-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Sidebar */}
        <Sidebar
          matters={matters}
          selectedMatter={selectedMatter}
          onSelect={handleSelectMatter}
          loading={loadingMatters}
        />

        {/* Main area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {!selectedMatter ? (
            /* Empty state */
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
                  Choose a matter from the sidebar to start querying documents or manage files.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col overflow-hidden bg-white rounded-tl-2xl shadow-inner">

              {/* Tab bar */}
              <div className="shrink-0 flex items-center gap-1 px-5 pt-4 pb-0 border-b border-blue-100">
                <div className="flex-1 min-w-0 mr-4">
                  <h2 className="text-base font-semibold text-slate-800 truncate">
                    {selectedMatter.name}
                  </h2>
                  <p className="text-xs text-slate-400 truncate">
                    {selectedMatter.client_name}
                    {selectedMatter.jurisdiction && ` · ${selectedMatter.jurisdiction}`}
                  </p>
                </div>

                {(['chat', 'documents'] as Tab[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors capitalize ${
                      activeTab === tab
                        ? 'border-blue-600 text-blue-700 bg-blue-50'
                        : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {tab === 'chat' ? (
                      <span className="flex items-center gap-1.5">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                          />
                        </svg>
                        Chat
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                          />
                        </svg>
                        Documents
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Panel content */}
              <div className="flex-1 overflow-hidden">
                {activeTab === 'chat'
                  ? <ChatPanel matter={selectedMatter} />
                  : <DocumentsPanel matter={selectedMatter} />
                }
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
