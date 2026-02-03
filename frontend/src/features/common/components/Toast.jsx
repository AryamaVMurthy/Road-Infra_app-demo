import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../../utils/utils'
import { Check, X, CloudOff } from 'lucide-react'

/**
 * Toast - Toast notification component
 * 
 * @param {Object} toast - Toast configuration object
 * @param {string} toast.message - Message to display
 * @param {string} toast.type - Type: 'success', 'error', or 'info'
 * @param {function} onClose - Callback when toast should close
 */
export const Toast = ({ toast, onClose }) => {
  if (!toast) return null

  const iconMap = {
    success: <Check size={20} />,
    error: <X size={20} />,
    info: <CloudOff size={20} />
  }

  const classMap = {
    success: "bg-emerald-600 text-white",
    error: "bg-red-600 text-white",
    info: "bg-slate-800 text-white"
  }

  return (
    <AnimatePresence>
      {toast && (
        <motion.div 
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 50 }}
          onClick={onClose}
          className={cn(
            "fixed bottom-36 left-1/2 -translate-x-1/2 px-6 py-4 rounded-2xl font-bold shadow-2xl z-[3000] flex items-center gap-3 cursor-pointer",
            classMap[toast.type]
          )}
        >
          {iconMap[toast.type]}
          {toast.message}
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export default Toast
