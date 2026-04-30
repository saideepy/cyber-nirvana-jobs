import { useState, useEffect, useCallback, useRef } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Loader2, SearchX, LayoutGrid, Zap, Globe2 } from 'lucide-react'
import { useAuth } from './context/AuthContext'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import FilterPanel from './components/FilterPanel'
import JobCard from './components/JobCard'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'

const DEFAULT_FILTERS = {
  sort:        'newest',
  days:        '',
  category:    '',
  source:      '',
  c2c_only:    false,
  vendor_only: false,
}

// ── Protected route wrappers ──────────────────────────────────────────────────

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <FullScreenLoader />
  if (!user)   return <Navigate to="/login" replace />
  return children
}

function RequireAdmin({ children }) {
  const { user, loading } = useAuth()
  if (loading)       return <FullScreenLoader />
  if (!user)         return <Navigate to="/login" replace />
  if (!user.is_admin) return <Navigate to="/" replace />
  return children
}

function RedirectIfAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <FullScreenLoader />
  if (user)    return <Navigate to={user.is_admin ? '/admin' : '/'} replace />
  return children
}

function FullScreenLoader() {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-indigo-400" />
    </div>
  )
}

// ── Platform source bar ───────────────────────────────────────────────────────

const PLATFORM_CONFIG = {
  'LinkedIn':         { label: 'LinkedIn',       ring: 'ring-blue-500',    bg: 'bg-blue-500/15',    text: 'text-blue-300',    border: 'border-blue-500/40',    dot: 'bg-blue-400'    },
  'Indeed':           { label: 'Indeed',          ring: 'ring-sky-500',     bg: 'bg-sky-500/15',     text: 'text-sky-300',     border: 'border-sky-500/40',     dot: 'bg-sky-400'     },
  'ZipRecruiter':     { label: 'ZipRecruiter',    ring: 'ring-amber-500',   bg: 'bg-amber-500/15',   text: 'text-amber-300',   border: 'border-amber-500/40',   dot: 'bg-amber-400'   },
  'Glassdoor':        { label: 'Glassdoor',       ring: 'ring-emerald-500', bg: 'bg-emerald-500/15', text: 'text-emerald-300', border: 'border-emerald-500/40', dot: 'bg-emerald-400' },
  'Monster':          { label: 'Monster',         ring: 'ring-purple-500',  bg: 'bg-purple-500/15',  text: 'text-purple-300',  border: 'border-purple-500/40',  dot: 'bg-purple-400'  },
  'Dice.com':         { label: 'Dice.com',        ring: 'ring-red-500',     bg: 'bg-red-500/15',     text: 'text-red-300',     border: 'border-red-500/40',     dot: 'bg-red-400'     },
  'Adzuna':           { label: 'Adzuna',          ring: 'ring-orange-500',  bg: 'bg-orange-500/15',  text: 'text-orange-300',  border: 'border-orange-500/40',  dot: 'bg-orange-400'  },
  'WeWorkRemotely':   { label: 'WeWorkRemotely',  ring: 'ring-indigo-500',  bg: 'bg-indigo-500/15',  text: 'text-indigo-300',  border: 'border-indigo-500/40',  dot: 'bg-indigo-400'  },
  'Remotive.com':     { label: 'Remotive',        ring: 'ring-teal-500',    bg: 'bg-teal-500/15',    text: 'text-teal-300',    border: 'border-teal-500/40',    dot: 'bg-teal-400'    },
  'Himalayas.app':    { label: 'Himalayas',       ring: 'ring-violet-500',  bg: 'bg-violet-500/15',  text: 'text-violet-300',  border: 'border-violet-500/40',  dot: 'bg-violet-400'  },
  'Arbeitnow':        { label: 'Arbeitnow',       ring: 'ring-cyan-500',    bg: 'bg-cyan-500/15',    text: 'text-cyan-300',    border: 'border-cyan-500/40',    dot: 'bg-cyan-400'    },
  'The Muse':         { label: 'The Muse',        ring: 'ring-pink-500',    bg: 'bg-pink-500/15',    text: 'text-pink-300',    border: 'border-pink-500/40',    dot: 'bg-pink-400'    },
  'Jobicy.com':       { label: 'Jobicy',          ring: 'ring-blue-400',    bg: 'bg-blue-400/15',    text: 'text-blue-200',    border: 'border-blue-400/40',    dot: 'bg-blue-300'    },
  'WorkingNomads':    { label: 'WorkingNomads',   ring: 'ring-cyan-400',    bg: 'bg-cyan-400/15',    text: 'text-cyan-200',    border: 'border-cyan-400/40',    dot: 'bg-cyan-300'    },
  "HN Who's Hiring":  { label: "HN Hiring",       ring: 'ring-rose-500',    bg: 'bg-rose-500/15',    text: 'text-rose-300',    border: 'border-rose-500/40',    dot: 'bg-rose-400'    },
}

const FEATURED_PLATFORMS = [
  'LinkedIn', 'Indeed', 'ZipRecruiter', 'Glassdoor', 'Monster', 'Dice.com',
]

function SourceBar({ stats, activeSource, onSelect }) {
  const counts   = stats?.by_source ?? {}
  const allSrcs  = stats?.all_sources ?? []

  // Featured platforms always shown (grayed if no jobs yet); then active non-featured sources
  const featured = FEATURED_PLATFORMS.map(name => ({ name, count: counts[name] ?? 0, pinned: true }))
  const rest     = allSrcs
    .filter(s => !FEATURED_PLATFORMS.includes(s) && (counts[s] ?? 0) > 0)
    .map(name => ({ name, count: counts[name] ?? 0, pinned: false }))

  const platforms = [...featured, ...rest]

  return (
    <div className="mb-5">
      <div className="flex items-center gap-2 mb-2.5 px-0.5">
        <Globe2 size={13} className="text-slate-400 shrink-0" />
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest">Job Platforms</span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
        {platforms.map(({ name, count }) => {
          const cfg      = PLATFORM_CONFIG[name] ?? { label: name, ring: 'ring-slate-500', bg: 'bg-slate-500/15', text: 'text-slate-300', border: 'border-slate-500/40', dot: 'bg-slate-400' }
          const isActive = activeSource === name
          const isEmpty  = count === 0
          return (
            <button
              key={name}
              onClick={() => !isEmpty && onSelect(isActive ? '' : name)}
              title={isEmpty ? 'No jobs scraped yet from this source' : `${count.toLocaleString()} jobs from ${cfg.label}`}
              className={`shrink-0 flex flex-col items-start gap-1 px-3 py-2 rounded-xl border transition-all duration-150
                ${isActive
                  ? `${cfg.bg} ${cfg.border} ${cfg.text} ring-1 ${cfg.ring} shadow-md scale-[1.03]`
                  : isEmpty
                    ? 'bg-slate-800/30 border-slate-700/30 text-slate-600 cursor-default'
                    : `bg-slate-800/50 border-slate-700/40 ${cfg.text} hover:${cfg.bg} hover:${cfg.border} hover:scale-[1.02]`
                }`}
            >
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isEmpty ? 'bg-slate-600' : cfg.dot}`} />
                <span className="text-[11px] font-semibold whitespace-nowrap">{cfg.label}</span>
              </div>
              <span className={`text-[10px] font-mono pl-3 ${isEmpty ? 'text-slate-600' : 'opacity-70'}`}>
                {isEmpty ? 'no jobs yet' : `${count.toLocaleString()} jobs`}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}


// ── Job board page ────────────────────────────────────────────────────────────

function JobBoardPage() {
  const { authFetch, user, logout } = useAuth()
  const navigate = useNavigate()

  const [search,        setSearch]        = useState('')
  const [filters,       setFilters]       = useState(DEFAULT_FILTERS)
  const [page,          setPage]          = useState(1)
  const [jobs,          setJobs]          = useState([])
  const [total,         setTotal]         = useState(0)
  const [pages,         setPages]         = useState(1)
  const [stats,         setStats]         = useState(null)
  const [loading,       setLoading]       = useState(false)
  const [error,         setError]         = useState(null)
  const [appliedJobIds, setAppliedJobIds] = useState(new Set())

  const perPage   = 30
  const searchRef = useRef(null)

  // Load applied job IDs on mount
  useEffect(() => {
    authFetch('/api/user/applications')
      .then(r => r.json())
      .then(d => setAppliedJobIds(new Set(d.applied_job_ids ?? [])))
      .catch(() => {})
  }, [authFetch])

  // Debounced search
  useEffect(() => {
    clearTimeout(searchRef.current)
    searchRef.current = setTimeout(() => {
      setPage(1)
      fetchJobs(1)
    }, 350)
  }, [search])

  // Refetch on filter/page change
  useEffect(() => { fetchJobs(page) }, [filters, page])

  // Poll stats every 15 s
  useEffect(() => {
    fetchStats()
    const id = setInterval(fetchStats, 15_000)
    return () => clearInterval(id)
  }, [])

  const buildParams = (pg) => {
    const p = new URLSearchParams({ page: pg, per_page: perPage, sort: filters.sort })
    if (search)               p.set('search',      search)
    if (filters.category)     p.set('category',    filters.category)
    if (filters.source)       p.set('source',      filters.source)
    if (filters.c2c_only)     p.set('c2c_only',    'true')
    if (filters.vendor_only)  p.set('vendor_only', 'true')
    if (filters.days)         p.set('days',        filters.days)
    return p.toString()
  }

  const fetchJobs = useCallback(async (pg = 1) => {
    setLoading(true)
    setError(null)
    try {
      const res  = await authFetch(`/api/jobs?${buildParams(pg)}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setJobs(data.jobs)
      setTotal(data.total)
      setPages(data.pages)
    } catch (e) {
      setError('Could not load jobs. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [search, filters, authFetch])

  const fetchStats = async () => {
    try {
      const res  = await authFetch('/api/stats')
      const data = await res.json()
      setStats(data)
    } catch {}
  }

  const handleTriggerScrape = async () => {
    try {
      await authFetch('/api/scrape/trigger', { method: 'POST' })
      setTimeout(fetchStats, 2000)
    } catch {}
  }

  const handleToggleApply = async (job, isApplied) => {
    try {
      if (isApplied) {
        await authFetch(`/api/jobs/${job.id}/apply`, { method: 'DELETE' })
        setAppliedJobIds(prev => { const s = new Set(prev); s.delete(job.id); return s })
      } else {
        await authFetch(`/api/jobs/${job.id}/apply`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({
            job_title:    job.title,
            job_category: job.role_category,
            job_url:      job.url,
          }),
        })
        setAppliedJobIds(prev => new Set([...prev, job.id]))
      }
    } catch {}
  }

  const handleFilterChange = (key, value) => {
    setFilters(f => ({ ...f, [key]: value }))
    setPage(1)
  }

  const handleReset = () => {
    setFilters(DEFAULT_FILTERS)
    setSearch('')
    setPage(1)
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      <Header
        search={search}
        onSearch={setSearch}
        stats={stats}
        onTriggerScrape={handleTriggerScrape}
        user={user}
        onLogout={handleLogout}
      />

      <div className="max-w-screen-2xl mx-auto w-full px-4 flex gap-5 flex-1">
        <FilterPanel
          filters={filters}
          onFilterChange={handleFilterChange}
          stats={stats}
          onReset={handleReset}
        />

        <main className="flex-1 py-4 min-w-0">
          <StatsBar stats={stats} filtered={total} />

          <SourceBar
            stats={stats}
            activeSource={filters.source}
            onSelect={(src) => handleFilterChange('source', src)}
          />

          {error && (
            <div className="mb-4 p-4 bg-red-900/30 border border-red-500/40 rounded-xl text-sm text-red-300">
              {error}
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center py-20 gap-3 text-slate-500">
              <Loader2 size={20} className="animate-spin" />
              <span className="text-sm">Loading jobs…</span>
            </div>
          )}

          {!loading && jobs.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-500">
              <SearchX size={36} className="text-slate-600" />
              <div className="text-center">
                <p className="font-medium text-slate-400">No jobs found</p>
                <p className="text-sm mt-1">Try adjusting your filters or trigger a new scrape.</p>
              </div>
              <button onClick={handleReset} className="btn-ghost text-xs mt-2">Reset filters</button>
            </div>
          )}

          {!loading && jobs.length > 0 && (() => {
            const topMatches  = jobs.filter(j => (j.semantic_score ?? 0) >= 0.30)
            const regularJobs = jobs.filter(j => (j.semantic_score ?? 0) <  0.30)
            return (
              <>
                {topMatches.length > 0 && (
                  <div className="mb-6 mt-2">
                    <div className="flex items-center gap-2 mb-3 px-1">
                      <Zap size={14} className="text-yellow-400" />
                      <span className="text-sm font-semibold text-yellow-300">Top AI Matches</span>
                      <span className="badge bg-yellow-500/10 text-yellow-400 border border-yellow-500/30 text-[10px]">
                        {topMatches.length} jobs · ≥30% AI score
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                      {topMatches.map(job => (
                        <JobCard
                          key={job.id}
                          job={job}
                          applied={appliedJobIds.has(job.id)}
                          onToggleApply={handleToggleApply}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {regularJobs.length > 0 && (
                  <div>
                    {topMatches.length > 0 && (
                      <div className="flex items-center gap-2 mb-3 px-1">
                        <LayoutGrid size={14} className="text-slate-400" />
                        <span className="text-sm font-semibold text-slate-400">Other Jobs</span>
                        <span className="badge bg-slate-700/50 text-slate-400 border border-slate-600/40 text-[10px]">
                          {regularJobs.length} jobs
                        </span>
                      </div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                      {regularJobs.map(job => (
                        <JobCard
                          key={job.id}
                          job={job}
                          applied={appliedJobIds.has(job.id)}
                          onToggleApply={handleToggleApply}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {pages > 1 && (
                  <Pagination
                    page={page}
                    pages={pages}
                    total={total}
                    perPage={perPage}
                    onPageChange={setPage}
                  />
                )}
              </>
            )
          })()}
        </main>
      </div>
    </div>
  )
}

// ── Root router ───────────────────────────────────────────────────────────────

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<RedirectIfAuth><LoginPage /></RedirectIfAuth>} />
      <Route path="/admin" element={<RequireAdmin><AdminPage /></RequireAdmin>} />
      <Route path="/"      element={<RequireAuth><JobBoardPage /></RequireAuth>} />
      <Route path="*"      element={<Navigate to="/" replace />} />
    </Routes>
  )
}

// ── Pagination ────────────────────────────────────────────────────────────────

function Pagination({ page, pages, total, perPage, onPageChange }) {
  const start = (page - 1) * perPage + 1
  const end   = Math.min(page * perPage, total)

  const pageNums = () => {
    const nums = []
    const delta = 2
    for (let i = Math.max(1, page - delta); i <= Math.min(pages, page + delta); i++) {
      nums.push(i)
    }
    return nums
  }

  return (
    <div className="flex items-center justify-between mt-6 py-3 border-t border-slate-700/50">
      <span className="text-xs text-slate-500">{start}–{end} of {total.toLocaleString()} jobs</span>
      <div className="flex items-center gap-1">
        <button onClick={() => onPageChange(page - 1)} disabled={page === 1} className="btn-ghost px-2 py-1.5 disabled:opacity-30">
          <ChevronLeft size={14} />
        </button>
        {page > 3 && <><PageBtn n={1} current={page} onClick={onPageChange} /><span className="text-slate-600 text-xs px-1">…</span></>}
        {pageNums().map(n => <PageBtn key={n} n={n} current={page} onClick={onPageChange} />)}
        {page < pages - 2 && <><span className="text-slate-600 text-xs px-1">…</span><PageBtn n={pages} current={page} onClick={onPageChange} /></>}
        <button onClick={() => onPageChange(page + 1)} disabled={page === pages} className="btn-ghost px-2 py-1.5 disabled:opacity-30">
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  )
}

function PageBtn({ n, current, onClick }) {
  return (
    <button
      onClick={() => onClick(n)}
      className={`w-7 h-7 rounded-md text-xs font-medium transition-all
        ${n === current ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-700 hover:text-white'}`}
    >
      {n}
    </button>
  )
}
