import { MapPin, DollarSign, ExternalLink, Building2, Calendar, CheckCircle2, Send } from 'lucide-react'
import { formatDistanceToNow, parseISO, format } from 'date-fns'

const CATEGORY_COLORS = {
  'Agentic AI Engineer':               'bg-purple-500/20 text-purple-300 border-purple-500/40',
  'AI / ML Engineer':                  'bg-blue-500/20 text-blue-300 border-blue-500/40',
  'Generative AI / GenAI Engineer':    'bg-pink-500/20 text-pink-300 border-pink-500/40',
  'LLM Engineer':                      'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
  'Prompt Engineer':                   'bg-orange-500/20 text-orange-300 border-orange-500/40',
  'Data Scientist':                    'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
  'Data Analyst':                      'bg-teal-500/20 text-teal-300 border-teal-500/40',
  'GCP / Google Cloud Data Engineer':  'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
  'Azure AI / Foundry Developer':      'bg-sky-500/20 text-sky-300 border-sky-500/40',
  'Claude / Anthropic Developer':      'bg-rose-500/20 text-rose-300 border-rose-500/40',
  'Python Developer (AI/ML)':          'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
  'MLOps / LLMOps Engineer':           'bg-amber-500/20 text-amber-300 border-amber-500/40',
  'NLP Engineer':                      'bg-lime-500/20 text-lime-300 border-lime-500/40',
  'AI / ML Architect':                 'bg-violet-500/20 text-violet-300 border-violet-500/40',
  'RAG / LangChain / Vector DB Developer': 'bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/40',
  'Copilot Developer':                 'bg-blue-400/20 text-blue-200 border-blue-400/40',
  'Deep Learning / Computer Vision Engineer': 'bg-red-500/20 text-red-300 border-red-500/40',
  'Data Engineer (AI / Cloud)':        'bg-green-500/20 text-green-300 border-green-500/40',
  'AI-Related (Semantic Match)':       'bg-slate-500/20 text-slate-300 border-slate-500/40',
}

const SOURCE_COLORS = {
  // Scraped directly
  'Adzuna':           'bg-orange-500/10 text-orange-400',
  'Dice.com':         'bg-red-500/10 text-red-400',
  'Remotive.com':     'bg-teal-500/10 text-teal-400',
  'Jobicy.com':       'bg-blue-500/10 text-blue-400',
  'WeWorkRemotely':   'bg-indigo-500/10 text-indigo-400',
  'Himalayas.app':    'bg-violet-500/10 text-violet-400',
  'WorkingNomads':    'bg-cyan-500/10 text-cyan-400',
  'Arbeitnow':        'bg-cyan-400/10 text-cyan-300',
  'The Muse':         'bg-pink-500/10 text-pink-400',
  "HN Who's Hiring":  'bg-rose-500/10 text-rose-400',
  // Via JSearch aggregation
  'LinkedIn':         'bg-blue-600/10 text-blue-400',
  'Indeed':           'bg-sky-600/10 text-sky-300',
  'ZipRecruiter':     'bg-amber-500/10 text-amber-400',
  'Glassdoor':        'bg-emerald-500/10 text-emerald-400',
  'Monster':          'bg-purple-500/10 text-purple-400',
}

function fmtDate(iso) {
  if (!iso) return null
  try { return format(parseISO(iso), 'MMM d, yyyy') }
  catch { return iso.slice(0, 10) }
}

export default function JobCard({ job, applied, onToggleApply }) {
  const catColor  = CATEGORY_COLORS[job.role_category] ?? 'bg-slate-500/20 text-slate-300 border-slate-500/40'
  const srcColor  = SOURCE_COLORS[job.source] ?? 'bg-slate-500/10 text-slate-400'
  const scoreWide = Math.round((job.semantic_score ?? 0) * 100)

  const handleApply = () => {
    if (!applied) window.open(job.url, '_blank', 'noopener,noreferrer')
    onToggleApply(job, applied)
  }

  return (
    <article className={`card p-4 flex flex-col gap-3 animate-slide-up transition-all ${applied ? 'border-green-500/30 bg-green-950/10' : ''}`}>
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
          <h3 className="text-sm font-semibold text-slate-100 group-hover:text-blue-300 transition-colors leading-snug">
            {job.title || 'Untitled position'}
          </h3>
          <ExternalLink size={11} className="text-slate-500 group-hover:text-blue-400 shrink-0 mt-1 transition-colors" />
        </a>
        {job.company && (
          <div className="flex items-center gap-1 mt-0.5 text-xs text-slate-400">
            <Building2 size={11} className="shrink-0" />
            <span className="truncate">{job.company}</span>
            {job.is_vendor && (
              <span className="badge bg-violet-500/15 text-violet-400 border border-violet-500/30 text-[9px] ml-1">Staffing</span>
            )}
          </div>
        )}
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-400">
        {job.location && (
          <span className="flex items-center gap-1"><MapPin size={11} className="shrink-0" />{job.location}</span>
        )}
        {job.salary && (
          <span className="flex items-center gap-1 text-emerald-400 font-medium">
            <span className="shrink-0">$</span>{job.salary}
          </span>
        )}
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5">
        {job.is_c2c && (
          <span className="badge bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[10px]">C2C / 1099</span>
        )}
        {scoreWide > 0 && (
          <span className="badge bg-slate-700/50 text-slate-400 border border-slate-600/40 text-[10px] font-mono">
            AI {scoreWide}%
          </span>
        )}
      </div>

      {/* Score bar */}
      {scoreWide > 0 && (
        <div className="w-full bg-slate-700/30 rounded-full h-[3px]">
          <div className="score-bar h-full rounded-full" style={{ width: `${Math.min(scoreWide, 100)}%` }} />
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-slate-700/40 gap-2">
        <span className="flex items-center gap-1 text-[10px] text-slate-600">
          <Calendar size={10} />
          {job.posted_date ? `Posted ${fmtDate(job.posted_date)}` : 'Date unknown'}
        </span>
        <button
          onClick={handleApply}
          className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-all shrink-0
            ${applied
              ? 'bg-green-500/20 text-green-300 border-green-500/40 cursor-default'
              : 'bg-blue-500/15 text-blue-300 border-blue-500/30 hover:bg-blue-500/25'
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
