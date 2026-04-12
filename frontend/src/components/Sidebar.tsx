import type { Matter } from '../types'

interface SidebarProps {
  matters: Matter[]
  selectedMatter: Matter | null
  onSelect: (matter: Matter) => void
  loading: boolean
}

export default function Sidebar({ matters, selectedMatter, onSelect, loading }: SidebarProps) {
  return (
    <aside className="w-64 shrink-0 bg-white border-r border-blue-100 flex flex-col h-full">
      <div className="px-5 py-4 border-b border-blue-100">
        <h2 className="text-xs font-semibold text-blue-400 uppercase tracking-widest">
          Matters
        </h2>
      </div>

      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {loading ? (
          <div className="space-y-2 px-2 pt-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-blue-50 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : matters.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <p className="text-sm text-slate-400">No matters assigned</p>
          </div>
        ) : (
          matters.map((matter) => {
            const isActive = selectedMatter?.id === matter.id
            return (
              <button
                key={matter.id}
                onClick={() => onSelect(matter)}
                className={`w-full text-left px-3 py-3 rounded-lg transition-all duration-150 group ${
                  isActive
                    ? 'bg-blue-600 shadow-sm'
                    : 'hover:bg-blue-50'
                }`}
              >
                <div className={`text-sm font-semibold truncate ${
                  isActive ? 'text-white' : 'text-slate-800'
                }`}>
                  {matter.name}
                </div>
                <div className={`text-xs mt-0.5 truncate ${
                  isActive ? 'text-blue-200' : 'text-slate-400'
                }`}>
                  {matter.client_name}
                </div>
              </button>
            )
          })
        )}
      </nav>

      <div className="p-3 border-t border-blue-100">
        <div className="px-3 py-2 rounded-lg bg-blue-50">
          <p className="text-xs text-blue-400 text-center">
            {matters.length} matter{matters.length !== 1 ? 's' : ''} accessible
          </p>
        </div>
      </div>
    </aside>
  )
}
