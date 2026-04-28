import { Briefcase, Calendar, Building2, HandCoins, Database } from 'lucide-react'

function Stat({ icon: Icon, label, value, color = 'text-blue-400' }) {
  return (
    <div className="flex items-center gap-2.5 px-4 py-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50">
      <Icon size={15} className={color} />
      <div>
        <div className={`text-lg font-bold leading-none ${color}`}>{value ?? '—'}</div>
        <div className="text-[10px] text-slate-500 mt-0.5 font-medium">{label}</div>
      </div>
    </div>
  )
}

export default function StatsBar({ stats, filtered }) {
  return (
    <div className="flex flex-wrap items-center gap-2 py-3">
      <Stat icon={Briefcase}  label="Total Jobs"     value={stats?.total_jobs?.toLocaleString()} color="text-blue-400" />
      <Stat icon={Calendar}   label="Added Today"    value={stats?.jobs_today?.toLocaleString()} color="text-emerald-400" />
      <Stat icon={HandCoins}  label="C2C / 1099"     value={stats?.c2c_jobs?.toLocaleString()}   color="text-amber-400" />
      <Stat icon={Building2}  label="Vendor / Staff" value={stats?.vendor_jobs?.toLocaleString()} color="text-violet-400" />
      <Stat icon={Database}   label="Job Boards"     value={stats?.all_sources?.length ?? 0}     color="text-cyan-400" />
      {filtered !== undefined && (
        <div className="ml-auto text-xs text-slate-500 font-medium">
          Showing <span className="text-slate-300 font-semibold">{filtered.toLocaleString()}</span> results
        </div>
      )}
    </div>
  )
}
