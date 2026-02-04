import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authService } from '../services/auth'
import { motion, AnimatePresence } from 'framer-motion'
import { ShieldCheck, Mail, Key, ArrowRight, Loader2 } from 'lucide-react'
import { cn } from '../utils/utils'

export default function Login() {
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [step, setStep] = useState(1) 
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleRequestOtp = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authService.requestOtp(email)
      setStep(2)
    } catch (err) {
      alert('Failed to send OTP')
    }
    setLoading(false)
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authService.login(email, otp)
      const decoded = authService.getCurrentUser()
      if (decoded.role === 'CITIZEN') navigate('/citizen')
      else if (decoded.role === 'ADMIN') navigate('/authority')
      else if (decoded.role === 'WORKER') navigate('/worker')
      else if (decoded.role === 'SYSADMIN') navigate('/admin')
    } catch (err) {
      alert('Invalid OTP')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-primary/5 rounded-full blur-[120px]"></div>
      <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-blue-600/5 rounded-full blur-[120px]"></div>
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-[480px] bg-white p-12 rounded-[3rem] shadow-[0_32px_64px_-16px_rgba(0,0,0,0.1)] relative z-10 border border-slate-100"
      >
        <div className="flex flex-col items-center mb-12 text-center">
          <div className="w-20 h-20 bg-primary rounded-3xl flex items-center justify-center text-white shadow-xl shadow-primary/20 mb-6">
            <ShieldCheck size={40} />
          </div>
          <h1 className="text-4xl font-black tracking-tight text-slate-900 mb-3">MARG</h1>
        </div>

        <AnimatePresence mode="wait">
          {step === 1 ? (
            <motion.form 
              key="step1"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              onSubmit={handleRequestOtp} 
              className="space-y-8"
            >
              <div className="space-y-3">
                <label className="text-sm font-black text-slate-800 ml-1">Official Email Address</label>
                <div className="relative group">
                  <Mail className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors" size={20} />
                  <input
                    type="email"
                    placeholder="name@authority.gov.in"
                    className="w-full pl-14 pr-6 py-5 bg-slate-50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-primary focus:ring-0 transition-all outline-none font-bold text-slate-900 placeholder:text-slate-300 placeholder:font-medium"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-5 px-8 bg-primary text-white rounded-2xl font-black text-lg flex items-center justify-center gap-3 hover:bg-blue-700 transition-all shadow-xl shadow-primary/20 disabled:bg-slate-200 disabled:shadow-none active:scale-[0.98]"
              >
                {loading ? <Loader2 className="animate-spin" /> : <>Request Access <ArrowRight size={22} /></>}
              </button>
            </motion.form>
          ) : (
            <motion.form 
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              onSubmit={handleLogin} 
              className="space-y-8"
            >
              <div className="p-5 bg-blue-50/50 rounded-2xl border border-blue-100 flex items-center gap-4">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 flex-shrink-0">
                    <Key size={18} />
                </div>
                <p className="text-sm text-blue-800 font-bold leading-tight">
                   Verification code has been dispatched to your email address.
                </p>
              </div>
              <div className="space-y-3">
                <label className="text-sm font-black text-slate-800 ml-1">Authentication Code</label>
                <div className="relative group">
                  <Key className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors" size={20} />
                  <input
                    type="text"
                    placeholder="Enter 6-digit code"
                    className="w-full pl-14 pr-6 py-5 bg-slate-50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-primary focus:ring-0 transition-all outline-none font-black text-slate-900 tracking-[0.5em] text-center text-xl placeholder:text-slate-300 placeholder:font-medium placeholder:tracking-normal"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    required
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-5 px-8 bg-primary text-white rounded-2xl font-black text-lg flex items-center justify-center gap-3 hover:bg-blue-700 transition-all shadow-xl shadow-primary/20 active:scale-[0.98]"
              >
                {loading ? <Loader2 className="animate-spin" /> : "Verify & Sign In"}
              </button>
              <button
                type="button"
                onClick={() => setStep(1)}
                className="w-full text-sm font-black text-slate-400 hover:text-slate-600 transition-colors uppercase tracking-widest"
              >
                Change Email Address
              </button>
            </motion.form>
          )}
        </AnimatePresence>
        
        <div className="mt-12 pt-10 border-t border-slate-100 text-center">
        </div>
      </motion.div>
    </div>
  )
}
