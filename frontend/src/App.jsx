import { useState, useEffect, useCallback, useRef } from 'react'
import { ChevronLeft, ChevronRight, Loader2, SearchX, LayoutGrid, Zap } from 'lucide-react'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import FilterPanel from './components/FilterPanel'
import JobCard from './components/JobCard'

const API = ''  // uses Vite proxy → http://localhost:8000

const DEFAULT_FILTERS = {
  sort:        'newest',
  days:        '',
  category:    '',
  source:      '',
  c2c_only:    false,
  vendor_only: false,
}

export default function App() {
  const [search,  setSearch]  = useState('')
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [page,    setPage]    = useState(1)
  const [jobs,    setJobs]    = useState([])
  const [total,   setTotal]   = useState(0)
  const [pages,   setPages]   = useState(1)
  const [stats,   setStats]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const perPage    = 30
  const searchRef  = useRef(null)

  // Debounced search
  useEffect(() => {
    clearTimeout(searchRef.current)
    searchRef.current = setTimeout(() => {
      setPage(1)
      fetchJobs(1)
    }, 350)
  }, [search])

  // Refetch on filter/page changes
  useEffect(() => {
    fetchJobs(page)
  }, [filters, page])

  // Poll stats every 15 s
  useEffect(() => {
    fetchStats()
    const id = setInterval(fetchStats, 15_000)
    return () => clearInterval(id)
  }, [])

  const buildParams = (pg) => {
    const p = new URLSearchParams({
      page:     pg,
      per_page: perPage,
      sort:     filters.sort,
    })
    if (search)           p.set('search', search)
    if (filters.category) p.set('category', filters.category)
    if (filters.source)   p.set('source', filters.source)
    if (filters.c2c_only)    p.set('c2c_only', 'true')
    if (filters.vendor_only) p.set('vendor_only', 'true')
    if (filters.days)     p.set('days', filters.days)
    return p.toString()
  }

  const fetchJobs = useCallback(async (pg = 1) => {
    setLoading(true)
    setError(null)
    try {
      const res  = await fetch(`${API}/api/jobs?${buildParams(pg)}`)
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
  }, [search, filters])

  const fetchStats = async () => {
    try {
      const res  = await fetch(`${API}/api/stats`)
      const data = await res.json()
      setStats(data)
    } catch {}
  }

  const handleTriggerScrape = async () => {
    try {
      await fetch(`${API}/api/scrape/trigger`, { method: 'POST' })
      setTimeout(fetchStats, 2000)
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

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      <Header
        search={search}
        onSearch={setSearch}
        stats={stats}
        onTriggerScrape={handleTriggerScrape}
      />

      <div className="max-w-screen-2xl mx-auto w-full px-4 flex gap-5 flex-1">
        {/* Sidebar */}
        <FilterPanel
          filters={filters}
          onFilterChange={handleFilterChange}
          stats={stats}
          onReset={handleReset}
        />

        {/* Main */}
        <main className="flex-1 py-4 min-w-0">
          <StatsBar stats={stats} filtered={total} />

          {/* Error banner */}
          {error && (
            <div className="mb-4 p-4 bg-red-900/30 border border-red-500/40 rounded-xl text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-20 gap-3 text-slate-500">
              <Loader2 size={20} className="animate-spin" />
              <span className="text-sm">Loading jobs…</span>
            </div>
          )}

          {/* Empty state */}
          {!loading && jobs.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-500">
              <SearchX size={36} className="text-slate-600" />
              <div className="text-center">
                <p className="font-medium text-slate-400">No jobs found</p>
                <p className="text-sm mt-1">Try adjusting your filters or trigger a new scrape.</p>
              </div>
              <button onClick={handleReset} className="btn-ghost text-xs mt-2">
                Reset filters
              </button>
            </div>
          )}

          {/* Job grid */}
          {!loading && jobs.length > 0 && (() => {
            const topMatches  = jobs.filter(j => (j.semantic_score ?? 0) >= 0.30)
            const regularJobs = jobs.filter(j => (j.semantic_score ?? 0) <  0.30)
            return (
              <>
                {/* Top AI Matches section */}
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
                      {topMatches.map(job => <JobCard key={job.id} job={job} />)}
                    </div>
                  </div>
                )}

                {/* All other jobs */}
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
                      {regularJobs.map(job => <JobCard key={job.id} job={job} />)}
                    </div>
                  </div>
                )}

                {/* Pagination */}
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
      <span className="text-xs text-slate-500">
        {start}–{end} of {total.toLocaleString()} jobs
      </span>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="btn-ghost px-2 py-1.5 disabled:opacity-30"
        >
          <ChevronLeft size={14} />
        </button>

        {page > 3 && (
          <>
            <PageBtn n={1} current={page} onClick={onPageChange} />
            <span className="text-slate-600 text-xs px-1">…</span>
          </>
        )}

        {pageNums().map(n => (
          <PageBtn key={n} n={n} current={page} onClick={onPageChange} />
        ))}

        {page < pages - 2 && (
          <>
            <span className="text-slate-600 text-xs px-1">…</span>
            <PageBtn n={pages} current={page} onClick={onPageChange} />
          </>
        )}

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page === pages}
          className="btn-ghost px-2 py-1.5 disabled:opacity-30"
        >
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
        ${n === current
          ? 'bg-blue-600 text-white'
          : 'text-slate-400 hover:bg-slate-700 hover:text-white'}`}
    >
      {n}
    </button>
  )
}
