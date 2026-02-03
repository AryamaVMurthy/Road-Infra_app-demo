import { motion } from 'framer-motion'
import { cn } from '../../../utils/utils'
import { Clock } from 'lucide-react'

/**
 * KanbanCard - Individual issue card for kanban board
 * 
 * @param {Object} issue - Issue data object
 * @param {boolean} selected - Whether this card is selected
 * @param {function} onClick - Click handler
 * @param {function} onSelectToggle - Checkbox toggle handler (for REPORTED column)
 * @param {React.ReactNode} actions - Actions dropdown component
 * @param {boolean} showCheckbox - Whether to show selection checkbox
 */
export const KanbanCard = ({ 
  issue, 
  selected, 
  onClick, 
  onSelectToggle,
  actions,
  showCheckbox = false 
}) => {
  const priorityClasses = {
    P1: "bg-rose-50 text-rose-600",
    P2: "bg-amber-50 text-amber-600",
    P3: "bg-blue-50 text-blue-600",
    P4: "bg-slate-50 text-slate-600"
  }

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.9 }} 
      animate={{ opacity: 1, scale: 1 }}
      onClick={onClick}
      className={cn(
        "bg-white p-6 rounded-[2rem] shadow-lg shadow-slate-200/40 border-2 transition-all relative group cursor-pointer ticket-card",
        selected ? "border-primary" : "border-transparent hover:border-slate-200"
      )}
    >
      {/* Header with actions and checkbox */}
      <div className="absolute top-5 right-5 flex items-center gap-2">
        {actions}
        {showCheckbox && (
          <input 
            type="checkbox" 
            checked={selected}
            className="w-5 h-5 rounded-md border-2 border-slate-200 checked:bg-primary transition-all cursor-pointer"
            onChange={(e) => { 
              e.stopPropagation()
              onSelectToggle?.(issue.id)
            }}
          />
        )}
      </div>

      {/* Priority and ETA badges */}
      <div className="flex gap-2 mb-4 flex-wrap pr-12">
        <span className={cn(
          "text-[10px] font-black px-2 py-0.5 rounded-full",
          priorityClasses[issue.priority] || priorityClasses.P3
        )}>
          {issue.priority}
        </span>
        {issue.eta_duration && (
          <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 flex items-center gap-1">
            <Clock size={10} />
            ETA: {issue.eta_duration}
          </span>
        )}
      </div>

      {/* Issue title */}
      <h4 className="font-black text-slate-900 text-lg mb-2 leading-tight group-hover:text-primary transition-colors">
        {issue.category_name}
      </h4>

      {/* Issue description */}
      <p className="text-xs font-medium text-slate-400 line-clamp-2 mb-6">
        Issue #{issue.id.slice(0,8)} at {issue.address || 'Confirmed GPS Location'}.
      </p>

      {/* Footer with date and worker */}
      <div className="flex items-center justify-between pt-4 border-t border-slate-50">
        <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
          <Clock size={12} className="text-slate-300" />
          <span>{new Date(issue.created_at).toLocaleDateString()}</span>
        </div>
        {issue.worker_name && (
          <span className="text-[10px] font-black text-slate-500 uppercase tracking-tight truncate max-w-[80px]">
            {issue.worker_name}
          </span>
        )}
      </div>
    </motion.div>
  )
}

export default KanbanCard
