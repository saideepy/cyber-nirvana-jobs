import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, RefreshCw, Clock, Zap, LogOut, User, Shield, FileText } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function Header({ search, onSearch, stats, onTriggerScrape, user, onLogout, onOpenResumeEditor }) {
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
        <div className="flex items-center gap-4">
          {/* Logo */}
          <div className="flex items-center gap-3 min-w-fit">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-md shadow-red-200/60 shrink-0"
              style={{ background: 'linear-gradient(135deg, #dc2626 0%, #ea580c 100%)' }}>
              <span className="text-white font-bold text-sm tracking-tight" style={{ fontFamily: 'Georgia, serif' }}>CN</span>
            </div>
            <div className="leading-none">
              <div
                className="text-xl font-black tracking-widest bg-clip-text text-transparent"
                style={{
                  fontFamily: "'Cinzel', Georgia, serif",
                  background: 'linear-gradient(90deg, #dc2626 0%, #ea580c 50%, #dc2626 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  letterSpacing: '0.12em',
                }}
              >
                CYBER NIRVANA
              </div>
              <div className="text-[10px] text-gray-400 font-medium tracking-widest uppercase mt-0.5">
                Contract Job Board
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="flex-1 max-w-2xl relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              className="input w-full pl-9"
              placeholder="Search by title, company, or keyword…"
              value={search}
              onChange={e => onSearch(e.target.value)}
            />
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-2 ml-auto">
            {/* Scraper status */}
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border
              ${stats?.is_scraping
                ? 'bg-red-50 border-red-300 text-red-600 scraping-active'
                : 'bg-gray-100 border-gray-200 text-gray-500'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${stats?.is_scraping ? 'bg-red-500 animate-pulse' : 'bg-gray-400'}`} />
              {stats?.is_scraping ? 'Scraping…' : 'Idle'}
            </div>

            <div className="hidden lg:flex items-center gap-1 text-xs text-gray-400">
              <Clock size={11} />
              <span>{lastScraped}</span>
            </div>

            <div className="hidden xl:flex items-center gap-1 text-xs text-gray-400">
              <Zap size={11} />
              <span>next {nextScrape}</span>
            </div>

            {/* Resume Editor — visible across all tabs */}
            <button
              onClick={onOpenResumeEditor}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border
                bg-white text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300 transition-all shadow-sm"
            >
              <FileText size={13} />
              Resume Editor
            </button>

            <button
              onClick={handleTrigger}
              disabled={stats?.is_scraping || triggering}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed text-xs px-3 py-1.5"
            >
              <RefreshCw size={13} className={stats?.is_scraping ? 'animate-spin' : ''} />
              Scrape Now
            </button>

            {user?.is_admin && (
              <Link to="/admin" className="btn-ghost text-xs px-3 py-1.5 text-red-600 hover:text-red-700 hover:bg-red-50">
                <Shield size={13} /> Admin
              </Link>
            )}

            {user && (
              <div className="flex items-center gap-1.5 pl-2 border-l border-gray-200">
                <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 bg-gray-100 rounded-lg border border-gray-200 text-xs text-gray-700">
                  <User size={11} className="text-red-500" />
                  {user.username}
                </div>
                <button
                  onClick={onLogout}
                  className="btn-ghost text-xs px-2 py-1.5 text-red-500 hover:text-red-600 hover:bg-red-50"
                  title="Logout"
                >
                  <LogOut size={13} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
