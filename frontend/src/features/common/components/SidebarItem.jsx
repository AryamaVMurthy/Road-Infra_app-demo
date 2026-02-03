import { cn } from '../../../utils/utils'

/**
 * SidebarItem - Navigation item for dashboard sidebar
 * 
 * @param {boolean} active - Whether this item is currently active
 * @param {React.ComponentType} icon - Lucide icon component
 * @param {string} label - Display label
 * @param {function} onClick - Click handler
 */
export const SidebarItem = ({ active, icon: Icon, label, onClick }) => (
  <button 
    onClick={onClick}
    className={cn(
      "w-full flex items-center gap-4 p-4 rounded-2xl font-bold transition-all group",
      active ? "bg-primary text-white shadow-lg shadow-primary/20" : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
    )}
  >
    <Icon size={22} className={cn("transition-transform group-hover:scale-110", active ? "text-white" : "text-slate-400")} />
    <span className="text-sm">{label}</span>
  </button>
)

export default SidebarItem
