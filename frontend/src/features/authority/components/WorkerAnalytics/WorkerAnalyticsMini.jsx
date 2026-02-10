import { motion } from 'framer-motion'
import { BarChart3, TrendingUp, Users, CheckCircle } from 'lucide-react'
import { cn } from '../../../../utils/utils'

/**
 * WorkerAnalyticsMini - Compact workforce overview for Authority Dashboard
 */
export const WorkerAnalyticsMini = ({ analytics }) => {
    if (!analytics) return null;
    const { summary } = analytics;

    return (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <MiniStat 
                label="Avg Tasks/Worker" 
                value={summary.avg_tasks_per_worker || 0} 
                icon={Users} 
                color="text-blue-600" 
                bgColor="bg-blue-50" 
            />
            <MiniStat 
                label="Total Active" 
                value={summary.total_active_tasks || 0} 
                icon={BarChart3} 
                color="text-amber-600" 
                bgColor="bg-amber-50" 
            />
            <MiniStat 
                label="Compliance Rate" 
                value={`${(summary.total_resolved / (summary.total_active_tasks + summary.total_resolved || 1) * 100).toFixed(1)}%`}
                icon={TrendingUp} 
                color="text-emerald-600" 
                bgColor="bg-emerald-50" 
            />
            <MiniStat 
                label="Total Resolved" 
                value={summary.total_resolved || 0} 
                icon={CheckCircle} 
                color="text-purple-600" 
                bgColor="bg-purple-50" 
            />
        </div>
    )
}

const MiniStat = ({ label, value, icon: Icon, color, bgColor }) => (
    <motion.div 
        whileHover={{ y: -2 }}
        className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/40 flex items-center gap-5"
    >
        <div className={cn("w-12 h-12 rounded-2xl flex items-center justify-center shadow-inner", bgColor, color)}>
            <Icon size={22} />
        </div>
        <div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.15em] mb-0.5">{label}</p>
            <p className="text-2xl font-black text-slate-900 leading-none">{value}</p>
        </div>
    </motion.div>
)

export default WorkerAnalyticsMini
