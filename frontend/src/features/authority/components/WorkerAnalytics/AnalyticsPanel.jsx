import { motion } from 'framer-motion'
import { BarChart3 } from 'lucide-react'

/**
 * WorkerAnalyticsMini - Compact workforce overview panel
 * Displays summary statistics for all workers
 * 
 * @param {Object} analytics - Analytics data object
 * @param {Array} analytics.workers - Individual worker statistics
 * @param {Object} analytics.summary - Aggregated summary stats
 */
export const WorkerAnalyticsMini = ({ analytics }) => {
  if (!analytics) return null
  
  const summary = analytics.summary || {}
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl p-5 border border-slate-100 shadow-lg shadow-slate-200/40 mb-6"
    >
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-primary/10 rounded-xl flex items-center justify-center text-primary">
            <BarChart3 size={18} />
          </div>
          <div>
            <h3 className="text-sm font-black text-slate-900">Workforce Overview</h3>
            <p className="text-[9px] text-slate-400 uppercase tracking-widest">Real-time</p>
          </div>
        </div>
        
        <div className="flex-1 flex items-center gap-4 justify-end">
          <StatBadge value={summary.total_workers || 0} label="Workers" color="emerald" />
          <StatBadge value={summary.total_active_tasks || 0} label="Active" color="amber" />
          <StatBadge value={summary.total_resolved || 0} label="Resolved" color="blue" />
          <StatBadge value={summary.avg_tasks_per_worker || 0} label="Avg/Worker" color="purple" />
        </div>
      </div>
    </motion.div>
  )
}

/**
 * StatBadge - Individual statistic display
 */
const StatBadge = ({ value, label, color }) => {
  const colorClasses = {
    emerald: "text-emerald-600",
    amber: "text-amber-600",
    blue: "text-blue-600",
    purple: "text-purple-600"
  }

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-xl">
      <p className={`text-lg font-black ${colorClasses[color]}`}>{value}</p>
      <p className="text-[9px] text-slate-400 uppercase">{label}</p>
    </div>
  )
}

export default WorkerAnalyticsMini
