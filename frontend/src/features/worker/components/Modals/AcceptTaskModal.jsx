import { useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Calendar, X } from 'lucide-react'
import { cn } from '../../../../utils/utils'

export const AcceptTaskModal = ({ task, eta, onEtaChange, onConfirm, onCancel }) => {
  const { minDate, maxDate } = useMemo(() => {
    const today = new Date()
    return {
      minDate: today.toISOString().split('T')[0],
      maxDate: new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0],
    }
  }, [])

  if (!task) return null

  const quickDates = [
    { label: 'Tomorrow', days: 1 },
    { label: '3 Days', days: 3 },
    { label: '1 Week', days: 7 },
  ]

  const setQuickDate = (days) => {
    const date = new Date()
    date.setDate(date.getDate() + days)
    onEtaChange(date.toISOString().split('T')[0])
  }

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }} 
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-[2000] flex items-end sm:items-center justify-center p-4 sm:p-6"
      >
        <motion.div 
          initial={{ y: 100, opacity: 0 }} 
          animate={{ y: 0, opacity: 1 }} 
          exit={{ y: 100, opacity: 0 }} 
          className="bg-white w-full max-w-md rounded-[2.5rem] sm:rounded-[3rem] p-6 sm:p-10 shadow-2xl border border-slate-100"
        >
          <div className="flex items-center gap-4 sm:gap-6 mb-6 sm:mb-10">
            <div className="w-12 h-12 sm:w-16 sm:h-16 bg-blue-50 rounded-2xl flex items-center justify-center text-primary shadow-inner flex-shrink-0">
              <Calendar size={24} className="sm:size-32" />
            </div>
            <div className="min-w-0">
              <h3 className="text-xl sm:text-2xl font-black text-slate-900">Task Acceptance</h3>
              <p className="text-xs sm:text-sm font-bold text-slate-400 uppercase tracking-widest truncate">
                ID: {task.id.slice(0,8)} • {task.category_name}
              </p>
            </div>
            <button 
              onClick={onCancel}
              className="ml-auto w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center text-slate-400 hover:text-slate-600 flex-shrink-0"
            >
              <X size={20} />
            </button>
          </div>

          <div className="space-y-6 sm:space-y-10">
            <div className="space-y-3 sm:space-y-4">
              <label className="text-[10px] sm:text-xs font-black text-slate-400 uppercase tracking-[0.2em] ml-1">
                Expected Completion Date
              </label>
              
              <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-4">
                {quickDates.map(({ label, days }) => (
                  <button 
                    key={label} 
                    onClick={() => setQuickDate(days)}
                    className={cn(
                      "py-3 sm:py-4 rounded-xl sm:rounded-2xl font-black text-xs sm:text-sm border-2 transition-all active:scale-95",
                      eta === new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
                        ? "bg-primary border-primary text-white shadow-xl shadow-primary/20" 
                        : "bg-slate-50 border-transparent text-slate-500 hover:bg-slate-100"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <input
                type="date"
                value={eta}
                onChange={(e) => onEtaChange(e.target.value)}
                min={minDate}
                max={maxDate}
                className="w-full py-4 px-6 rounded-2xl border-2 border-slate-100 text-slate-900 font-bold text-center focus:outline-none focus:border-primary transition-all"
              />
              
              {eta && (
                <p className="text-center text-sm text-slate-500 font-medium">
                  Target: {new Date(eta).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
              )}
            </div>

            <div className="flex gap-3 sm:gap-4">
              <button 
                onClick={onCancel}
                className="flex-1 py-4 sm:py-5 bg-slate-100 text-slate-400 rounded-[1.5rem] font-bold hover:bg-slate-200 hover:text-slate-900 transition-all text-sm sm:text-base"
              >
                Dismiss
              </button>
              <button 
                onClick={onConfirm}
                disabled={!eta}
                className="flex-[2] py-4 sm:py-5 bg-primary text-white rounded-[1.5rem] font-black shadow-xl shadow-primary/20 disabled:bg-slate-100 disabled:text-slate-300 disabled:shadow-none transition-all active:scale-95 text-sm sm:text-base"
              >
                Confirm & Accept
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default AcceptTaskModal
