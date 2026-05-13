import { Briefcase, Calendar, Building2, HandCoins, Database } from 'lucide-react'

function Stat({ icon: Icon, label, value, color = 'text-red-500', bg = 'bg-red-50' }) {
  return (
    <div className="flex items-center gap-2.5 px-4 py-2.5 bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${bg}`}>
        <Icon size={15} className={color} />
      </div>
      <div>
        <div className={`text-lg font-bold leading-none ${color}`}>{value ?? '—'}</div>
        <div className="text-[10px] text-gray-400 mt-0.5 font-medium">{label}</div>
      </div>
    </div>
  )
}

export default function StatsBar({ stats, filtered }) {
  return (
    <div className="flex flex-wrap items-center gap-2 py-3">
      <Stat icon={Briefcase}  label="Total Jobs"     value={stats?.total_jobs?.toLocaleString()} color="text-red-600"    bg="bg-red-50" />
      <Stat icon={Calendar}   label="Added Today"    value={stats?.jobs_today?.toLocaleString()} color="text-emerald-600" bg="bg-emerald-50" />
      <Stat icon={HandCoins}  label="C2C / 1099"     value={stats?.c2c_jobs?.toLocaleString()}   color="text-amber-600"  bg="bg-amber-50" />
      <Stat icon={Building2}  label="Vendor / Staff" value={stats?.vendor_jobs?.toLocaleString()} color="text-violet-600" bg="bg-violet-50" />
      <Stat icon={Database}   label="Job Boards"     value={stats?.all_sources?.length ?? 0}     color="text-blue-600"   bg="bg-blue-50" />
      {filtered !== undefined && (
        <div className="ml-auto text-xs text-gray-400 font-medium">
          Showing <span className="text-gray-700 font-semibold">{filtered.toLocaleString()}</span> results
        </div>
      )}
    </div>
  )
}
