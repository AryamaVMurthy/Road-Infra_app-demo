import React, { useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Camera, X, Upload, WifiOff, Loader2 } from 'lucide-react'
import { cn } from '../../../utils/utils'

/**
 * ResolveTaskModal - Modal for submitting task resolution
 * 
 * Features:
 * - Photo capture/upload
 * - Offline mode indication
 * - Photo preview with remove option
 * - Submit/Save for sync actions
 * 
 * @param {Object} task - Task being resolved
 * @param {File} photo - Selected photo file
 * @param {Function} onPhotoChange - Photo change callback
 * @param {Function} onSubmit - Submit callback
 * @param {Function} onCancel - Cancel callback
 * @param {boolean} isOnline - Online status
 * @param {boolean} isResolving - Whether submission is in progress
 */
export const ResolveTaskModal = ({ 
  task, 
  photo, 
  onPhotoChange, 
  onSubmit, 
  onCancel,
  isOnline,
  isResolving 
}) => {
  const fileInputRef = useRef(null)

  if (!task) return null

  const handlePhotoCapture = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      onPhotoChange(file)
    }
  }

  const photoPreviewUrl = photo ? URL.createObjectURL(photo) : null

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
          <div className="flex items-center justify-between mb-6 sm:mb-8">
            <div className="flex items-center gap-4 sm:gap-6">
              <div className="w-12 h-12 sm:w-16 sm:h-16 bg-emerald-50 rounded-2xl flex items-center justify-center text-emerald-600 shadow-inner flex-shrink-0">
                <Camera size={24} className="sm:size-32" />
              </div>
              <div className="min-w-0">
                <h3 className="text-xl sm:text-2xl font-black text-slate-900">Resolve Task</h3>
                <p className="text-xs sm:text-sm font-bold text-slate-400 truncate">
                  {task.category_name}
                </p>
              </div>
            </div>
            <button 
              onClick={onCancel}
              className="w-8 h-8 sm:w-10 sm:h-10 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400 hover:bg-slate-200 flex-shrink-0"
            >
              <X size={18} />
            </button>
          </div>

          {/* Offline Warning */}
          {!isOnline && (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-3 sm:p-4 mb-4 sm:mb-6 flex items-center gap-3">
              <WifiOff size={18} className="text-amber-600 flex-shrink-0" />
              <p className="text-xs sm:text-sm font-bold text-amber-700">
                Offline mode - resolution will sync automatically
              </p>
            </div>
          )}

          {/* Photo Input */}
          <div className="space-y-4 sm:space-y-6">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handlePhotoCapture}
              className="hidden"
            />
            
            {photoPreviewUrl ? (
              <div className="relative">
                <img 
                  src={photoPreviewUrl} 
                  alt="Resolution proof" 
                  className="w-full h-48 sm:h-64 object-cover rounded-2xl border-4 border-emerald-200"
                />
                <button 
                  onClick={() => onPhotoChange(null)}
                  className="absolute top-3 right-3 w-8 h-8 bg-white/90 rounded-full flex items-center justify-center text-slate-500 hover:bg-red-50 hover:text-red-500 transition-all"
                >
                  <X size={16} />
                </button>
              </div>
            ) : (
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="w-full h-48 sm:h-64 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center gap-3 text-slate-400 hover:border-emerald-400 hover:text-emerald-500 transition-all"
              >
                <Camera size={40} className="sm:size-48" />
                <span className="font-bold text-xs sm:text-sm">Tap to capture resolution photo</span>
              </button>
            )}

            {/* Submit Button */}
            <button 
              onClick={onSubmit}
              disabled={!photo || isResolving}
              className={cn(
                "w-full py-4 sm:py-5 rounded-[1.5rem] font-black shadow-xl transition-all flex items-center justify-center gap-2 sm:gap-3 active:scale-95 text-sm sm:text-base",
                photo && !isResolving
                  ? "bg-emerald-600 text-white shadow-emerald-200 hover:bg-emerald-700"
                  : "bg-slate-100 text-slate-300 cursor-not-allowed shadow-none"
              )}
            >
              {isResolving ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  {isOnline ? 'Submitting...' : 'Saving offline...'}
                </>
              ) : (
                <>
                  <Upload size={18} />
                  {isOnline ? 'Submit Resolution' : 'Save for Sync'}
                </>
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default ResolveTaskModal
