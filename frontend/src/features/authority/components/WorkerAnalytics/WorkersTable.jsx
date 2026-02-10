import React from 'react'
import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'
import { cn } from '../../../../utils/utils'

export const WorkersTable = ({ workers, analytics, onActivate, onDeactivate }) => {
  if (!workers || workers.length === 0) {
    return (
      <div className="bg-white rounded-[3rem] p-12 text-center border border-slate-100 shadow-xl">
        <p className="text-slate-400 font-bold">No workers found</p>
      </div>
    )
  }

  return (
    <motion.div 
      initial={{ opacity: 0 }} 
      animate={{ opacity: 1 }} 
      className="bg-white rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/40 overflow-hidden"
    >
      <div className="p-6 sm:p-8 border-b bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h3 className="text-lg sm:text-xl font-black text-slate-900">Active Field Force</h3>
        <div className="text-sm text-slate-500">
          {workers.length} workers • {workers.reduce((sum, w) => sum + w.active_task_count, 0)} active tasks
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="bg-slate-50 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
            <tr>
              <th className="px-4 sm:px-8 py-4 sm:py-6">Member</th>
              <th className="px-4 sm:px-8 py-4 sm:py-6">Status</th>
              <th className="px-4 sm:px-8 py-4 sm:py-6">Active Tasks</th>
               <th className="px-4 sm:px-8 py-4 sm:py-6">Resolved</th>
              <th className="px-4 sm:px-8 py-4 sm:py-6">This Week</th>
              <th className="px-4 sm:px-8 py-4 sm:py-6">Performance</th>
              <th className="px-4 sm:px-8 py-4 sm:py-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {workers.map((worker) => (
              <WorkerRow 
                key={worker.id} 
                worker={worker}
                workerAnalytics={analytics?.workers?.find(w => w.worker_id === worker.id)}
                onActivate={onActivate}
                onDeactivate={onDeactivate}
              />
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  )
}

const WorkerRow = ({ worker, workerAnalytics, onActivate, onDeactivate }) => {
  const statusColors = {
    ACTIVE: "bg-emerald-50 text-emerald-600",
    INACTIVE: "bg-slate-100 text-slate-500"
  }

  const getTaskCountColor = (count) => {
    if (count === 0) return "text-slate-300"
    if (count <= 2) return "text-blue-600"
    return "text-amber-600"
  }

  return (
    <tr className="hover:bg-slate-50/50 transition-colors">
      <td className="px-4 sm:px-8 py-4 sm:py-6">
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="w-8 h-8 sm:w-10 sm:h-10 bg-slate-100 rounded-xl flex items-center justify-center text-primary font-black text-sm sm:text-base shadow-sm flex-shrink-0">
            {worker.full_name?.[0] || 'W'}
          </div>
          <div className="min-w-0">
            <p className="font-black text-slate-900 text-sm sm:text-base truncate">
              {worker.full_name || 'Unknown'}
            </p>
            <p className="text-[10px] font-bold text-slate-400 uppercase truncate">
              {worker.email}
            </p>
          </div>
        </div>
      </td>

      <td className="px-4 sm:px-8 py-4 sm:py-6">
        <span className={cn(
          "px-2 sm:px-3 py-1 rounded-full text-[9px] sm:text-[10px] font-black uppercase tracking-wider",
          statusColors[worker.status] || statusColors.INACTIVE
        )}>
          {worker.status}
        </span>
      </td>

      <td className="px-4 sm:px-8 py-4 sm:py-6">
        <div className="flex items-center gap-2">
          <span className={cn(
            "text-base sm:text-lg font-black",
            getTaskCountColor(worker.active_task_count)
          )}>
            {worker.active_task_count}
          </span>
          <span className="text-xs text-slate-400">tasks</span>
        </div>
      </td>

      <td className="px-4 sm:px-8 py-4 sm:py-6">
        <span className="text-base sm:text-lg font-black text-emerald-600">
          {worker.resolved_count}
        </span>
      </td>

      <td className="px-4 sm:px-8 py-4 sm:py-6">
        <span className="text-base sm:text-lg font-black text-purple-600">
          {workerAnalytics?.tasks_this_week || 0}
        </span>
      </td>

      <td className="px-4 sm:px-8 py-4 sm:py-6">
        {workerAnalytics?.avg_resolution_hours ? (
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-amber-500 flex-shrink-0" />
            <span className="text-sm font-bold text-slate-600">
              {workerAnalytics.avg_resolution_hours}h avg
            </span>
          </div>
        ) : (
          <span className="text-xs text-slate-400">No data</span>
        )}
      </td>

      <td className="px-4 sm:px-8 py-4 sm:py-6 text-right flex gap-2 justify-end">
        {worker.status === 'ACTIVE' ? (
          <button 
            onClick={() => onDeactivate?.(worker.id)}
            className="text-[10px] font-black uppercase tracking-wider text-rose-500 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-lg transition-all"
          >
            Deactivate
          </button>
        ) : (
          <button
            onClick={() => onActivate?.(worker.id)}
            className="text-[10px] font-black uppercase tracking-wider text-emerald-500 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition-all"
          >
            Activate
          </button>
        )}
      </td>
    </tr>
  )
}

export default WorkersTable
