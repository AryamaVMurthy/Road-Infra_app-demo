import { cn } from '../../../utils/utils'
import { TrendingUp } from 'lucide-react'

/**
 * StatCard - Statistics display card for dashboard
 * 
 * @param {string} label - Metric label
 * @param {number} value - Metric value
 * @param {React.ComponentType} icon - Lucide icon component
 * @param {string} colorClass - Tailwind color classes for icon background
 * @param {string} trend - Optional trend indicator (e.g., "+12%")
 */
export const StatCard = ({ label, value, icon: Icon, colorClass, trend }) => (
  <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/40 flex items-center gap-6">
    <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center text-white", colorClass)}>
      <Icon size={24} />
    </div>
    <div className="flex-1">
      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-3xl font-extrabold text-slate-900">{value}</p>
    </div>
    {trend && (
      <div className="flex items-center gap-1 text-emerald-500 text-xs font-bold">
        <TrendingUp size={14} />
        {trend}
      </div>
    )}
  </div>
)

export default StatCard
