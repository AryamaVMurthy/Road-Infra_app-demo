import React from 'react'
import { motion } from 'framer-motion'
import { MapPin, Navigation2, CloudOff, Camera, ArrowRight } from 'lucide-react'
import { cn } from '../../../../utils/utils'

/**
 * TaskCard - Displays a single task for workers
 * 
 * Features:
 * - Priority indicator with animation
 * - Location information
 * - Status display
 * - Action buttons based on task status
 * - Pending sync indicator
 * 
 * @param {Object} task - Task data object
 * @param {number} idx - Index for animation delay
 * @param {Function} onSelect - Select task callback (for accepting)
 * @param {Function} onResolve - Resolve task callback
 * @param {boolean} hasPendingSync - Whether this task has pending offline sync
 */
export const TaskCard = ({ task, idx, onSelect, onResolve, hasPendingSync }) => {
  const isCritical = task.priority === 'P1'
  const isAssigned = task.status === 'ASSIGNED'
  const isInProgress = task.status === 'ACCEPTED' || task.status === 'IN_PROGRESS'

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.05 }}
      className="bg-white rounded-[2.5rem] p-6 sm:p-8 border border-slate-100 shadow-[0_20px_50px_-12px_rgba(0,0,0,0.05)] relative overflow-hidden"
    >
      {/* Pending Sync Badge */}
      {hasPendingSync && (
        <div className="absolute top-3 right-3 sm:top-4 sm:right-4 flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-600 rounded-full text-xs font-bold">
          <CloudOff size={14} />
          <span className="hidden sm:inline">Pending Sync</span>
        </div>
      )}
      
      {/* Header */}
      <div className="flex justify-between items-start mb-4 sm:mb-6">
        <div className="space-y-2 sm:space-y-3 pr-16">
          {/* Priority Badge */}
          <div className={cn(
            "inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest",
            isCritical ? "bg-rose-50 text-rose-600" : "bg-blue-50 text-blue-600"
          )}>
            <div className={cn(
              "w-1.5 h-1.5 rounded-full animate-pulse",
              isCritical ? "bg-rose-600" : "bg-blue-600"
            )}></div>
            {task.priority} Priority
          </div>
          
          {/* Task Title */}
          <h3 className="text-xl sm:text-2xl font-black text-slate-900 leading-tight">
            {task.category_name}
          </h3>
          
          {/* Location */}
          <p className="flex items-center gap-2 text-sm font-bold text-slate-400">
            <MapPin size={14} className="text-primary flex-shrink-0" /> 
            <span className="truncate">{task.address || 'Location Identified'}</span>
          </p>
        </div>
        
        {/* Navigation Icon */}
        <div className="w-12 h-12 sm:w-14 sm:h-14 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-400 border border-slate-100 shadow-inner flex-shrink-0">
          <Navigation2 size={20} className="sm:size-24" />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 mb-6 sm:mb-8">
        <StatBox 
          label="Reports"
          value={task.report_count}
        />
        <StatBox 
          label="Status"
          value={task.status}
          highlight
        />
      </div>

      {/* Action Button */}
      <div className="flex gap-3 sm:gap-4">
        {isAssigned ? (
          <ActionButton
            onClick={() => onSelect(task)}
            variant="primary"
            icon={ArrowRight}
          >
            Accept Task
          </ActionButton>
        ) : isInProgress ? (
          <ActionButton
            onClick={() => onResolve(task)}
            disabled={hasPendingSync}
            variant={hasPendingSync ? "warning" : "success"}
            icon={Camera}
          >
            {hasPendingSync ? 'Awaiting Sync' : 'Resolve Task'}
          </ActionButton>
        ) : (
          <div className="flex-1 py-4 sm:py-5 bg-slate-100 text-slate-400 rounded-[1.5rem] font-black text-center text-sm sm:text-base">
            {task.status}
          </div>
        )}
      </div>
      
      {/* In Progress Indicator */}
      {task.status === 'IN_PROGRESS' && !hasPendingSync && (
        <div className="absolute top-6 right-6 sm:top-8 sm:right-8">
          <span className="flex h-2.5 w-2.5 sm:h-3 sm:w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-full w-full bg-emerald-500"></span>
          </span>
        </div>
      )}
    </motion.div>
  )
}

/**
 * StatBox - Displays a statistic
 */
const StatBox = ({ label, value, highlight = false }) => (
  <div className="bg-slate-50/50 rounded-2xl p-4 sm:p-5 border border-slate-100">
    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">
      {label}
    </p>
    <p className={cn(
      "text-xl sm:text-2xl font-black",
      highlight ? "text-primary" : "text-slate-900"
    )}>
      {value}
    </p>
  </div>
)

/**
 * ActionButton - Styled action button
 */
const ActionButton = ({ onClick, disabled, variant, icon: Icon, children }) => {
  const variants = {
    primary: "bg-primary text-white shadow-xl shadow-primary/20 hover:bg-blue-700",
    success: "bg-emerald-600 text-white shadow-emerald-200 hover:bg-emerald-700",
    warning: "bg-amber-100 text-amber-600 cursor-not-allowed"
  }

  return (
    <button 
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex-1 py-4 sm:py-5 rounded-[1.5rem] font-black shadow-xl transition-all flex items-center justify-center gap-2 sm:gap-3 active:scale-95 text-sm sm:text-base",
        variants[variant],
        disabled && "shadow-none"
      )}
    >
      <Icon size={18} className="sm:size-20" />
      {children}
    </button>
  )
}

export default TaskCard
