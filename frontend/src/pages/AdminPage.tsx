import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { mattersApi } from '../api/matters'
import { usersApi } from '../api/users'
import type { MatterDetail, User, UserRole } from '../types'

type AdminTab = 'team' | 'matters'

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function UserRow({
  user,
  currentUserId,
  onRoleChange,
  onDeactivate,
}: {
  user: User
  currentUserId: string
  onRoleChange: (id: string, role: UserRole) => void
  onDeactivate: (id: string) => void
}) {
  const isSelf = user.id === currentUserId
  return (
    <tr className="border-t border-slate-100 hover:bg-slate-50">
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-slate-800">{user.full_name}</p>
        <p className="text-xs text-slate-400">{user.email}</p>
      </td>
      <td className="px-4 py-3">
        <select
          value={user.role}
          disabled={isSelf}
          onChange={(e) => onRoleChange(user.id, e.target.value as UserRole)}
          className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <option value="partner">Partner</option>
          <option value="associate">Associate</option>
          <option value="paralegal">Paralegal</option>
        </select>
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
          user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-500'
        }`}>
          {user.is_active ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        {user.is_active && !isSelf && (
          <button
            onClick={() => onDeactivate(user.id)}
            className="text-xs text-red-400 hover:text-red-600 hover:underline"
          >
            Deactivate
          </button>
        )}
        {isSelf && (
          <span className="text-xs text-slate-300">you</span>
        )}
      </td>
    </tr>
  )
}

function AddUserForm({ onCreated }: { onCreated: (user: User) => void }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'associate' as UserRole })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const user = await usersApi.create(form)
      onCreated(user)
      setForm({ email: '', full_name: '', password: '', role: 'associate' })
      setOpen(false)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to create user')
    } finally {
      setSaving(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800 border border-blue-200 hover:border-blue-400 px-4 py-2 rounded-xl transition-colors"
      >
        <span className="text-lg leading-none">+</span> Add User
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-3">
      <p className="text-sm font-semibold text-slate-700">New Team Member</p>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <input
          required
          placeholder="Full name"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          className="col-span-2 sm:col-span-1 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
        />
        <input
          required
          type="email"
          placeholder="Email address"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          className="col-span-2 sm:col-span-1 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
        />
        <input
          required
          type="password"
          placeholder="Temporary password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          className="col-span-2 sm:col-span-1 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
        />
        <select
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
          className="col-span-2 sm:col-span-1 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
        >
          <option value="partner">Partner</option>
          <option value="associate">Associate</option>
          <option value="paralegal">Paralegal</option>
        </select>
      </div>
      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={saving}
          className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Creating…' : 'Create User'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-sm bg-white text-slate-500 hover:text-slate-700 px-4 py-2 rounded-lg border border-slate-200 hover:border-slate-300 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

function MatterCard({
  matter,
  allUsers,
  onUpdated,
  onDeleted,
}: {
  matter: MatterDetail
  allUsers: User[]
  onUpdated: (updated: MatterDetail) => void
  onDeleted: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [addingUserId, setAddingUserId] = useState('')
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  const nonMembers = allUsers.filter(
    (u) => u.is_active && !matter.members.some((m) => m.id === u.id)
  )

  const handleAdd = async () => {
    if (!addingUserId) return
    setSaving(true)
    setError('')
    try {
      await mattersApi.addMember(matter.id, addingUserId)
      const updated = await mattersApi.get(matter.id)
      onUpdated(updated)
      setAddingUserId('')
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to add member')
    } finally {
      setSaving(false)
    }
  }

  const handleRemove = async (userId: string) => {
    setSaving(true)
    setError('')
    try {
      await mattersApi.removeMember(matter.id, userId)
      const updated = await mattersApi.get(matter.id)
      onUpdated(updated)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to remove member')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Permanently delete "${matter.name}"? All documents, query history, and memberships will be removed. This cannot be undone.`)) return
    setDeleting(true)
    setError('')
    try {
      await mattersApi.deleteMatter(matter.id)
      onDeleted(matter.id)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to delete matter')
      setDeleting(false)
    }
  }

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-slate-50 transition-colors text-left"
      >
        <div>
          <p className="text-sm font-semibold text-slate-600">{matter.name}</p>
          <p className="text-xs text-slate-400 mt-0.5">{matter.client_name}{matter.jurisdiction ? ` · ${matter.jurisdiction}` : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs bg-blue-100 text-blue-600 font-medium px-2.5 py-0.5 rounded-full">
            {matter.members.length} member{matter.members.length !== 1 ? 's' : ''}
          </span>
          <svg
            className={`w-4 h-4 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded member management */}
      {expanded && (
        <div className="border-t border-slate-100 bg-slate-50 px-4 py-3 space-y-3">
          {error && <p className="text-xs text-red-500">{error}</p>}

          {/* Current members */}
          <div className="space-y-1.5">
            {matter.members.map((m) => (
              <div key={m.id} className="flex items-center justify-between bg-white border border-slate-100 rounded-lg px-3 py-2">
                <div>
                  <p className="text-xs font-medium text-slate-700">{m.full_name}</p>
                  <p className="text-xs text-slate-400">{m.email}</p>
                </div>
                <button
                  onClick={() => handleRemove(m.id)}
                  disabled={saving || matter.members.length <= 1}
                  className="text-xs text-red-400 hover:text-red-600 disabled:opacity-30 disabled:cursor-not-allowed"
                  title={matter.members.length <= 1 ? 'Cannot remove last member' : 'Remove from matter'}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>

          {/* Add member */}
          {nonMembers.length > 0 && (
            <div className="flex gap-2">
              <select
                value={addingUserId}
                onChange={(e) => setAddingUserId(e.target.value)}
                className="flex-1 text-xs border border-slate-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="">Add a team member…</option>
                {nonMembers.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.role})
                  </option>
                ))}
              </select>
              <button
                onClick={handleAdd}
                disabled={!addingUserId || saving}
                className="text-xs bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-40 transition-colors"
              >
                Add
              </button>
            </div>
          )}
          {nonMembers.length === 0 && (
            <p className="text-xs text-slate-400">All active team members are already on this matter.</p>
          )}

          {/* Matter ID — shown for folder-watch / API use */}
          <div className="border-t border-slate-100 pt-2 mt-1">
            <p className="text-xs text-slate-400 mb-1 font-medium">Matter ID</p>
            <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1.5">
              <code className="text-xs text-slate-600 font-mono flex-1 truncate select-all">{matter.id}</code>
              <button
                onClick={() => { navigator.clipboard.writeText(matter.id) }}
                title="Copy matter ID"
                className="shrink-0 text-slate-400 hover:text-blue-600 transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </button>
            </div>
          </div>

          {/* Danger zone */}
          <div className="border-t border-red-100 pt-3 mt-1">
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="text-xs text-red-500 hover:text-red-700 hover:bg-red-50 border border-red-200 hover:border-red-400 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              {deleting ? 'Deleting…' : 'Delete matter'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function AddMatterForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', client_name: '', jurisdiction: '', description: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await mattersApi.create(form)
      setForm({ name: '', client_name: '', jurisdiction: '', description: '' })
      setOpen(false)
      onCreated()
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to create matter')
    } finally {
      setSaving(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800 border border-blue-200 hover:border-blue-400 px-4 py-2 rounded-xl transition-colors"
      >
        <span className="text-lg leading-none">+</span> New Matter
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-3">
      <p className="text-sm font-semibold text-slate-700">New Matter</p>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <input
          required
          placeholder="Matter name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="col-span-2 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
        />
        <input
          required
          placeholder="Client name"
          value={form.client_name}
          onChange={(e) => setForm({ ...form, client_name: e.target.value })}
          className="col-span-2 sm:col-span-1 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
        />
        <input
          placeholder="Jurisdiction (optional)"
          value={form.jurisdiction}
          onChange={(e) => setForm({ ...form, jurisdiction: e.target.value })}
          className="col-span-2 sm:col-span-1 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
        />
        <textarea
          placeholder="Description (optional)"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          rows={2}
          className="col-span-2 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white resize-none"
        />
      </div>
      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={saving}
          className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Creating…' : 'Create Matter'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-sm bg-white text-slate-500 hover:text-slate-700 px-4 py-2 rounded-lg border border-slate-200 hover:border-slate-300 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Main AdminPage
// ---------------------------------------------------------------------------

export default function AdminPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<AdminTab>('team')
  const [users, setUsers] = useState<User[]>([])
  const [matters, setMatters] = useState<MatterDetail[]>([])
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const init = async () => {
      try {
        const me = await usersApi.me()
        if (me.role !== 'partner') {
          navigate('/')
          return
        }
        setCurrentUser(me)
        const [allUsers, allMatters] = await Promise.all([
          usersApi.list(),
          mattersApi.list(),
        ])
        setUsers(allUsers)
        // Load detailed matter info (with members) in parallel
        const details = await Promise.all(allMatters.map((m) => mattersApi.get(m.id)))
        setMatters(details)
      } catch {
        setError('Failed to load data. You may not have permission to access this page.')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [navigate])

  const handleRoleChange = async (userId: string, role: UserRole) => {
    try {
      const updated = await usersApi.updateRole(userId, role)
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)))
    } catch (err: any) {
      alert(err?.response?.data?.detail ?? 'Failed to update role')
    }
  }

  const handleDeactivate = async (userId: string) => {
    if (!confirm('Deactivate this user? They will lose access immediately.')) return
    try {
      const updated = await usersApi.deactivate(userId)
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)))
    } catch (err: any) {
      alert(err?.response?.data?.detail ?? 'Failed to deactivate user')
    }
  }

  const handleMatterUpdated = (updated: MatterDetail) => {
    setMatters((prev) => prev.map((m) => (m.id === updated.id ? updated : m)))
  }

  const handleMatterDeleted = (id: string) => {
    setMatters((prev) => prev.filter((m) => m.id !== id))
  }

  const reloadMatters = async () => {
    const all = await mattersApi.list()
    const details = await Promise.all(all.map((m) => mattersApi.get(m.id)))
    setMatters(details)
  }

  return (
    <div className="flex flex-col h-screen bg-blue-50 overflow-hidden">
      {/* Header */}
      <header className="shrink-0 bg-blue-900 text-white px-5 h-14 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-blue-300 hover:text-white transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="text-sm">Back to Dashboard</span>
          </button>
        </div>
        <span className="text-sm font-semibold text-blue-200">Team & Settings</span>
        <div className="w-32" /> {/* spacer */}
      </header>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <div key={i} className="h-16 bg-white rounded-xl animate-pulse" />)}
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 rounded-xl">{error}</div>
          ) : (
            <>
              {/* Tabs */}
              <div className="flex gap-1 border-b border-blue-100">
                {(['team', 'matters'] as AdminTab[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-5 py-2 text-sm font-medium border-b-2 transition-colors capitalize ${
                      tab === t
                        ? 'border-blue-600 text-blue-700 bg-blue-50'
                        : 'border-transparent bg-white text-slate-500 hover:text-blue-600 hover:bg-blue-50 hover:border-blue-200'
                    }`}
                  >
                    {t === 'team' ? `Team (${users.length})` : `Matters (${matters.length})`}
                  </button>
                ))}
              </div>

              {/* ── Team tab ── */}
              {tab === 'team' && (
                <div className="space-y-4">
                  <AddUserForm onCreated={(u) => setUsers((prev) => [...prev, u])} />

                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          <th className="px-4 py-3 text-left">Name / Email</th>
                          <th className="px-4 py-3 text-left">Role</th>
                          <th className="px-4 py-3 text-left">Status</th>
                          <th className="px-4 py-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.map((u) => (
                          <UserRow
                            key={u.id}
                            user={u}
                            currentUserId={currentUser?.id ?? ''}
                            onRoleChange={handleRoleChange}
                            onDeactivate={handleDeactivate}
                          />
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* ── Matters tab ── */}
              {tab === 'matters' && (
                <div className="space-y-4">
                  <AddMatterForm onCreated={reloadMatters} />

                  <div className="space-y-2">
                    {matters.length === 0 ? (
                      <p className="text-sm text-slate-400 text-center py-8">No matters yet — create one above.</p>
                    ) : (
                      matters.map((m) => (
                        <MatterCard
                          key={m.id}
                          matter={m}
                          allUsers={users}
                          onUpdated={handleMatterUpdated}
                          onDeleted={handleMatterDeleted}
                        />
                      ))
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
