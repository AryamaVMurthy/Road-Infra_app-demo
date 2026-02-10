import React, { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Users, X, Loader2, Send, FileUp, AlertCircle } from 'lucide-react'
import { cn } from '../../../../utils/utils'
import Papa from 'papaparse'

export const OnboardWorkersModal = ({ 
  onOnboard, 
  onCancel,
  isSubmitting
}) => {
  const [emails, setEmails] = useState('')
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const handleSubmit = () => {
    const emailList = emails.split(/[,;\n\s]+/).map(e => e.trim()).filter(e => {
        return e !== '' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)
    })
    
    if (emailList.length > 0) {
      onOnboard(emailList)
    } else {
      setError("Please provide at least one valid email address.")
    }
  }

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return

    Papa.parse(file, {
      complete: (results) => {
        const extractedEmails = results.data
          .flat()
          .map(cell => String(cell).trim())
          .filter(cell => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cell))
        
        if (extractedEmails.length > 0) {
          const currentEmails = emails.split(/[,;\n\s]+/).map(e => e.trim()).filter(e => e !== '')
          const combined = Array.from(new Set([...currentEmails, ...extractedEmails]))
          setEmails(combined.join(', '))
          setError(null)
        } else {
          setError("No valid email addresses found in the CSV.")
        }
      },
      error: (err) => {
        setError("Error parsing CSV file.")
      }
    })
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
              <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center shadow-inner flex-shrink-0">
                <Users size={24} />
              </div>
              <div className="min-w-0">
                <h3 className="text-xl sm:text-2xl font-black text-slate-900">
                  Onboard Workers
                </h3>
                <p className="text-xs sm:text-sm font-bold text-slate-400 truncate">
                  Add multiple workers in bulk
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

          <div className="space-y-6">
            <div className="space-y-3">
              <div className="flex justify-between items-center ml-1">
                <label className="text-[10px] sm:text-xs font-black text-slate-400 uppercase tracking-[0.2em]">
                  Emails (Comma/Newline separated)
                </label>
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-1.5 text-[10px] font-black text-primary uppercase tracking-wider hover:underline"
                >
                  <FileUp size={12} />
                  Import CSV
                </button>
                <input 
                    type="file" 
                    ref={fileInputRef} 
                    onChange={handleFileUpload} 
                    accept=".csv,.txt" 
                    className="hidden" 
                />
              </div>
              <textarea
                value={emails}
                onChange={(e) => {
                    setEmails(e.target.value);
                    if (error) setError(null);
                }}
                placeholder="worker1@ex.com, worker2@ex.com..."
                rows={5}
                className="w-full p-6 rounded-2xl border-2 border-slate-100 text-slate-900 font-bold focus:outline-none focus:border-primary transition-all resize-none"
              />
              {error ? (
                <div className="flex items-center gap-2 text-rose-500 font-bold text-[10px] ml-1">
                    <AlertCircle size={14} />
                    {error}
                </div>
              ) : (
                <p className="text-xs text-slate-400 font-medium ml-1">
                  You can paste a list of emails or upload a CSV file.
                </p>
              )}
            </div>

            <button 
              onClick={handleSubmit}
              disabled={!emails.trim() || isSubmitting}
              className={cn(
                "w-full py-4 sm:py-5 rounded-[1.5rem] font-black shadow-xl transition-all flex items-center justify-center gap-2 active:scale-95",
                emails.trim() && !isSubmitting
                  ? "bg-primary text-white shadow-primary/20 hover:bg-primary/90"
                  : "bg-slate-100 text-slate-300 cursor-not-allowed shadow-none"
              )}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Sending Invites...
                </>
              ) : (
                <>
                  <Send size={18} />
                  Send Invites
                </>
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default OnboardWorkersModal
