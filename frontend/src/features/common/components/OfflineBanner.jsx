import { motion } from 'framer-motion'
import { WifiOff } from 'lucide-react'

/**
 * OfflineBanner - Shows offline status and pending sync count
 * 
 * @param {boolean} isOnline - Current online status
 * @param {number} pendingCount - Number of items pending sync
 */
export const OfflineBanner = ({ isOnline, pendingCount }) => {
  if (isOnline) return null

  return (
    <motion.div 
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      className="bg-amber-500 text-white px-4 py-3 flex items-center justify-center gap-2 text-sm font-bold"
    >
      <WifiOff size={16} />
      You&apos;re offline. Resolutions will sync when connected.
      {pendingCount > 0 && (
        <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs">
          {pendingCount} pending
        </span>
      )}
    </motion.div>
  )
}

export default OfflineBanner
