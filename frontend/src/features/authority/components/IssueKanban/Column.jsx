import { cn } from '../../../../utils/utils'

/**
 * KanbanColumn - Column container for kanban board
 * 
 * @param {string} title - Column title
 * @param {string} color - Color theme for column
 * @param {number} count - Number of items in column
 * @param {React.ReactNode} children - Card components
 */
export const KanbanColumn = ({ title, color, count, children }) => {
  const colorClasses = {
    rose: "bg-rose-500",
    blue: "bg-blue-500",
    amber: "bg-amber-500",
    emerald: "bg-emerald-500",
    slate: "bg-slate-400"
  }

  return (
    <div className="w-80 flex-shrink-0 flex flex-col gap-6">
      {/* Column header */}
      <div className="flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className={cn("w-2 h-2 rounded-full", colorClasses[color])}></div>
          <h3 className="font-black text-slate-600 text-sm tracking-widest">{title}</h3>
        </div>
        <span className="px-2 py-0.5 bg-slate-200 rounded-md text-[10px] font-black text-slate-500">
          {count}
        </span>
      </div>

      {/* Cards container */}
      <div className="flex-1 space-y-4 overflow-y-auto pr-2 custom-scrollbar">
        {children}
      </div>
    </div>
  )
}

export default KanbanColumn
