import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Eye, EyeOff, Loader2, Lock, User } from 'lucide-react'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate  = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPwd,  setShowPwd]  = useState(false)
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password) return
    setError('')
    setLoading(true)
    try {
      const user = await login(username.trim(), password)
      navigate(user.is_admin ? '/admin' : '/', { replace: true })
    } catch (err) {
      setError(err.message || 'Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      {/* Background accent */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-5"
          style={{ background: 'radial-gradient(circle, #dc2626 0%, transparent 70%)' }} />
      </div>

      <div className="relative w-full max-w-md">
        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-xl">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center shadow-md shadow-red-200 mb-4"
              style={{ background: 'linear-gradient(135deg, #dc2626 0%, #ea580c 100%)' }}
            >
              <span className="text-white font-bold text-xl tracking-tight" style={{ fontFamily: 'Georgia, serif' }}>CN</span>
            </div>
            <h1
              className="text-2xl font-black tracking-widest mb-1"
              style={{
                fontFamily: "'Cinzel', Georgia, serif",
                background: 'linear-gradient(90deg, #dc2626 0%, #ea580c 50%, #dc2626 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '0.12em',
              }}
            >
              CYBER NIRVANA
            </h1>
            <p className="text-xs text-gray-400 font-medium tracking-widest uppercase">Contract Job Board</p>
          </div>

          <h2 className="text-lg font-semibold text-gray-800 text-center mb-6">Sign in to your account</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="sidebar-label">Username</label>
              <div className="relative">
                <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                <input
                  type="text"
                  autoComplete="username"
                  className="input w-full pl-9"
                  placeholder="Enter username"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <label className="sidebar-label">Password</label>
              <div className="relative">
                <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                <input
                  type={showPwd ? 'text' : 'password'}
                  autoComplete="current-password"
                  className="input w-full pl-9 pr-10"
                  placeholder="Enter password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600 text-center">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !username.trim() || !password}
              className="btn-primary w-full justify-center mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <><Loader2 size={15} className="animate-spin" /> Signing in…</>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <p className="text-center text-xs text-gray-400 mt-6">
            Access is by invitation only. Contact your administrator.
          </p>
        </div>
      </div>
    </div>
  )
}
