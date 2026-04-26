import { useNavigate } from 'react-router-dom'
import type { Matter, User } from '../types'

interface SidebarProps {
  matters: Matter[]
  selectedMatter: Matter | null
  onSelect: (matter: Matter) => void
  onNewMatter: () => void
  currentUser: User | null
  loading: boolean
}

export default function Sidebar({
  matters,
  selectedMatter,
  onSelect,
  onNewMatter,
  currentUser,
  loading,
}: SidebarProps) {
  const navigate = useNavigate()
  const isPartner = currentUser?.role === 'partner'

  return (
    <aside className="w-64 shrink-0 bg-white border-r border-blue-100 flex flex-col h-full">
      {/* Header */}
      <div className="px-5 py-4 border-b border-blue-100 flex items-center justify-between">
        <h2 className="text-xs font-semibold text-blue-400 uppercase tracking-widest">
          Matters
        </h2>
        {isPartner && (
          <button
            onClick={onNewMatter}
            title="New matter"
            className="w-6 h-6 flex items-center justify-center rounded-md text-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
      </div>

      {/* Matter list */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {loading ? (
          <div className="space-y-2 px-2 pt-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-blue-50 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : matters.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <p className="text-sm text-slate-400">
              {isPartner ? 'No matters yet — create one with +' : 'No matters assigned'}
            </p>
          </div>
        ) : (
          matters.map((matter) => {
            const isActive = selectedMatter?.id === matter.id
            return (
              <button
                key={matter.id}
                onClick={() => onSelect(matter)}
                className={`w-full text-left px-3 py-3 rounded-lg transition-all duration-150 ${
                  isActive ? 'bg-blue-600 shadow-sm' : 'hover:bg-blue-50'
                }`}
              >
                <div className={`text-sm font-semibold truncate ${isActive ? 'text-white' : 'text-slate-600'}`}>
                  {matter.name}
                </div>
                <div className={`text-xs mt-0.5 truncate ${isActive ? 'text-blue-200' : 'text-slate-400'}`}>
                  {matter.client_name}
                </div>
              </button>
            )
          })
        )}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-blue-100 space-y-1">
        {isPartner && (
          <button
            onClick={() => navigate('/admin')}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Team & Settings
          </button>
        )}
        <div className="px-3 py-2 rounded-lg bg-blue-50">
          <p className="text-xs text-blue-400 text-center">
            {matters.length} matter{matters.length !== 1 ? 's' : ''} accessible
          </p>
        </div>
      </div>
    </aside>
  )
}
