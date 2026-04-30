import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  Users, Activity, LayoutGrid, LogOut, Plus, Edit2, Trash2,
  X, Check, Loader2, Eye, EyeOff, ArrowLeft, RefreshCw,
  User, Shield, Circle
} from 'lucide-react'

const CATEGORY_COLORS = {
  'Agentic AI Engineer':            'bg-purple-500/20 text-purple-300',
  'AI / ML Engineer':               'bg-blue-500/20 text-blue-300',
  'Generative AI / GenAI Engineer': 'bg-pink-500/20 text-pink-300',
  'LLM Engineer':                   'bg-cyan-500/20 text-cyan-300',
  'Data Scientist':                 'bg-emerald-500/20 text-emerald-300',
  'MLOps / LLMOps Engineer':        'bg-amber-500/20 text-amber-300',
  'NLP Engineer':                   'bg-lime-500/20 text-lime-300',
  'RAG / LangChain / Vector DB Developer': 'bg-fuchsia-500/20 text-fuchsia-300',
}
const catColor = (cat) => CATEGORY_COLORS[cat] ?? 'bg-slate-600/30 text-slate-300'

function fmtDateTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    })
  } catch { return iso }
}

// ── UserModal ─────────────────────────────────────────────────────────────────

function UserModal({ user, onSave, onClose }) {
  const { authFetch } = useAuth()
  const isEdit = Boolean(user)

  const [username, setUsername] = useState(user?.username ?? '')
  const [password, setPassword] = useState('')
  const [showPwd,  setShowPwd]  = useState(false)
  const [isActive, setIsActive] = useState(user?.is_active ?? true)
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleSave = async (e) => {
    e.preventDefault()
    if (!username.trim()) return setError('Username is required')
    if (!isEdit && !password) return setError('Password is required')
    if (password && password.length < 6) return setError('Password must be at least 6 characters')
    setError('')
    setLoading(true)
    try {
      const body = {}
      if (username.trim() !== (user?.username ?? '')) body.username = username.trim()
      if (password) body.password = password
      if (isEdit) body.is_active = isActive
      if (!isEdit) { body.username = username.trim(); body.password = password }

      const url = isEdit ? `/api/admin/users/${user.id}` : '/api/admin/users'
      const res = await authFetch(url, {
        method:  isEdit ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to save')
      }
      onSave()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700/60 rounded-2xl w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between p-5 border-b border-slate-700/50">
          <h3 className="font-semibold text-slate-100">
            {isEdit ? 'Edit User' : 'Create New User'}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSave} className="p-5 space-y-4">
          <div>
            <label className="sidebar-label">Username</label>
            <input
              type="text"
              className="input w-full"
              placeholder="Enter username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              disabled={loading}
            />
          </div>

          <div>
            <label className="sidebar-label">{isEdit ? 'New Password (leave blank to keep)' : 'Password'}</label>
            <div className="relative">
              <input
                type={showPwd ? 'text' : 'password'}
                className="input w-full pr-10"
                placeholder={isEdit ? 'Enter new password' : 'Min 6 characters'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPwd(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
              >
                {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          {isEdit && (
            <label className="flex items-center gap-3 cursor-pointer select-none">
              <div
                onClick={() => setIsActive(v => !v)}
                className={`w-10 h-5 rounded-full transition-colors flex items-center px-0.5 ${isActive ? 'bg-green-500' : 'bg-slate-600'}`}
              >
                <div className={`w-4 h-4 bg-white rounded-full transition-transform ${isActive ? 'translate-x-5' : 'translate-x-0'}`} />
              </div>
              <span className="text-sm text-slate-300">{isActive ? 'Active' : 'Inactive'}</span>
            </label>
          )}

          {error && (
            <div className="p-3 bg-red-900/30 border border-red-500/40 rounded-lg text-sm text-red-300">
              {error}
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn-ghost flex-1 justify-center text-sm">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center text-sm disabled:opacity-50">
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              {isEdit ? 'Save Changes' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── DeleteConfirm ─────────────────────────────────────────────────────────────

function DeleteConfirm({ user, onConfirm, onClose }) {
  const [loading, setLoading] = useState(false)
  const handleDelete = async () => {
    setLoading(true)
    await onConfirm()
    setLoading(false)
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700/60 rounded-2xl w-full max-w-sm shadow-2xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
            <Trash2 size={18} className="text-red-400" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100">Delete User</h3>
            <p className="text-xs text-slate-400">This action cannot be undone</p>
          </div>
        </div>
        <p className="text-sm text-slate-300 mb-6">
          Are you sure you want to delete <span className="text-white font-semibold">{user.username}</span>?
          All their sessions and job applications will be removed.
        </p>
        <div className="flex gap-2">
          <button onClick={onClose} className="btn-ghost flex-1 justify-center text-sm">Cancel</button>
          <button onClick={handleDelete} disabled={loading}
            className="btn flex-1 justify-center text-sm bg-red-600 text-white hover:bg-red-500 active:scale-95 disabled:opacity-50">
            {loading ? <Loader2 size={14} className="animate-spin" /> : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── StatCard ──────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="card p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={22} />
      </div>
      <div>
        <div className="text-2xl font-bold text-slate-100">{value ?? '—'}</div>
        <div className="text-xs text-slate-400 mt-0.5">{label}</div>
      </div>
    </div>
  )
}

// ── UserRow ───────────────────────────────────────────────────────────────────

function UserRow({ user, onEdit, onDelete }) {
  const initials = user.username.slice(0, 2).toUpperCase()
  return (
    <div className="card p-4 flex items-start gap-4">
      {/* Avatar */}
      <div className="relative shrink-0">
        <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
          <span className="text-indigo-300 font-bold text-sm">{initials}</span>
        </div>
        <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-slate-800 ${user.is_online ? 'bg-green-400' : 'bg-slate-600'}`} />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-slate-100 text-sm">{user.username}</span>
          {!user.is_active && (
            <span className="badge bg-red-500/15 text-red-400 border border-red-500/30 text-[10px]">Inactive</span>
          )}
          {user.is_online && (
            <span className="badge bg-green-500/15 text-green-400 border border-green-500/30 text-[10px] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              Online
            </span>
          )}
        </div>

        <div className="text-xs text-slate-500 mt-0.5">
          Last login: {fmtDateTime(user.last_login)}
          {user.last_seen && user.is_online && (
            <span className="ml-2 text-green-400/70">· active {fmtDateTime(user.last_seen)}</span>
          )}
        </div>

        {/* Today's activity */}
        <div className="mt-2 flex items-center gap-2 flex-wrap">
          <span className={`badge text-[10px] font-medium ${user.apps_today_count > 0 ? 'bg-blue-500/15 text-blue-300 border border-blue-500/30' : 'bg-slate-700/50 text-slate-500'}`}>
            {user.apps_today_count} applied today
          </span>
          {user.categories_today.map(cat => (
            <span key={cat} className={`badge text-[10px] ${catColor(cat)}`}>
              {cat}
            </span>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        <button
          onClick={() => onEdit(user)}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-blue-300 hover:bg-blue-500/10 transition-all"
          title="Edit user"
        >
          <Edit2 size={14} />
        </button>
        <button
          onClick={() => onDelete(user)}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
          title="Delete user"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}

// ── AdminPage ─────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const { user, logout, authFetch } = useAuth()
  const navigate = useNavigate()

  const [users,     setUsers]     = useState([])
  const [dashboard, setDashboard] = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [modal,     setModal]     = useState(null) // null | 'create' | { edit: user } | { delete: user }

  const fetchData = useCallback(async () => {
    try {
      const [dashRes, usersRes] = await Promise.all([
        authFetch('/api/admin/dashboard'),
        authFetch('/api/admin/users'),
      ])
      if (dashRes.ok)  setDashboard(await dashRes.json())
      if (usersRes.ok) setUsers(await usersRes.json())
    } finally {
      setLoading(false)
    }
  }, [authFetch])

  useEffect(() => {
    fetchData()
    const id = setInterval(fetchData, 10_000)
    return () => clearInterval(id)
  }, [fetchData])

  const handleDeleteConfirm = async (userId) => {
    await authFetch(`/api/admin/users/${userId}`, { method: 'DELETE' })
    setModal(null)
    fetchData()
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Header */}
      <header className="header-glow sticky top-0 z-40">
        <div className="max-w-screen-xl mx-auto px-4 py-3 flex items-center gap-4">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-900/50"
              style={{ background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)' }}>
              <span className="text-white font-bold text-xs" style={{ fontFamily: 'Georgia, serif' }}>CN</span>
            </div>
            <div className="leading-none">
              <div className="text-base font-black tracking-widest bg-clip-text text-transparent"
                style={{
                  fontFamily: "'Cinzel', Georgia, serif",
                  background: 'linear-gradient(90deg, #a5b4fc 0%, #c4b5fd 50%, #818cf8 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  letterSpacing: '0.12em',
                }}>
                CYBER NIRVANA
              </div>
            </div>
          </div>

          <span className="badge bg-rose-500/15 text-rose-400 border border-rose-500/30 text-xs">
            <Shield size={11} /> Admin Panel
          </span>

          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => navigate('/')}
              className="btn-ghost text-xs px-3 py-1.5"
            >
              <ArrowLeft size={13} /> Job Board
            </button>
            <button
              onClick={fetchData}
              className="btn-ghost text-xs px-3 py-1.5"
              title="Refresh"
            >
              <RefreshCw size={13} />
            </button>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/50 rounded-lg border border-slate-700/50 text-xs text-slate-300">
              <User size={12} className="text-indigo-400" />
              {user?.username}
            </div>
            <button
              onClick={handleLogout}
              className="btn-ghost text-xs px-3 py-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10"
            >
              <LogOut size={13} /> Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-screen-xl mx-auto w-full px-4 py-6 flex-1">
        {loading && !dashboard ? (
          <div className="flex items-center justify-center py-20 gap-3 text-slate-500">
            <Loader2 size={20} className="animate-spin" />
            <span className="text-sm">Loading dashboard…</span>
          </div>
        ) : (
          <>
            {/* Stats row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <StatCard icon={Users}     label="Total Users"       value={dashboard?.total_users}  color="bg-indigo-500/15 text-indigo-400" />
              <StatCard icon={Activity}  label="Online Now"        value={dashboard?.online_now}   color="bg-green-500/15 text-green-400" />
              <StatCard icon={LayoutGrid} label="Applications Today" value={dashboard?.apps_today} color="bg-blue-500/15 text-blue-400" />
              <StatCard icon={Users}     label="Active Users"      value={dashboard?.active_users} color="bg-purple-500/15 text-purple-400" />
            </div>

            {/* Users section */}
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-slate-100">
                Users
                <span className="ml-2 text-sm font-normal text-slate-500">({users.length})</span>
              </h2>
              <button
                onClick={() => setModal('create')}
                className="btn-primary text-xs px-3 py-1.5"
              >
                <Plus size={13} /> Add User
              </button>
            </div>

            {users.length === 0 ? (
              <div className="card p-12 flex flex-col items-center gap-3 text-slate-500">
                <Users size={36} className="text-slate-700" />
                <p className="text-sm">No users yet. Create the first one.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {users.map(u => (
                  <UserRow
                    key={u.id}
                    user={u}
                    onEdit={u => setModal({ edit: u })}
                    onDelete={u => setModal({ delete: u })}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </main>

      {/* Modals */}
      {modal === 'create' && (
        <UserModal
          user={null}
          onSave={() => { setModal(null); fetchData() }}
          onClose={() => setModal(null)}
        />
      )}
      {modal?.edit && (
        <UserModal
          user={modal.edit}
          onSave={() => { setModal(null); fetchData() }}
          onClose={() => setModal(null)}
        />
      )}
      {modal?.delete && (
        <DeleteConfirm
          user={modal.delete}
          onConfirm={() => handleDeleteConfirm(modal.delete.id)}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  )
}
