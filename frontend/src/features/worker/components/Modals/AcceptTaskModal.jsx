import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Clock, X } from 'lucide-react'
import { cn } from '../../../../utils/utils'

/**
 * AcceptTaskModal - Modal for accepting a task with ETA
 * 
 * Features:
 * - ETA selection with preset buttons
 * - Task information display
 * - Confirm/Cancel actions
 * 
 * @param {Object} task - Task being accepted
 * @param {string} eta - Current ETA value
 * @param {Function} onEtaChange - ETA change callback
 * @param {Function} onConfirm - Confirm acceptance callback
 * @param {Function} onCancel - Cancel callback
 */
export const AcceptTaskModal = ({ task, eta, onEtaChange, onConfirm, onCancel }) => {
  if (!task) return null

  const timeOptions = ['30m', '1h', '2h', '4h', '1d', '2d']

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
          {/* Header */}
          <div className="flex items-center gap-4 sm:gap-6 mb-6 sm:mb-10">
            <div className="w-12 h-12 sm:w-16 sm:h-16 bg-blue-50 rounded-2xl flex items-center justify-center text-primary shadow-inner flex-shrink-0">
              <Clock size={24} className="sm:size-32" />
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

          {/* ETA Selection */}
          <div className="space-y-6 sm:space-y-10">
            <div className="space-y-3 sm:space-y-4">
              <label className="text-[10px] sm:text-xs font-black text-slate-400 uppercase tracking-[0.2em] ml-1">
                Expected Arrival (ETA)
              </label>
              <div className="grid grid-cols-3 gap-2 sm:gap-3">
                {timeOptions.map(time => (
                  <button 
                    key={time} 
                    onClick={() => onEtaChange(time)}
                    className={cn(
                      "py-3 sm:py-4 rounded-xl sm:rounded-2xl font-black text-xs sm:text-sm border-2 transition-all active:scale-95",
                      eta === time 
                        ? "bg-primary border-primary text-white shadow-xl shadow-primary/20" 
                        : "bg-slate-50 border-transparent text-slate-500 hover:bg-slate-100"
                    )}
                  >
                    {time}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
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
