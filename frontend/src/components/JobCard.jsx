import { MapPin, DollarSign, ExternalLink, Building2, Calendar, CheckCircle2, Send } from 'lucide-react'
import { formatDistanceToNow, parseISO, format } from 'date-fns'

const CATEGORY_COLORS = {
  // AI/ML domain
  'Agentic AI Engineer':               'bg-purple-100 text-purple-700 border-purple-200',
  'AI / ML Engineer':                  'bg-blue-100 text-blue-700 border-blue-200',
  'Generative AI / GenAI Engineer':    'bg-pink-100 text-pink-700 border-pink-200',
  'LLM Engineer':                      'bg-cyan-100 text-cyan-700 border-cyan-200',
  'Prompt Engineer':                   'bg-orange-100 text-orange-700 border-orange-200',
  'Data Scientist':                    'bg-emerald-100 text-emerald-700 border-emerald-200',
  'Data Analyst':                      'bg-teal-100 text-teal-700 border-teal-200',
  'GCP / Google Cloud Data Engineer':  'bg-yellow-100 text-yellow-700 border-yellow-200',
  'Azure AI / Foundry Developer':      'bg-sky-100 text-sky-700 border-sky-200',
  'Claude / Anthropic Developer':      'bg-rose-100 text-rose-700 border-rose-200',
  'Python Developer (AI/ML)':          'bg-indigo-100 text-indigo-700 border-indigo-200',
  'MLOps / LLMOps Engineer':           'bg-amber-100 text-amber-700 border-amber-200',
  'NLP Engineer':                      'bg-lime-100 text-lime-700 border-lime-200',
  'AI / ML Architect':                 'bg-violet-100 text-violet-700 border-violet-200',
  'RAG / LangChain / Vector DB Developer': 'bg-fuchsia-100 text-fuchsia-700 border-fuchsia-200',
  'Copilot Developer':                 'bg-blue-100 text-blue-600 border-blue-200',
  'Deep Learning / Computer Vision Engineer': 'bg-red-100 text-red-700 border-red-200',
  'Data Engineer (AI / Cloud)':        'bg-green-100 text-green-700 border-green-200',
  'AI-Related (Semantic Match)':       'bg-gray-100 text-gray-600 border-gray-200',
  // .NET domain
  '.NET Developer':                    'bg-red-100 text-red-700 border-red-200',
  'React Developer':                   'bg-cyan-100 text-cyan-700 border-cyan-200',
  // SAP domain
  'SAP TM':                            'bg-blue-100 text-blue-700 border-blue-200',
}

const SOURCE_COLORS = {
  'Adzuna':           'bg-orange-50 text-orange-600',
  'Dice.com':         'bg-red-50 text-red-600',
  'Remotive.com':     'bg-teal-50 text-teal-600',
  'Jobicy.com':       'bg-blue-50 text-blue-600',
  'WeWorkRemotely':   'bg-indigo-50 text-indigo-600',
  'Himalayas.app':    'bg-violet-50 text-violet-600',
  'WorkingNomads':    'bg-cyan-50 text-cyan-600',
  'Arbeitnow':        'bg-cyan-50 text-cyan-500',
  'The Muse':         'bg-pink-50 text-pink-600',
  "HN Who's Hiring":  'bg-rose-50 text-rose-600',
  'LinkedIn':         'bg-blue-50 text-blue-600',
  'Indeed':           'bg-sky-50 text-sky-600',
  'ZipRecruiter':     'bg-amber-50 text-amber-600',
  'Glassdoor':        'bg-emerald-50 text-emerald-600',
  'Monster':          'bg-purple-50 text-purple-600',
}

function fmtDate(iso) {
  if (!iso) return null
  try { return format(parseISO(iso), 'MMM d, yyyy') }
  catch { return iso.slice(0, 10) }
}

export default function JobCard({ job, applied, onToggleApply }) {
  const catColor  = CATEGORY_COLORS[job.role_category] ?? 'bg-gray-100 text-gray-600 border-gray-200'
  const srcColor  = SOURCE_COLORS[job.source] ?? 'bg-gray-50 text-gray-500'
  const scoreWide = Math.round((job.semantic_score ?? 0) * 100)

  const handleApply = () => {
    if (!applied) window.open(job.url, '_blank', 'noopener,noreferrer')
    onToggleApply(job, applied)
  }

  return (
    <article className={`card p-4 flex flex-col gap-3 ${applied ? 'border-green-300 bg-green-50/30' : ''}`}>
      {/* Top row: category + source */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <span className={`badge border text-[10px] leading-tight ${catColor}`}>
          {job.role_category}
        </span>
        <span className={`badge text-[10px] leading-tight ${srcColor}`}>
          {job.source}
        </span>
      </div>

      {/* Title */}
      <div>
        <a href={job.url} target="_blank" rel="noopener noreferrer" className="group inline-flex items-start gap-1.5">
          <h3 className="text-sm font-semibold text-gray-900 group-hover:text-red-600 transition-colors leading-snug">
            {job.title || 'Untitled position'}
          </h3>
          <ExternalLink size={11} className="text-gray-400 group-hover:text-red-500 shrink-0 mt-1 transition-colors" />
        </a>
        {job.company && (
          <div className="flex items-center gap-1 mt-0.5 text-xs text-gray-500">
            <Building2 size={11} className="shrink-0" />
            <span className="truncate">{job.company}</span>
            {job.is_vendor && (
              <span className="badge bg-violet-100 text-violet-600 border border-violet-200 text-[9px] ml-1">Staffing</span>
            )}
          </div>
        )}
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
        {job.location && (
          <span className="flex items-center gap-1"><MapPin size={11} className="shrink-0" />{job.location}</span>
        )}
        {job.salary && (
          <span className="flex items-center gap-1 text-emerald-600 font-medium">
            <span className="shrink-0">$</span>{job.salary}
          </span>
        )}
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5">
        {job.is_c2c && (
          <span className="badge bg-amber-100 text-amber-700 border border-amber-200 text-[10px]">C2C / 1099</span>
        )}
        {scoreWide > 0 && (
          <span className="badge bg-gray-100 text-gray-500 border border-gray-200 text-[10px] font-mono">
            AI {scoreWide}%
          </span>
        )}
      </div>

      {/* Score bar */}
      {scoreWide > 0 && (
        <div className="w-full bg-gray-100 rounded-full h-[3px]">
          <div className="score-bar h-full rounded-full" style={{ width: `${Math.min(scoreWide, 100)}%` }} />
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-gray-100 gap-2">
        <span className="flex items-center gap-1 text-[10px] text-gray-400">
          <Calendar size={10} />
          {job.posted_date ? `Posted ${fmtDate(job.posted_date)}` : 'Date unknown'}
        </span>
        <button
          onClick={handleApply}
          className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-all shrink-0
            ${applied
              ? 'bg-green-100 text-green-700 border-green-200 cursor-default'
              : 'bg-red-600 text-white border-red-600 hover:bg-red-500'
            }`}
        >
          {applied
            ? <><CheckCircle2 size={11} /> Applied</>
            : <><Send size={11} /> Apply</>
          }
        </button>
      </div>
    </article>
  )
}
