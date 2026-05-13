import { useState, useEffect, useCallback, useRef } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import {
  ChevronLeft, ChevronRight, Loader2, SearchX, LayoutGrid, Zap,
  Globe2, Linkedin, RefreshCw, Search, Brain, Code2, Package, Layers
} from 'lucide-react'
import { useAuth } from './context/AuthContext'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import FilterPanel from './components/FilterPanel'
import JobCard from './components/JobCard'
import LinkedInPostCard from './components/LinkedInPostCard'
import ResumeEditorModal from './components/ResumeEditorModal'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'

const DEFAULT_FILTERS = {
  sort:        'newest',
  days:        '',
  category:    '',
  source:      '',
  c2c_only:    false,
  vendor_only: false,
  remote_only: false,
}

const DOMAINS = [
  { id: 'AIML',   label: 'AI / ML', icon: Brain  },
  { id: 'DOTNET', label: '.NET',    icon: Code2  },
  { id: 'SAP',    label: 'SAP',     icon: Package },
]

// ── Role options per domain (for LinkedIn posts filter) ───────────────────────
const DOMAIN_ROLE_OPTIONS = {
  AIML: [
    'AI Engineer', 'ML Engineer', 'Machine Learning Engineer', 'LLM Engineer',
    'GenAI Engineer', 'Data Scientist', 'Python Developer', 'MLOps Engineer',
    'NLP Engineer', 'Deep Learning Engineer', 'RAG Developer', 'Agentic AI',
    'AI/ML Engineer', 'Python Engineer',
  ],
  DOTNET: [
    '.NET Developer', 'Senior .NET Developer', '.NET Software Engineer',
    '.NET Full Stack Developer', '.NET Backend Developer',
    'C# Developer', 'ASP.NET Developer', 'React Developer', 'Angular Developer',
  ],
  SAP: [
    'SAP TM', 'SAP Transport Management', 'SAP TM Architect',
    'SAP TM Functional Consultant', 'SAP TM Solution Consultant',
    'SAP SCM Consultant', 'S4HANA TM',
  ],
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
  if (loading)        return <FullScreenLoader />
  if (!user)          return <Navigate to="/login" replace />
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
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-red-500" />
    </div>
  )
}

// ── Platform source bar ───────────────────────────────────────────────────────

const PLATFORM_CONFIG = {
  'LinkedIn':        { label: 'LinkedIn',      dot: 'bg-blue-500',    text: 'text-blue-600',    bg: 'bg-blue-50',    border: 'border-blue-200'    },
  'Indeed':          { label: 'Indeed',         dot: 'bg-sky-500',     text: 'text-sky-600',     bg: 'bg-sky-50',     border: 'border-sky-200'     },
  'ZipRecruiter':    { label: 'ZipRecruiter',   dot: 'bg-amber-500',   text: 'text-amber-600',   bg: 'bg-amber-50',   border: 'border-amber-200'   },
  'Glassdoor':       { label: 'Glassdoor',      dot: 'bg-emerald-500', text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  'Monster':         { label: 'Monster',        dot: 'bg-purple-500',  text: 'text-purple-600',  bg: 'bg-purple-50',  border: 'border-purple-200'  },
  'Dice.com':        { label: 'Dice.com',       dot: 'bg-red-500',     text: 'text-red-600',     bg: 'bg-red-50',     border: 'border-red-200'     },
  'Adzuna':          { label: 'Adzuna',         dot: 'bg-orange-500',  text: 'text-orange-600',  bg: 'bg-orange-50',  border: 'border-orange-200'  },
  'WeWorkRemotely':  { label: 'WeWorkRemotely', dot: 'bg-indigo-500',  text: 'text-indigo-600',  bg: 'bg-indigo-50',  border: 'border-indigo-200'  },
  'Remotive.com':    { label: 'Remotive',       dot: 'bg-teal-500',    text: 'text-teal-600',    bg: 'bg-teal-50',    border: 'border-teal-200'    },
  'Himalayas.app':   { label: 'Himalayas',      dot: 'bg-violet-500',  text: 'text-violet-600',  bg: 'bg-violet-50',  border: 'border-violet-200'  },
  'Arbeitnow':       { label: 'Arbeitnow',      dot: 'bg-cyan-500',    text: 'text-cyan-600',    bg: 'bg-cyan-50',    border: 'border-cyan-200'    },
  'The Muse':        { label: 'The Muse',       dot: 'bg-pink-500',    text: 'text-pink-600',    bg: 'bg-pink-50',    border: 'border-pink-200'    },
  'Jobicy.com':      { label: 'Jobicy',         dot: 'bg-blue-400',    text: 'text-blue-500',    bg: 'bg-blue-50',    border: 'border-blue-100'    },
  'WorkingNomads':   { label: 'WorkingNomads',  dot: 'bg-cyan-400',    text: 'text-cyan-500',    bg: 'bg-cyan-50',    border: 'border-cyan-100'    },
  "HN Who's Hiring": { label: "HN Hiring",      dot: 'bg-rose-500',    text: 'text-rose-600',    bg: 'bg-rose-50',    border: 'border-rose-200'    },
}

const FEATURED_PLATFORMS = ['LinkedIn', 'Indeed', 'ZipRecruiter', 'Glassdoor', 'Monster', 'Dice.com']

function SourceBar({ stats, activeSource, onSelect }) {
  const counts  = stats?.by_source ?? {}
  const allSrcs = stats?.all_sources ?? []

  const featured = FEATURED_PLATFORMS.map(name => ({ name, count: counts[name] ?? 0, pinned: true }))
  const rest     = allSrcs
    .filter(s => !FEATURED_PLATFORMS.includes(s) && (counts[s] ?? 0) > 0)
    .map(name => ({ name, count: counts[name] ?? 0, pinned: false }))

  const platforms = [...featured, ...rest]

  return (
    <div className="mb-5">
      <div className="flex items-center gap-2 mb-2.5 px-0.5">
        <Globe2 size={13} className="text-gray-400 shrink-0" />
        <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-widest">Job Platforms</span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
        {platforms.map(({ name, count }) => {
          const cfg      = PLATFORM_CONFIG[name] ?? { label: name, dot: 'bg-gray-400', text: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200' }
          const isActive = activeSource === name
          const isEmpty  = count === 0
          return (
            <button
              key={name}
              onClick={() => !isEmpty && onSelect(isActive ? '' : name)}
              title={isEmpty ? 'No jobs scraped yet' : `${count.toLocaleString()} jobs from ${cfg.label}`}
              className={`shrink-0 flex flex-col items-start gap-1 px-3 py-2 rounded-xl border transition-all duration-150
                ${isActive
                  ? `${cfg.bg} ${cfg.border} ${cfg.text} ring-1 ring-offset-0 ring-current shadow-sm scale-[1.03]`
                  : isEmpty
                    ? 'bg-gray-50 border-gray-200 text-gray-300 cursor-default'
                    : `bg-white border-gray-200 ${cfg.text} hover:${cfg.bg} hover:${cfg.border} hover:scale-[1.02]`
                }`}
            >
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isEmpty ? 'bg-gray-300' : cfg.dot}`} />
                <span className="text-[11px] font-semibold whitespace-nowrap">{cfg.label}</span>
              </div>
              <span className={`text-[10px] font-mono pl-3 ${isEmpty ? 'text-gray-300' : 'opacity-70'}`}>
                {isEmpty ? 'no jobs yet' : `${count.toLocaleString()} jobs`}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── LinkedIn Posts tab ────────────────────────────────────────────────────────

const TIME_FILTERS = [
  { label: 'Last 1 hr',  value: 1  },
  { label: 'Last 2 hrs', value: 2  },
  { label: 'Last 5 hrs', value: 5  },
  { label: '> 5 hrs',    value: 'gt5' },
  { label: 'All 24 hrs', value: null },
]

function LinkedInPostsTab({ authFetch, domain }) {
  const [posts,    setPosts]    = useState([])
  const [total,    setTotal]    = useState(0)
  const [pages,    setPages]    = useState(1)
  const [page,     setPage]     = useState(1)
  const [search,   setSearch]   = useState('')
  const [role,     setRole]     = useState('')
  const [timeFilter, setTimeFilter] = useState(null)  // null = all 24h
  const [loading,  setLoading]  = useState(false)
  const [status,   setStatus]   = useState(null)
  const [scraping, setScraping] = useState(false)
  const searchRef  = useRef(null)
  const perPage    = 30

  const fetchPosts = useCallback(async (pg = 1) => {
    setLoading(true)
    try {
      const p = new URLSearchParams({ page: pg, per_page: perPage, domain })
      if (search) p.set('search', search)
      if (role)   p.set('role',   role)
      if (timeFilter && timeFilter !== 'gt5') p.set('hours', timeFilter)
      const res  = await authFetch(`/api/linkedin-posts?${p}`)
      const data = await res.json()
      // For ">5 hrs" filter — client-side: exclude posts from last 5h
      let postsData = data.posts ?? []
      if (timeFilter === 'gt5') {
        const cutoff = Date.now() - 5 * 60 * 60 * 1000
        postsData = postsData.filter(p => {
          const t = new Date(p.scraped_at || p.posted_at || 0).getTime()
          return t < cutoff
        })
      }
      setPosts(postsData)
      setTotal(timeFilter === 'gt5' ? postsData.length : (data.total ?? 0))
      setPages(timeFilter === 'gt5' ? 1 : (data.pages ?? 1))
      setStatus(data)
    } catch {}
    finally { setLoading(false) }
  }, [search, role, domain, timeFilter, authFetch])

  // Reset on domain change
  useEffect(() => {
    setPage(1)
    setSearch('')
    setRole('')
    setTimeFilter(null)
  }, [domain])

  useEffect(() => {
    clearTimeout(searchRef.current)
    searchRef.current = setTimeout(() => { setPage(1); fetchPosts(1) }, 350)
  }, [search])

  useEffect(() => { fetchPosts(page) }, [page, role, domain, timeFilter])

  useEffect(() => {
    const id = setInterval(() => fetchPosts(page), 15 * 60 * 1000)
    return () => clearInterval(id)
  }, [page, fetchPosts])

  const handleTriggerScrape = async () => {
    setScraping(true)
    try {
      await authFetch(`/api/linkedin-posts/scrape?domain=${domain}`, { method: 'POST' })
      setTimeout(() => fetchPosts(page), 3000)
    } catch {}
    finally { setTimeout(() => setScraping(false), 3000) }
  }

  const roleOptions = DOMAIN_ROLE_OPTIONS[domain] ?? []

  const noApiKey = status && (status.apis_active ?? []).length === 1
    && (status.apis_active[0] ?? '').startsWith('No API')

  return (
    <div className="flex-1 py-4 min-w-0">
      {/* API key warning */}
      {noApiKey && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5">
          <span className="text-amber-500 text-sm shrink-0 mt-0.5">⚠</span>
          <div className="text-xs leading-relaxed text-amber-700">
            <span className="font-semibold">Apify token required for LinkedIn posts.</span>
            <span className="ml-1 text-amber-600">
              LinkedIn blocks all free search tools — only Apify (real browser) can fetch posts without login.
              Add <code className="bg-amber-100 px-1 rounded font-mono">APIFY_TOKEN=…</code> to <code className="bg-amber-100 px-1 rounded font-mono">/data/env.conf</code> on EC2.
            </span>
          </div>
        </div>
      )}

      {/* Status bar */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${(status?.total_posts ?? 0) > 0 ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
            <span className="text-xs text-gray-500">
              {(status?.total_posts ?? 0).toLocaleString()} posts · refreshed every 15 min
            </span>
          </div>
          {status?.last_scraped && (
            <span className="text-[11px] text-gray-400">
              Last: {new Date(status.last_scraped).toLocaleTimeString()}
            </span>
          )}
        </div>

        <button
          onClick={handleTriggerScrape}
          disabled={scraping || status?.is_scraping}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
            bg-red-50 text-red-600 border border-red-200
            hover:bg-red-100 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          <RefreshCw size={12} className={scraping || status?.is_scraping ? 'animate-spin' : ''} />
          {scraping || status?.is_scraping ? 'Scraping…' : 'Refresh Now'}
        </button>
      </div>

      {/* Search + role filter */}
      <div className="flex gap-2 mb-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search posts, authors…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input w-full pl-8"
          />
        </div>
        <select
          value={role}
          onChange={e => { setRole(e.target.value); setPage(1) }}
          className="input min-w-40"
        >
          <option value="">All roles</option>
          {roleOptions.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>

      {/* Time filter pills */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        <span className="text-[11px] text-gray-400 font-medium uppercase tracking-wider">Posted:</span>
        {TIME_FILTERS.map(f => (
          <button
            key={String(f.value)}
            onClick={() => { setTimeFilter(f.value); setPage(1) }}
            className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all
              ${timeFilter === f.value
                ? 'bg-red-600 text-white border-red-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-red-300 hover:text-red-600'}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20 gap-3 text-gray-400">
          <Loader2 size={20} className="animate-spin text-red-500" />
          <span className="text-sm">Loading posts…</span>
        </div>
      )}

      {!loading && posts.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-gray-400">
          <Linkedin size={36} className="text-gray-300" />
          <div className="text-center">
            <p className="font-medium text-gray-600">No LinkedIn posts yet</p>
            <p className="text-sm mt-1 text-gray-400">Click "Refresh Now" to pull the latest posts.</p>
          </div>
          <button
            onClick={handleTriggerScrape}
            disabled={scraping}
            className="mt-2 btn-primary text-xs"
          >
            <RefreshCw size={12} className={scraping ? 'animate-spin' : ''} />
            Fetch Posts Now
          </button>
        </div>
      )}

      {!loading && posts.length > 0 && (
        <>
          <div className="mb-3 flex items-center gap-2 px-1">
            <Linkedin size={13} className="text-blue-500" />
            <span className="text-sm font-semibold text-gray-700">LinkedIn Posts</span>
            <span className="badge bg-blue-50 text-blue-600 border border-blue-100 text-[10px]">
              {total.toLocaleString()} posts · past 24h
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {posts.map(post => <LinkedInPostCard key={post.id} post={post} />)}
          </div>

          {pages > 1 && (
            <Pagination page={page} pages={pages} total={total} perPage={perPage} onPageChange={setPage} />
          )}
        </>
      )}
    </div>
  )
}

// ── Source Board Tab (LinkedIn Board / Dice Board) ────────────────────────────
// Shows jobs from a single source platform, filtered to current domain, past 24h.

function SourceBoardTab({ source, domain, authFetch, appliedJobIds, onToggleApply }) {
  const [jobs,    setJobs]    = useState([])
  const [total,   setTotal]   = useState(0)
  const [pages,   setPages]   = useState(1)
  const [page,    setPage]    = useState(1)
  const [loading, setLoading] = useState(false)
  const [remoteOnly, setRemoteOnly] = useState(false)
  const perPage = 30

  const fetchBoard = useCallback(async (pg = 1) => {
    setLoading(true)
    try {
      const p = new URLSearchParams({
        source,
        domain,
        page:       pg,
        per_page:   perPage,
        sort:       'posted',
        strict_24h: 'true',
      })
      if (remoteOnly) p.set('remote_only', 'true')
      const res  = await authFetch(`/api/jobs?${p}`)
      const data = await res.json()
      setJobs(data.jobs ?? [])
      setTotal(data.total ?? 0)
      setPages(data.pages ?? 1)
    } catch {}
    finally { setLoading(false) }
  }, [source, domain, authFetch, remoteOnly])

  // Reset page + refetch when domain or remoteOnly changes
  useEffect(() => { setPage(1); fetchBoard(1) }, [domain, remoteOnly])
  useEffect(() => { fetchBoard(page) }, [page])

  // Auto-refresh every 10 minutes
  useEffect(() => {
    const id = setInterval(() => fetchBoard(page), 10 * 60 * 1000)
    return () => clearInterval(id)
  }, [page, fetchBoard])

  const cfg = source === 'LinkedIn'
    ? { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', dot: 'bg-blue-500', label: 'LinkedIn Job Board' }
    : { color: 'text-red-600',  bg: 'bg-red-50',  border: 'border-red-200',  dot: 'bg-red-500',  label: 'Dice.com Job Board' }

  return (
    <div className="flex-1 py-4 min-w-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-2.5">
          <span className={`w-2.5 h-2.5 rounded-full ${cfg.dot} animate-pulse`} />
          <span className="text-sm font-semibold text-gray-800">{cfg.label}</span>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${cfg.bg} ${cfg.border} ${cfg.color}`}>
            past 24 h only
          </span>
          {total > 0 && (
            <span className="text-[11px] text-gray-400 font-mono">{total.toLocaleString()} jobs</span>
          )}
        </div>
        {/* Remote toggle */}
        <label className="flex items-center gap-2 cursor-pointer">
          <div
            className={`relative w-8 h-4 rounded-full transition-colors duration-200 border
              ${remoteOnly ? 'bg-blue-100 border-blue-300' : 'bg-gray-100 border-gray-200'}`}
            onClick={() => setRemoteOnly(v => !v)}
          >
            <div className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full transition-all duration-200
              ${remoteOnly ? 'bg-blue-500 translate-x-4' : 'bg-gray-400 translate-x-0'}`} />
          </div>
          <span className={`text-xs ${remoteOnly ? 'text-blue-700 font-medium' : 'text-gray-500'}`}>
            Remote only
          </span>
        </label>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20 gap-3 text-gray-400">
          <Loader2 size={20} className="animate-spin text-red-500" />
          <span className="text-sm">Loading…</span>
        </div>
      )}

      {!loading && jobs.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-gray-400">
          <Layers size={36} className="text-gray-300" />
          <div className="text-center">
            <p className="font-medium text-gray-600">No {source} jobs in the last 24 h</p>
            <p className="text-sm mt-1 text-gray-400">
              Jobs post between 9 AM – 5 PM EST. Check back during active hours.
            </p>
          </div>
        </div>
      )}

      {!loading && jobs.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {jobs.map(job => (
              <JobCard
                key={job.id}
                job={job}
                applied={appliedJobIds.has(job.id)}
                onToggleApply={onToggleApply}
              />
            ))}
          </div>
          {pages > 1 && (
            <Pagination page={page} pages={pages} total={total} perPage={perPage} onPageChange={setPage} />
          )}
        </>
      )}
    </div>
  )
}


// ── Job board page ────────────────────────────────────────────────────────────

function JobBoardPage() {
  const { authFetch, user, logout } = useAuth()
  const navigate = useNavigate()

  const [domain,        setDomain]        = useState('AIML')
  const [subTab,        setSubTab]        = useState('jobs')
  const [showResume,    setShowResume]    = useState(false)
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

  useEffect(() => {
    authFetch('/api/user/applications')
      .then(r => r.json())
      .then(d => setAppliedJobIds(new Set(d.applied_job_ids ?? [])))
      .catch(() => {})
  }, [authFetch])

  // Reset filters and sub-tab when switching domain
  const handleDomainChange = (newDomain) => {
    setDomain(newDomain)
    setSubTab('jobs')
    setFilters(DEFAULT_FILTERS)
    setSearch('')
    setPage(1)
  }

  useEffect(() => {
    clearTimeout(searchRef.current)
    searchRef.current = setTimeout(() => { setPage(1); fetchJobs(1) }, 350)
  }, [search])

  useEffect(() => { fetchJobs(page) }, [filters, page, domain])

  useEffect(() => {
    fetchStats()
    const id = setInterval(fetchStats, 15_000)
    return () => clearInterval(id)
  }, [])

  const buildParams = (pg) => {
    const p = new URLSearchParams({ page: pg, per_page: perPage, sort: filters.sort, domain })
    if (search)                p.set('search',      search)
    if (filters.category)      p.set('category',    filters.category)
    if (filters.source)        p.set('source',      filters.source)
    if (filters.c2c_only)      p.set('c2c_only',    'true')
    if (filters.vendor_only)   p.set('vendor_only', 'true')
    if (filters.remote_only)   p.set('remote_only', 'true')
    if (filters.days)          p.set('days',        filters.days)
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
  }, [search, filters, domain, authFetch])

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
          body:    JSON.stringify({ job_title: job.title, job_category: job.role_category, job_url: job.url }),
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

  const activeDomain = DOMAINS.find(d => d.id === domain)

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header
        search={search}
        onSearch={setSearch}
        stats={stats}
        onTriggerScrape={handleTriggerScrape}
        user={user}
        onLogout={handleLogout}
        onOpenResumeEditor={() => setShowResume(true)}
      />

      {showResume && (
        <ResumeEditorModal
          authFetch={authFetch}
          onClose={() => setShowResume(false)}
        />
      )}

      {/* Domain tab bar */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-screen-2xl mx-auto px-4">
          <div className="flex gap-0">
            {DOMAINS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => handleDomainChange(id)}
                className={`flex items-center gap-2 px-6 py-3.5 text-sm font-semibold border-b-2 transition-all
                  ${domain === id
                    ? 'border-red-500 text-red-600 bg-red-50/40'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                  }`}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-screen-2xl mx-auto w-full px-4 flex gap-5 flex-1">
        {/* Filter panel — All Jobs sub-tab only */}
        {subTab === 'jobs' && (
          <FilterPanel
            filters={filters}
            onFilterChange={handleFilterChange}
            stats={stats}
            onReset={handleReset}
            domain={domain}
          />
        )}

        <main className="flex-1 py-4 min-w-0">
          {/* Sub-tab bar */}
          <div className="flex gap-1.5 mb-5 flex-wrap">
            <button
              onClick={() => setSubTab('jobs')}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border transition-all
                ${subTab === 'jobs'
                  ? 'bg-red-600 text-white border-red-600 shadow-sm'
                  : 'bg-white text-gray-500 border-gray-200 hover:text-gray-700 hover:bg-gray-50'
                }`}
            >
              <LayoutGrid size={13} />
              All Jobs
            </button>
            <button
              onClick={() => setSubTab('linkedin_board')}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border transition-all
                ${subTab === 'linkedin_board'
                  ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                  : 'bg-white text-gray-500 border-gray-200 hover:text-gray-700 hover:bg-gray-50'
                }`}
            >
              <Linkedin size={13} />
              LinkedIn Board
            </button>
            <button
              onClick={() => setSubTab('dice_board')}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border transition-all
                ${subTab === 'dice_board'
                  ? 'bg-red-700 text-white border-red-700 shadow-sm'
                  : 'bg-white text-gray-500 border-gray-200 hover:text-gray-700 hover:bg-gray-50'
                }`}
            >
              <Layers size={13} />
              Dice Board
            </button>
            <button
              onClick={() => setSubTab('linkedin')}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border transition-all
                ${subTab === 'linkedin'
                  ? 'bg-red-600 text-white border-red-600 shadow-sm'
                  : 'bg-white text-gray-500 border-gray-200 hover:text-gray-700 hover:bg-gray-50'
                }`}
            >
              <Linkedin size={13} />
              LinkedIn Posts
            </button>
          </div>

          {/* LinkedIn Board sub-tab */}
          {subTab === 'linkedin_board' && (
            <SourceBoardTab
              source="LinkedIn"
              domain={domain}
              authFetch={authFetch}
              appliedJobIds={appliedJobIds}
              onToggleApply={handleToggleApply}
            />
          )}

          {/* Dice Board sub-tab */}
          {subTab === 'dice_board' && (
            <SourceBoardTab
              source="Dice.com"
              domain={domain}
              authFetch={authFetch}
              appliedJobIds={appliedJobIds}
              onToggleApply={handleToggleApply}
            />
          )}

          {/* LinkedIn posts sub-tab */}
          {subTab === 'linkedin' && (
            <LinkedInPostsTab authFetch={authFetch} domain={domain} />
          )}

          {/* Jobs sub-tab */}
          {subTab === 'jobs' && (
            <>
              <StatsBar stats={stats} filtered={total} />

              <SourceBar
                stats={stats}
                activeSource={filters.source}
                onSelect={(src) => handleFilterChange('source', src)}
              />

              {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">
                  {error}
                </div>
              )}

              {loading && (
                <div className="flex items-center justify-center py-20 gap-3 text-gray-400">
                  <Loader2 size={20} className="animate-spin text-red-500" />
                  <span className="text-sm">Loading jobs…</span>
                </div>
              )}

              {!loading && jobs.length === 0 && (
                <div className="flex flex-col items-center justify-center py-20 gap-3 text-gray-400">
                  <SearchX size={36} className="text-gray-300" />
                  <div className="text-center">
                    <p className="font-medium text-gray-600">No jobs found</p>
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
                          <Zap size={14} className="text-amber-500" />
                          <span className="text-sm font-semibold text-gray-700">Top Matches</span>
                          <span className="badge bg-amber-50 text-amber-600 border border-amber-200 text-[10px]">
                            {topMatches.length} jobs · ≥30% match score
                          </span>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                          {topMatches.map(job => (
                            <JobCard key={job.id} job={job} applied={appliedJobIds.has(job.id)} onToggleApply={handleToggleApply} />
                          ))}
                        </div>
                      </div>
                    )}

                    {regularJobs.length > 0 && (
                      <div>
                        {topMatches.length > 0 && (
                          <div className="flex items-center gap-2 mb-3 px-1">
                            <LayoutGrid size={14} className="text-gray-400" />
                            <span className="text-sm font-semibold text-gray-500">Other Jobs</span>
                            <span className="badge bg-gray-100 text-gray-500 border border-gray-200 text-[10px]">
                              {regularJobs.length} jobs
                            </span>
                          </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                          {regularJobs.map(job => (
                            <JobCard key={job.id} job={job} applied={appliedJobIds.has(job.id)} onToggleApply={handleToggleApply} />
                          ))}
                        </div>
                      </div>
                    )}

                    {pages > 1 && (
                      <Pagination page={page} pages={pages} total={total} perPage={perPage} onPageChange={setPage} />
                    )}
                  </>
                )
              })()}
            </>
          )}
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
    <div className="flex items-center justify-between mt-6 py-3 border-t border-gray-200">
      <span className="text-xs text-gray-400">{start}–{end} of {total.toLocaleString()} jobs</span>
      <div className="flex items-center gap-1">
        <button onClick={() => onPageChange(page - 1)} disabled={page === 1}
          className="btn-ghost px-2 py-1.5 disabled:opacity-30">
          <ChevronLeft size={14} />
        </button>
        {page > 3 && <><PageBtn n={1} current={page} onClick={onPageChange} /><span className="text-gray-300 text-xs px-1">…</span></>}
        {pageNums().map(n => <PageBtn key={n} n={n} current={page} onClick={onPageChange} />)}
        {page < pages - 2 && <><span className="text-gray-300 text-xs px-1">…</span><PageBtn n={pages} current={page} onClick={onPageChange} /></>}
        <button onClick={() => onPageChange(page + 1)} disabled={page === pages}
          className="btn-ghost px-2 py-1.5 disabled:opacity-30">
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
        ${n === current ? 'bg-red-600 text-white' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-900'}`}
    >
      {n}
    </button>
  )
}
