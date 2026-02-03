import React, { useState, useEffect, useRef, useCallback } from 'react'
import api from '../../services/api'
import { 
    Briefcase, Clock, MapPin, Camera, Navigation, 
    LogOut, ArrowRight, Navigation2, Check, Loader2, Activity, Map as MapIcon, Globe,
    WifiOff, CloudOff, Upload, X
} from 'lucide-react'
import { authService } from '../../services/auth'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer } from 'react-leaflet'
import { HeatmapLayer } from '../../components/HeatmapLayer'
import { LocateControl } from '../../components/LocateControl'
import { SearchField } from '../../components/SearchField'
import { offlineService } from '../../services/offline'
import { useWorkerOfflineSync } from '../../hooks/useWorkerOfflineSync'

const MAP_TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

const TaskCard = ({ task, onSelect, onResolve, idx, hasPendingSync }) => {
    const isCritical = task.priority === 'P1';
    
    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="bg-white rounded-[2.5rem] p-8 border border-slate-100 shadow-[0_20px_50px_-12px_rgba(0,0,0,0.05)] relative overflow-hidden"
        >
            {hasPendingSync && (
                <div className="absolute top-4 right-4 flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-600 rounded-full text-xs font-bold">
                    <CloudOff size={14} />
                    Pending Sync
                </div>
            )}
            
            <div className="flex justify-between items-start mb-6">
                <div className="space-y-3">
                    <div className={cn(
                        "inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest",
                        isCritical ? "bg-rose-50 text-rose-600" : "bg-blue-50 text-blue-600"
                    )}>
                        <div className={cn("w-1.5 h-1.5 rounded-full animate-pulse", isCritical ? "bg-rose-600" : "bg-blue-600")}></div>
                        {task.priority} Priority
                    </div>
                    <h3 className="text-2xl font-black text-slate-900 leading-tight">{task.category_name}</h3>
                    <p className="flex items-center gap-2 text-sm font-bold text-slate-400">
                        <MapPin size={14} className="text-primary" /> {task.address || 'Location Identified'}
                    </p>
                </div>
                <div className="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-400 border border-slate-100 shadow-inner">
                    <Navigation2 size={24} />
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="bg-slate-50/50 rounded-2xl p-5 border border-slate-100">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Reports</p>
                    <p className="text-2xl font-black text-slate-900">{task.report_count}</p>
                </div>
                <div className="bg-slate-50/50 rounded-2xl p-5 border border-slate-100">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Status</p>
                    <p className="text-2xl font-black text-primary">{task.status}</p>
                </div>
            </div>

            <div className="flex gap-4">
                {task.status === 'ASSIGNED' ? (
                    <button 
                        onClick={() => onSelect(task)}
                        className="flex-1 py-5 bg-primary text-white rounded-[1.5rem] font-black shadow-xl shadow-primary/20 hover:bg-blue-700 transition-all flex items-center justify-center gap-2 active:scale-95"
                    >
                        Accept Task <ArrowRight size={20} />
                    </button>
                ) : task.status === 'ACCEPTED' || task.status === 'IN_PROGRESS' ? (
                    <button 
                        onClick={() => onResolve(task)}
                        disabled={hasPendingSync}
                        className={cn(
                            "flex-1 py-5 rounded-[1.5rem] font-black shadow-xl transition-all flex items-center justify-center gap-3 active:scale-95",
                            hasPendingSync 
                                ? "bg-amber-100 text-amber-600 cursor-not-allowed" 
                                : "bg-emerald-600 text-white shadow-emerald-200 hover:bg-emerald-700"
                        )}
                    >
                        <Camera size={24} /> {hasPendingSync ? 'Awaiting Sync' : 'Resolve Task'}
                    </button>
                ) : (
                    <div className="flex-1 py-5 bg-slate-100 text-slate-400 rounded-[1.5rem] font-black text-center">
                        {task.status}
                    </div>
                )}
            </div>
            
            {task.status === 'IN_PROGRESS' && !hasPendingSync && (
                <div className="absolute top-8 right-8">
                    <span className="flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                    </span>
                </div>
            )}
        </motion.div>
    )
}

export default function WorkerHome() {
  const [activeTab, setActiveTab] = useState('tasks') 
  const [tasks, setTasks] = useState([])
  const [heatmapData, setHeatmapData] = useState([])
  const [selectedTask, setSelectedTask] = useState(null)
  const [resolveTask, setResolveTask] = useState(null)
  const [eta, setEta] = useState('')
  const [loading, setLoading] = useState(true)
  const [userLocation, setUserLocation] = useState([17.4447, 78.3483])
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [pendingResolutions, setPendingResolutions] = useState({})
  const [resolvePhoto, setResolvePhoto] = useState(null)
  const [isResolving, setIsResolving] = useState(false)
  const [toast, setToast] = useState(null)
  const fileInputRef = useRef(null)
  const user = authService.getCurrentUser()
  const navigate = useNavigate()

  const handleSyncComplete = useCallback((issueId, success) => {
    setPendingResolutions(prev => {
      const updated = { ...prev };
      delete updated[issueId];
      return updated;
    });
    if (success) {
      showToast('Resolution synced successfully!', 'success');
      fetchTasks();
    } else {
      showToast('Resolution sync failed', 'error');
    }
  }, []);

  const { pendingCount, isSyncing } = useWorkerOfflineSync(handleSyncComplete);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const loadPendingResolutions = useCallback(async () => {
    try {
      const pending = await offlineService.getPendingResolutions();
      const pendingMap = {};
      pending.forEach(r => { pendingMap[r.issueId] = true; });
      setPendingResolutions(pendingMap);
    } catch {}
  }, []);

  useEffect(() => { 
    fetchTasks();
    loadPendingResolutions();
    api.get('/analytics/heatmap').then(res => setHeatmapData(res.data)).catch(() => {});
    navigator.geolocation.getCurrentPosition(
      (pos) => setUserLocation([pos.coords.latitude, pos.coords.longitude]),
      () => {}
    );

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [loadPendingResolutions]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res = await api.get('/worker/tasks');
      setTasks(res.data);
    } catch (err) {
      console.error("Failed to fetch tasks");
    }
    setLoading(false);
  };

  const handleAccept = async (taskId) => {
    try {
        await api.post(`/worker/tasks/${taskId}/accept?eta=${eta}`);
        showToast('Task successfully accepted.', 'success');
        fetchTasks();
        setSelectedTask(null);
    } catch (err) { 
      showToast('Failed to synchronize status.', 'error'); 
    }
  };

  const handleResolveSubmit = async () => {
    if (!resolvePhoto || !resolveTask) return;
    
    setIsResolving(true);

    if (!navigator.onLine) {
      try {
        await offlineService.saveResolution(resolveTask.id, resolvePhoto, {
          category_name: resolveTask.category_name,
          priority: resolveTask.priority,
        });
        setPendingResolutions(prev => ({ ...prev, [resolveTask.id]: true }));
        showToast('Resolution saved offline. Will sync when connected.', 'info');
        setResolveTask(null);
        setResolvePhoto(null);
      } catch (err) {
        showToast('Failed to save offline resolution.', 'error');
      }
      setIsResolving(false);
      return;
    }

    try {
      const formData = new FormData();
      formData.append('photo', resolvePhoto);
      await api.post(`/worker/tasks/${resolveTask.id}/resolve`, formData);
      showToast('Task resolved successfully!', 'success');
      fetchTasks();
      setResolveTask(null);
      setResolvePhoto(null);
    } catch (err) {
      showToast('Failed to resolve task.', 'error');
    }
    setIsResolving(false);
  };

  const handlePhotoCapture = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setResolvePhoto(file);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Offline Banner */}
      <AnimatePresence>
        {!isOnline && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="bg-amber-500 text-white px-4 py-3 flex items-center justify-center gap-2 text-sm font-bold"
          >
            <WifiOff size={16} />
            You're offline. Resolutions will sync when connected.
            {pendingCount > 0 && <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs">{pendingCount} pending</span>}
          </motion.div>
        )}
      </AnimatePresence>

      <header className="px-8 py-10 bg-white/80 backdrop-blur-xl border-b border-slate-100 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <div className="flex items-center gap-5">
           <div className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center text-white shadow-2xl shadow-primary/30">
              <Briefcase size={28} />
           </div>
           <div>
              <h1 className="text-xl font-black text-slate-900 leading-none tracking-tight">Field Force</h1>
              <div className="flex items-center gap-2 mt-1.5">
                <div className={cn("w-2 h-2 rounded-full", isOnline ? "bg-emerald-500" : "bg-amber-500")}></div>
                <p className="text-[10px] font-black text-slate-400 tracking-widest uppercase">
                  Agent: {isOnline ? 'Online' : 'Offline'}
                </p>
              </div>
           </div>
        </div>
        <button onClick={() => authService.logout()} className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all border border-slate-100 shadow-sm">
          <LogOut size={20} />
        </button>
      </header>

      <main className="flex-1 overflow-auto p-8 pb-32 max-w-3xl mx-auto w-full">
        <AnimatePresence mode="wait">
          {activeTab === 'tasks' ? (
            <motion.div key="tasks" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-8">
                <div className="flex items-center justify-between px-2 mb-2">
                    <div className="space-y-1">
                        <h2 className="text-3xl font-black text-slate-900">Assigned Tasks</h2>
                        <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Region: Gachibowli Zone</p>
                    </div>
                    <div className="text-right">
                        <p className="text-2xl font-black text-primary">{tasks.length}</p>
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">Pending</p>
                    </div>
                </div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <Loader2 className="animate-spin text-primary" size={32} />
                        <p className="text-xs font-black text-slate-400 uppercase tracking-widest">Refreshing task pool...</p>
                    </div>
                ) : tasks.length === 0 ? (
                    <div className="bg-white rounded-[3rem] p-12 text-center border border-slate-100 shadow-xl">
                        <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6 text-slate-200">
                            <Activity size={32} />
                        </div>
                        <h3 className="text-xl font-black text-slate-900 mb-2">Clear Schedule</h3>
                        <p className="text-slate-400 font-bold text-sm">No infrastructure reports require your attention.</p>
                    </div>
                ) : (
                    tasks.map((task, idx) => (
                        <TaskCard 
                          key={task.id} 
                          task={task} 
                          idx={idx} 
                          onSelect={setSelectedTask}
                          onResolve={setResolveTask}
                          hasPendingSync={pendingResolutions[task.id]}
                        />
                    ))
                )}
            </motion.div>
          ) : activeTab === 'map' ? (
            <motion.div key="map" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="h-[70vh] space-y-8">
                <div className="flex items-center justify-between px-2">
                    <h2 className="text-3xl font-black text-slate-900">Workzone Map</h2>
                    <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Active Infrastructure Heatmap</p>
                </div>
                <div className="h-full w-full rounded-[3rem] overflow-hidden border-8 border-white shadow-2xl relative">
                    <MapContainer center={userLocation} zoom={12} className="h-full w-full">
                        <TileLayer url={MAP_TILES} attribution={MAP_ATTRIBUTION} />
                        <HeatmapLayer points={heatmapData} />
                        <LocateControl />
                        <SearchField />
                    </MapContainer>
                </div>
            </motion.div>
          ) : (
            <motion.div key="history" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center justify-center py-24 text-center">
                <div className="w-24 h-24 bg-white rounded-[2.5rem] flex items-center justify-center text-slate-200 mb-8 border border-slate-100 shadow-xl">
                    <Clock size={48} />
                </div>
                <h3 className="text-2xl font-black text-slate-900 mb-3">Service History</h3>
                <p className="text-slate-400 font-bold max-w-[280px]">Completed resolutions will appear here after administrative approval.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <nav className="h-28 bg-white/80 backdrop-blur-2xl border-t border-slate-100 fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around px-10 shadow-[0_-10px_30px_rgba(0,0,0,0.02)]">
        <button onClick={() => setActiveTab('tasks')} className={cn("flex flex-col items-center gap-1.5 transition-all", activeTab === 'tasks' ? "text-primary scale-110" : "text-slate-300 hover:text-slate-500")}>
          <Briefcase size={28} />
          <span className="text-[10px] font-black uppercase tracking-tighter">Tasks</span>
        </button>

        <button onClick={() => setActiveTab('map')} className={cn("flex flex-col items-center gap-1.5 transition-all", activeTab === 'map' ? "text-primary scale-110" : "text-slate-300 hover:text-slate-500")}>
          <MapIcon size={28} />
          <span className="text-[10px] font-black uppercase tracking-tighter">Area Map</span>
        </button>

        <button onClick={() => navigate('/analytics')} className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-primary transition-all">
          <Globe size={28} />
          <span className="text-[10px] font-black uppercase tracking-tighter">City Health</span>
        </button>
        
        <button onClick={() => setActiveTab('history')} className={cn("flex flex-col items-center gap-1.5 transition-all", activeTab === 'history' ? "text-primary scale-110" : "text-slate-300 hover:text-slate-500")}>
          <Clock size={28} />
          <span className="text-[10px] font-black uppercase tracking-tighter">History</span>
        </button>
      </nav>

      {/* Accept Task Modal */}
      <AnimatePresence>
        {selectedTask && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-[2000] flex items-end sm:items-center justify-center p-6">
                <motion.div initial={{ y: 100, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 100, opacity: 0 }} className="bg-white w-full max-w-md rounded-[3rem] p-10 shadow-2xl border border-slate-100">
                    <div className="flex items-center gap-6 mb-10">
                        <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center text-primary shadow-inner">
                            <Clock size={32} />
                        </div>
                        <div>
                            <h3 className="text-2xl font-black text-slate-900">Task Acceptance</h3>
                            <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">ID: {selectedTask.id.slice(0,8)}</p>
                        </div>
                    </div>

                    <div className="space-y-10">
                        <div className="space-y-4">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">Expected Arrival (ETA)</label>
                            <div className="grid grid-cols-3 gap-3">
                                {['30m', '1h', '2h', '4h', '1d', '2d'].map(time => (
                                    <button key={time} onClick={() => setEta(time)} className={cn("py-4 rounded-2xl font-black text-sm border-2 transition-all active:scale-95", eta === time ? "bg-primary border-primary text-white shadow-xl shadow-primary/20" : "bg-slate-50 border-transparent text-slate-500 hover:bg-slate-100")}>{time}</button>
                                ))}
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <button onClick={() => setSelectedTask(null)} className="flex-1 py-5 bg-slate-100 text-slate-400 rounded-[1.5rem] font-black hover:bg-slate-200 hover:text-slate-900 transition-all">Dismiss</button>
                            <button onClick={() => handleAccept(selectedTask.id)} disabled={!eta} className="flex-[2] py-5 bg-primary text-white rounded-[1.5rem] font-black shadow-xl shadow-primary/20 disabled:bg-slate-100 disabled:text-slate-300 disabled:shadow-none transition-all active:scale-95">Confirm & Accept</button>
                        </div>
                    </div>
                </motion.div>
            </motion.div>
        )}
      </AnimatePresence>

      {/* Resolve Task Modal */}
      <AnimatePresence>
        {resolveTask && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-[2000] flex items-end sm:items-center justify-center p-6">
                <motion.div initial={{ y: 100, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 100, opacity: 0 }} className="bg-white w-full max-w-md rounded-[3rem] p-10 shadow-2xl border border-slate-100">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-6">
                            <div className="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center text-emerald-600 shadow-inner">
                                <Camera size={32} />
                            </div>
                            <div>
                                <h3 className="text-2xl font-black text-slate-900">Resolve Task</h3>
                                <p className="text-sm font-bold text-slate-400">{resolveTask.category_name}</p>
                            </div>
                        </div>
                        <button onClick={() => { setResolveTask(null); setResolvePhoto(null); }} className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400 hover:bg-slate-200">
                            <X size={20} />
                        </button>
                    </div>

                    {!isOnline && (
                        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-6 flex items-center gap-3">
                            <WifiOff size={20} className="text-amber-600" />
                            <p className="text-sm font-bold text-amber-700">Offline mode - resolution will sync automatically</p>
                        </div>
                    )}

                    <div className="space-y-6">
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            capture="environment"
                            onChange={handlePhotoCapture}
                            className="hidden"
                        />
                        
                        {resolvePhoto ? (
                            <div className="relative">
                                <img 
                                    src={URL.createObjectURL(resolvePhoto)} 
                                    alt="Resolution proof" 
                                    className="w-full h-64 object-cover rounded-2xl border-4 border-emerald-200"
                                />
                                <button 
                                    onClick={() => setResolvePhoto(null)}
                                    className="absolute top-3 right-3 w-8 h-8 bg-white/90 rounded-full flex items-center justify-center text-slate-500 hover:bg-red-50 hover:text-red-500"
                                >
                                    <X size={16} />
                                </button>
                            </div>
                        ) : (
                            <button 
                                onClick={() => fileInputRef.current?.click()}
                                className="w-full h-48 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center gap-3 text-slate-400 hover:border-emerald-400 hover:text-emerald-500 transition-all"
                            >
                                <Camera size={48} />
                                <span className="font-bold text-sm">Tap to capture resolution photo</span>
                            </button>
                        )}

                        <button 
                            onClick={handleResolveSubmit}
                            disabled={!resolvePhoto || isResolving}
                            className={cn(
                                "w-full py-5 rounded-[1.5rem] font-black shadow-xl transition-all flex items-center justify-center gap-3 active:scale-95",
                                resolvePhoto && !isResolving
                                    ? "bg-emerald-600 text-white shadow-emerald-200 hover:bg-emerald-700"
                                    : "bg-slate-100 text-slate-300 cursor-not-allowed shadow-none"
                            )}
                        >
                            {isResolving ? (
                                <>
                                    <Loader2 size={20} className="animate-spin" />
                                    {isOnline ? 'Submitting...' : 'Saving offline...'}
                                </>
                            ) : (
                                <>
                                    <Upload size={20} />
                                    {isOnline ? 'Submit Resolution' : 'Save for Sync'}
                                </>
                            )}
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        )}
      </AnimatePresence>

      {/* Toast Notification */}
      <AnimatePresence>
        {toast && (
            <motion.div 
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 50 }}
                className={cn(
                    "fixed bottom-36 left-1/2 -translate-x-1/2 px-6 py-4 rounded-2xl font-bold shadow-2xl z-[3000] flex items-center gap-3",
                    toast.type === 'success' && "bg-emerald-600 text-white",
                    toast.type === 'error' && "bg-red-600 text-white",
                    toast.type === 'info' && "bg-slate-800 text-white"
                )}
            >
                {toast.type === 'success' && <Check size={20} />}
                {toast.type === 'error' && <X size={20} />}
                {toast.type === 'info' && <CloudOff size={20} />}
                {toast.message}
            </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
