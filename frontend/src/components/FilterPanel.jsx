import { X, SlidersHorizontal } from 'lucide-react'

const SORT_OPTIONS = [
  { value: 'newest',  label: 'Scraped: Newest' },
  { value: 'posted',  label: 'Posted: Newest'  },
  { value: 'score',   label: 'AI Score'        },
  { value: 'oldest',  label: 'Scraped: Oldest' },
]

const DAY_OPTIONS = [
  { value: '',   label: 'All time'    },
  { value: '1',  label: 'Today'       },
  { value: '3',  label: 'Last 3 days' },
  { value: '7',  label: 'Last 7 days' },
  { value: '14', label: 'Last 14 days'},
]

const DOTNET_CATEGORIES = ['.NET Developer', 'React Developer']
const SAP_CATEGORIES    = ['SAP TM']
const AIML_EXCLUDED     = [...DOTNET_CATEGORIES, ...SAP_CATEGORIES]

function filterCategoriesForDomain(allCategories, domain) {
  if (domain === 'DOTNET') return allCategories.filter(c => DOTNET_CATEGORIES.includes(c))
  if (domain === 'SAP')    return allCategories.filter(c => SAP_CATEGORIES.includes(c))
  return allCategories.filter(c => !AIML_EXCLUDED.includes(c))
}

export default function FilterPanel({ filters, onFilterChange, stats, onReset, domain }) {
  const activeCount = [
    filters.category,
    filters.source,
    filters.c2c_only,
    filters.vendor_only,
    filters.remote_only,
    filters.days,
  ].filter(Boolean).length

  const visibleCategories = filterCategoriesForDomain(stats?.all_categories ?? [], domain)

  return (
    <aside className="w-56 shrink-0 sticky top-[60px] h-[calc(100vh-60px)] overflow-y-auto py-4 pr-1">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <SlidersHorizontal size={14} className="text-red-500" />
          Filters
          {activeCount > 0 && (
            <span className="badge bg-red-100 text-red-600 border border-red-200">
              {activeCount}
            </span>
          )}
        </div>
        {activeCount > 0 && (
          <button onClick={onReset} className="text-xs text-gray-400 hover:text-red-500 flex items-center gap-1 transition-colors">
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
          <Toggle
            checked={filters.remote_only}
            onChange={v => onFilterChange('remote_only', v)}
            label="Remote only"
            color="blue"
          />
        </div>
      </div>

      {/* Category */}
      {visibleCategories.length > 0 && (
        <div className="sidebar-section">
          <label className="sidebar-label">Role category</label>
          <div className="space-y-0.5">
            <CategoryItem
              label="All categories"
              count={stats?.total_jobs ?? 0}
              selected={!filters.category}
              onClick={() => onFilterChange('category', '')}
            />
            {visibleCategories.map(cat => (
              <CategoryItem
                key={cat}
                label={cat}
                count={stats?.by_category?.[cat] ?? 0}
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
              count={stats?.total_jobs ?? 0}
              selected={!filters.source}
              onClick={() => onFilterChange('source', '')}
            />
            {stats.all_sources.map(src => (
              <CategoryItem
                key={src}
                label={src}
                count={stats?.by_source?.[src] ?? 0}
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
  const trackColors = {
    amber:  checked ? 'bg-amber-100 border-amber-300' : 'bg-gray-100 border-gray-200',
    violet: checked ? 'bg-violet-100 border-violet-300' : 'bg-gray-100 border-gray-200',
    blue:   checked ? 'bg-blue-100 border-blue-300' : 'bg-gray-100 border-gray-200',
  }
  const dotColors = {
    amber:  checked ? 'bg-amber-500' : 'bg-gray-400',
    violet: checked ? 'bg-violet-500' : 'bg-gray-400',
    blue:   checked ? 'bg-blue-500' : 'bg-gray-400',
  }
  return (
    <label className="flex items-center gap-2.5 cursor-pointer group">
      <div
        className={`relative w-8 h-4 rounded-full transition-colors duration-200 border ${trackColors[color]}`}
        onClick={() => onChange(!checked)}
      >
        <div className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full transition-all duration-200 ${dotColors[color]} ${checked ? 'translate-x-4' : 'translate-x-0'}`} />
      </div>
      <span className={`text-xs transition-colors ${checked ? 'text-gray-800' : 'text-gray-500 group-hover:text-gray-700'}`}>
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
          ? 'bg-red-50 text-red-700 border border-red-200'
          : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800 border border-transparent'}`}
    >
      <span className="truncate text-left">{label}</span>
      <span className={`ml-1 text-[10px] tabular-nums shrink-0 ${selected ? 'text-red-500' : 'text-gray-400'}`}>
        {count}
      </span>
    </button>
  )
}
