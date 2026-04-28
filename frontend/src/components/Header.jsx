import { useState } from 'react'
import { Search, RefreshCw, Clock, Zap } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function Header({ search, onSearch, stats, onTriggerScrape }) {
  const [triggering, setTriggering] = useState(false)

  const handleTrigger = async () => {
    setTriggering(true)
    await onTriggerScrape()
    setTimeout(() => setTriggering(false), 2000)
  }

  const lastScraped = stats?.last_scraped
    ? formatDistanceToNow(new Date(stats.last_scraped), { addSuffix: true })
    : 'never'

  const nextScrape = stats?.next_scrape
    ? formatDistanceToNow(new Date(stats.next_scrape), { addSuffix: true })
    : '—'

  return (
    <header className="header-glow sticky top-0 z-50">
      <div className="max-w-screen-2xl mx-auto px-4 py-3">
        {/* Top row */}
        <div className="flex items-center gap-4">
          {/* Logo */}
          <div className="flex items-center gap-3 min-w-fit">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-900/50 shrink-0"
              style={{ background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)' }}>
              <span className="text-white font-bold text-sm tracking-tight" style={{ fontFamily: 'Georgia, serif' }}>CN</span>
            </div>
            <div className="leading-none">
              <div
                className="text-xl font-black tracking-widest bg-clip-text text-transparent"
                style={{
                  fontFamily: "'Cinzel', Georgia, serif",
                  background: 'linear-gradient(90deg, #a5b4fc 0%, #c4b5fd 50%, #818cf8 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  letterSpacing: '0.12em',
                }}
              >
                CYBER NIRVANA
              </div>
              <div className="text-[10px] text-slate-500 font-medium tracking-widest uppercase mt-0.5">
                AI / ML Contract Jobs
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="flex-1 max-w-2xl relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="text"
              className="input w-full pl-9"
              placeholder="Search by title, company, or keyword…"
              value={search}
              onChange={e => onSearch(e.target.value)}
            />
          </div>

          {/* Scraper controls */}
          <div className="flex items-center gap-3 ml-auto">
            {/* Status pill */}
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border
              ${stats?.is_scraping
                ? 'bg-blue-500/10 border-blue-500/40 text-blue-300 scraping-active'
                : 'bg-slate-800 border-slate-600 text-slate-400'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${stats?.is_scraping ? 'bg-blue-400 animate-pulse' : 'bg-slate-500'}`} />
              {stats?.is_scraping ? 'Scraping…' : 'Idle'}
            </div>

            {/* Last run info */}
            <div className="hidden lg:flex items-center gap-1 text-xs text-slate-500">
              <Clock size={11} />
              <span>{lastScraped}</span>
            </div>

            {/* Next run info */}
            <div className="hidden xl:flex items-center gap-1 text-xs text-slate-500">
              <Zap size={11} />
              <span>next {nextScrape}</span>
            </div>

            {/* Trigger button */}
            <button
              onClick={handleTrigger}
              disabled={stats?.is_scraping || triggering}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed text-xs px-3 py-1.5"
            >
              <RefreshCw size={13} className={stats?.is_scraping ? 'animate-spin' : ''} />
              Scrape Now
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
