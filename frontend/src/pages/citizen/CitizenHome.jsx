import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, LayoutList, LogOut, MapPin, ChevronRight, Globe } from 'lucide-react'
import { authService } from '../../services/auth'
import { useAuth } from '../../hooks/useAuth'
import { motion } from 'framer-motion'
import { cn } from '../../utils/utils'

const NavCard = ({ to, title, description, icon: Icon, primary = false, onClick }) => {
    const Component = to ? Link : 'button';
    return (
        <motion.div whileHover={{ y: -5, scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Component
                to={to}
                onClick={onClick}
                className={cn(
                    "flex flex-col p-8 rounded-[2rem] shadow-xl border transition-all h-full group text-left w-full",
                    primary ? "bg-primary text-white border-primary/20 shadow-primary/20" : "bg-white text-slate-900 border-slate-100 shadow-slate-200/50"
                )}
            >
                <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center mb-6 transition-colors", 
                    primary ? "bg-white/20 text-white" : "bg-primary/10 text-primary group-hover:bg-primary group-hover:text-white"
                )}>
                    <Icon size={28} />
                </div>
                <h3 className="text-xl font-extrabold mb-2">{title}</h3>
                <p className={cn("text-sm font-medium leading-relaxed mb-6", primary ? "text-white/70" : "text-slate-500")}>
                    {description}
                </p>
                <div className="mt-auto flex items-center gap-2 font-bold text-xs uppercase tracking-widest">
                    <span>{to ? 'Explore Now' : 'View Data'}</span>
                    <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
                </div>
            </Component>
        </motion.div>
    )
}

export default function CitizenHome() {
  const { user } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="px-8 py-6 bg-white/80 backdrop-blur-md sticky top-0 z-50 border-b border-slate-100">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-white shadow-lg">
                <MapPin size={20} />
             </div>
             <h1 className="text-xl font-extrabold tracking-tight">MARG</h1>
          </div>
          <div className="flex items-center gap-4">
             <button onClick={() => authService.logout()} className="flex items-center gap-2 px-4 py-2 text-red-600 bg-red-50 rounded-full font-bold text-sm hover:bg-red-100 transition-all">
                <LogOut size={16} /> Sign Out
             </button>
          </div>

        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-8 py-12">
        <motion.section 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-12"
        >
            <h2 className="text-5xl font-extrabold text-slate-900 tracking-tight mb-4">
                Namaste, <span className="text-primary">{user?.email?.split('@')[0] || 'Citizen'}</span>.
            </h2>
            <p className="text-xl text-slate-500 font-medium max-w-2xl leading-relaxed">
                Empowering every citizen to report, track, and resolve city-wide infrastructure issues in real-time.
            </p>
        </motion.section>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <NavCard 
                to="/citizen/report"
                title="Report New Issue"
                description="Use your camera and GPS to instantly alert authorities about potholes, leaks, or garbage."
                icon={Plus}
                primary
            />
            <NavCard 
                to="/citizen/my-reports"
                title="Your History"
                description="Monitor the real-time resolution status of every issue you've reported."
                icon={LayoutList}
            />
            <NavCard 
                onClick={() => navigate('/analytics')}
                title="City Analytics"
                description="View real-time infrastructure health, hotspots, and city-wide resolution trends."
                icon={Globe}
            />
        </div>

        <motion.section 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="mt-16 bg-slate-900 rounded-[3rem] p-10 text-white relative overflow-hidden shadow-2xl"
        >
            <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
                <div className="space-y-2">
                    <h3 className="text-3xl font-black tracking-tight">Citizen Impact Dashboard</h3>
                    <p className="text-slate-400 font-medium">Your data helps build a more resilient city.</p>
                </div>
                <button 
                    onClick={() => navigate('/analytics')}
                    className="px-10 py-5 bg-primary text-white font-black rounded-2xl shadow-xl shadow-primary/20 hover:bg-blue-700 transition-all flex items-center gap-3"
                >
                    View City Health Analytics <ChevronRight size={20} />
                </button>
            </div>
            <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-primary/20 rounded-full blur-[100px]"></div>
        </motion.section>
      </main>

      <footer className="py-12 border-t border-slate-100 text-center">
          <p className="text-sm text-slate-400 font-medium">© 2026 MARG</p>
      </footer>
    </div>
  )
}
