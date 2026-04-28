import { X, SlidersHorizontal } from 'lucide-react'

const SORT_OPTIONS = [
  { value: 'newest',  label: 'Scraped: Newest' },
  { value: 'posted',  label: 'Posted: Newest'  },
  { value: 'score',   label: 'AI Score'        },
  { value: 'oldest',  label: 'Scraped: Oldest' },
]

const DAY_OPTIONS = [
  { value: '',   label: 'All time'   },
  { value: '1',  label: 'Today'      },
  { value: '3',  label: 'Last 3 days'},
  { value: '7',  label: 'Last 7 days'},
  { value: '14', label: 'Last 14 days'},
]

export default function FilterPanel({ filters, onFilterChange, stats, onReset }) {
  const activeCount = [
    filters.category,
    filters.source,
    filters.c2c_only,
    filters.vendor_only,
    filters.days,
  ].filter(Boolean).length

  return (
    <aside className="w-56 shrink-0 sticky top-[60px] h-[calc(100vh-60px)] overflow-y-auto py-4 pr-1">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <SlidersHorizontal size={14} className="text-blue-400" />
          Filters
          {activeCount > 0 && (
            <span className="badge bg-blue-500/20 text-blue-300 border border-blue-500/30">
              {activeCount}
            </span>
          )}
        </div>
        {activeCount > 0 && (
          <button onClick={onReset} className="text-xs text-slate-500 hover:text-red-400 flex items-center gap-1 transition-colors">
            <X size={11} /> Reset
          </button>
        )}
      </div>

      {/* Sort */}
      <div className="sidebar-section">
        <label className="sidebar-label">Sort by</label>
        <select
          className="input w-full text-xs"
          value={filters.sort}
          onChange={e => onFilterChange('sort', e.target.value)}
        >
          {SORT_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Date range */}
      <div className="sidebar-section">
        <label className="sidebar-label">Date scraped</label>
        <select
          className="input w-full text-xs"
          value={filters.days}
          onChange={e => onFilterChange('days', e.target.value)}
        >
          {DAY_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Toggles */}
      <div className="sidebar-section">
        <label className="sidebar-label">Quick filters</label>
        <div className="space-y-2">
          <Toggle
            checked={filters.c2c_only}
            onChange={v => onFilterChange('c2c_only', v)}
            label="C2C / 1099 only"
            color="amber"
          />
          <Toggle
            checked={filters.vendor_only}
            onChange={v => onFilterChange('vendor_only', v)}
            label="Vendor / staffing only"
            color="violet"
          />
        </div>
      </div>

      {/* Category */}
      {stats?.all_categories?.length > 0 && (
        <div className="sidebar-section">
          <label className="sidebar-label">Role category</label>
          <div className="space-y-0.5">
            <CategoryItem
              label="All categories"
              count={stats.total_jobs}
              selected={!filters.category}
              onClick={() => onFilterChange('category', '')}
            />
            {stats.all_categories.map(cat => (
              <CategoryItem
                key={cat}
                label={cat}
                count={stats.by_category?.[cat] ?? 0}
                selected={filters.category === cat}
                onClick={() => onFilterChange('category', filters.category === cat ? '' : cat)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Source */}
      {stats?.all_sources?.length > 0 && (
        <div className="sidebar-section">
          <label className="sidebar-label">Source board</label>
          <div className="space-y-0.5">
            <CategoryItem
              label="All sources"
              count={stats.total_jobs}
              selected={!filters.source}
              onClick={() => onFilterChange('source', '')}
            />
            {stats.all_sources.map(src => (
              <CategoryItem
                key={src}
                label={src}
                count={stats.by_source?.[src] ?? 0}
                selected={filters.source === src}
                onClick={() => onFilterChange('source', filters.source === src ? '' : src)}
              />
            ))}
          </div>
        </div>
      )}
    </aside>
  )
}

function Toggle({ checked, onChange, label, color }) {
  const colors = {
    amber:  'checked:bg-amber-500',
    violet: 'checked:bg-violet-500',
    blue:   'checked:bg-blue-500',
  }
  return (
    <label className="flex items-center gap-2.5 cursor-pointer group">
      <div
        className={`relative w-8 h-4 rounded-full transition-colors duration-200 border
          ${checked
            ? `bg-${color}-500/30 border-${color}-500/60`
            : 'bg-slate-700 border-slate-600'}`}
        onClick={() => onChange(!checked)}
      >
        <div className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full transition-all duration-200
          ${checked ? `translate-x-4 bg-${color}-400` : 'translate-x-0 bg-slate-400'}`}
        />
      </div>
      <span className={`text-xs transition-colors ${checked ? 'text-slate-200' : 'text-slate-400 group-hover:text-slate-300'}`}>
        {label}
      </span>
    </label>
  )
}

function CategoryItem({ label, count, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-2 py-1.5 rounded-md text-xs transition-all
        ${selected
          ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
          : 'text-slate-400 hover:bg-slate-700/50 hover:text-slate-200 border border-transparent'}`}
    >
      <span className="truncate text-left">{label}</span>
      <span className={`ml-1 text-[10px] tabular-nums shrink-0 ${selected ? 'text-blue-400' : 'text-slate-600'}`}>
        {count}
      </span>
    </button>
  )
}
