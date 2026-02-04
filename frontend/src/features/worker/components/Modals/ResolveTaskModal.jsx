import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Camera, X, Upload, WifiOff, Loader2, Calendar, ArrowRight, ArrowLeft } from 'lucide-react'
import { cn } from '../../../../utils/utils'

export const ResolveTaskModal = ({ 
  task, 
  photo, 
  onPhotoChange, 
  onSubmit, 
  onCancel,
  isOnline,
  isResolving,
  etaDate,
  onEtaDateChange
}) => {
  const fileInputRef = React.useRef(null)
  const [step, setStep] = useState(1)

  if (!task) return null

  const handlePhotoCapture = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      onPhotoChange(file)
    }
  }

  const photoPreviewUrl = photo ? URL.createObjectURL(photo) : null

  const today = new Date()
  const minDate = today.toISOString().split('T')[0]
  const maxDate = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]

  const quickDates = [
    { label: 'Tomorrow', days: 1 },
    { label: '3 Days', days: 3 },
    { label: '1 Week', days: 7 },
  ]

  const setQuickDate = (days) => {
    const date = new Date()
    date.setDate(date.getDate() + days)
    onEtaDateChange(date.toISOString().split('T')[0])
  }

  const handleNext = () => {
    if (etaDate) {
      setStep(2)
    }
  }

  const handleBack = () => {
    setStep(1)
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
          <div className="flex items-center justify-between mb-6 sm:mb-8">
            <div className="flex items-center gap-4 sm:gap-6">
              <div className={cn(
                "w-12 h-12 sm:w-16 sm:h-16 rounded-2xl flex items-center justify-center shadow-inner flex-shrink-0",
                step === 1 ? "bg-blue-50 text-blue-600" : "bg-emerald-50 text-emerald-600"
              )}>
                {step === 1 ? <Calendar size={24} /> : <Camera size={24} />}
              </div>
              <div className="min-w-0">
                <h3 className="text-xl sm:text-2xl font-black text-slate-900">
                  {step === 1 ? 'Set Completion Date' : 'Upload Proof'}
                </h3>
                <p className="text-xs sm:text-sm font-bold text-slate-400 truncate">
                  Step {step} of 2 • {task.category_name}
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

          {!isOnline && (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-3 sm:p-4 mb-4 sm:mb-6 flex items-center gap-3">
              <WifiOff size={18} className="text-amber-600 flex-shrink-0" />
              <p className="text-xs sm:text-sm font-bold text-amber-700">
                Offline mode - resolution will sync automatically
              </p>
            </div>
          )}

          <AnimatePresence mode="wait">
            {step === 1 ? (
              <motion.div 
                key="step1"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4 sm:space-y-6"
              >
                <div className="space-y-3 sm:space-y-4">
                  <label className="text-[10px] sm:text-xs font-black text-slate-400 uppercase tracking-[0.2em] ml-1">
                    Expected Completion Date
                  </label>
                  
                  <div className="grid grid-cols-3 gap-2 sm:gap-3">
                    {quickDates.map(({ label, days }) => (
                      <button 
                        key={label} 
                        onClick={() => setQuickDate(days)}
                        className={cn(
                          "py-3 sm:py-4 rounded-xl sm:rounded-2xl font-black text-xs sm:text-sm border-2 transition-all active:scale-95",
                          etaDate === new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
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
                    value={etaDate || ''}
                    onChange={(e) => onEtaDateChange(e.target.value)}
                    min={minDate}
                    max={maxDate}
                    className="w-full py-4 px-6 rounded-2xl border-2 border-slate-100 text-slate-900 font-bold text-center focus:outline-none focus:border-primary transition-all"
                  />
                  
                  {etaDate && (
                    <p className="text-center text-sm text-slate-500 font-medium">
                      Target: {new Date(etaDate).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                    </p>
                  )}
                </div>

                <button 
                  onClick={handleNext}
                  disabled={!etaDate}
                  className={cn(
                    "w-full py-4 sm:py-5 rounded-[1.5rem] font-black shadow-xl transition-all flex items-center justify-center gap-2 active:scale-95",
                    etaDate
                      ? "bg-primary text-white shadow-primary/20 hover:bg-primary/90"
                      : "bg-slate-100 text-slate-300 cursor-not-allowed shadow-none"
                  )}
                >
                  Next: Upload Photo
                  <ArrowRight size={18} />
                </button>
              </motion.div>
            ) : (
              <motion.div 
                key="step2"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-4 sm:space-y-6"
              >
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
                    <Camera size={40} />
                    <span className="font-bold text-xs sm:text-sm">Tap to capture resolution photo</span>
                  </button>
                )}

                <div className="flex gap-3">
                  <button 
                    onClick={handleBack}
                    className="flex-1 py-4 sm:py-5 bg-slate-100 text-slate-500 rounded-[1.5rem] font-bold hover:bg-slate-200 transition-all flex items-center justify-center gap-2"
                  >
                    <ArrowLeft size={18} />
                    Back
                  </button>
                  <button 
                    onClick={onSubmit}
                    disabled={!photo || isResolving}
                    className={cn(
                      "flex-[2] py-4 sm:py-5 rounded-[1.5rem] font-black shadow-xl transition-all flex items-center justify-center gap-2 sm:gap-3 active:scale-95 text-sm sm:text-base",
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
                        {isOnline ? 'Submit' : 'Save for Sync'}
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default ResolveTaskModal
