import React, { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import api from '../../services/api'
import { useNavigate } from 'react-router-dom'
import { Camera, MapPin, Check, ArrowLeft, ArrowRight, Upload, Map as MapIcon, Loader2, Info, AlertCircle, Navigation } from 'lucide-react'
import { authService } from '../../services/auth'
import { offlineService } from '../../services/offline'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'

import { SearchField } from '../../components/SearchField'
import { LocateControl } from '../../components/LocateControl'
import { useGeolocation } from '../../hooks/useGeolocation'

const MAP_TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

function LocationMarker({ position, setPosition }) {
  useMapEvents({
    click(e) {
      setPosition(e.latlng)
    },
  })

  return position === null ? null : (
    <Marker position={position}></Marker>
  )
}

const StepIndicator = ({ step }) => (
    <div className="flex items-center gap-2 mb-10">
        {[1, 2, 3].map((s) => (
            <React.Fragment key={s}>
                <div className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all shadow-md",
                    step === s ? "bg-primary text-white scale-110 ring-4 ring-primary/10" : 
                    step > s ? "bg-green-500 text-white" : "bg-slate-200 text-slate-400"
                )}>
                    {step > s ? <Check size={18} /> : s}
                </div>
                {s < 3 && <div className={cn("flex-1 h-1 rounded-full", step > s ? "bg-green-500" : "bg-slate-200")}></div>}
            </React.Fragment>
        ))}
    </div>
)

export default function ReportIssue() {
  const [step, setStep] = useState(1) 
  const [position, setPosition] = useState(null)
  const [photo, setPhoto] = useState(null)
  const [photoPreview, setPhotoPreview] = useState(null)
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const { 
    position: geoPosition, 
    loading: geoLoading, 
    error: geoError,
    refresh: refreshLocation,
    isUsingFallback 
  } = useGeolocation()

  useEffect(() => {
    if (geoPosition && !position) {
      setPosition({ lat: geoPosition.lat, lng: geoPosition.lng })
    }
  }, [geoPosition, position])

  useEffect(() => {
    api.get('/admin/categories').then(res => setCategories(res.data)).catch(() => {
        setCategories([
            {id: '1', name: 'Pothole'}, {id: '2', name: 'Drainage'}, {id: '3', name: 'Garbage'}
        ])
    })
  }, [])

  const handlePhotoChange = (e) => {
    if (e.target.files[0]) {
      setPhoto(e.target.files[0])
      setPhotoPreview(URL.createObjectURL(e.target.files[0]))
    }
  }

  const handleSubmit = async () => {
    setLoading(true)
    const user = authService.getCurrentUser()
    const reportData = {
        category_id: selectedCategory,
        lat: position.lat, lng: position.lng,
        reporter_email: user.sub, description, photo
    }

    try {
      if (!navigator.onLine) {
          await offlineService.saveReport(reportData)
          alert('Offline: Report saved and will be synced.')
          navigate('/citizen/my-reports')
      } else {
          const formData = new FormData()
          Object.keys(reportData).forEach(key => formData.append(key, reportData[key]))
          await api.post('/issues/report', formData)
          alert('Successfully reported!')
          navigate('/citizen/my-reports')
      }
    } catch (err) {
      alert('Failed to submit. Saving locally...')
      await offlineService.saveReport(reportData)
      navigate('/citizen/my-reports')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="px-8 py-6 bg-white border-b border-slate-100 flex items-center justify-between">
        <button onClick={() => step > 1 ? setStep(step - 1) : navigate('/citizen')} className="flex items-center gap-2 text-slate-500 font-bold hover:text-primary transition-colors">
          <ArrowLeft size={18} /> {step === 1 ? 'Cancel' : 'Back'}
        </button>
        <h1 className="text-xl font-extrabold tracking-tight">New Report</h1>
        <div className="w-20"></div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full p-8">
        <div className="bg-white rounded-[2.5rem] p-10 shadow-2xl shadow-slate-200/60 border border-slate-100 relative overflow-hidden">
          <StepIndicator step={step} />

          <AnimatePresence mode="wait">
            {step === 1 && (
              <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                <div className="mb-8">
                    <h2 className="text-3xl font-extrabold mb-2 text-slate-900">Pinpoint Location</h2>
                    <p className="text-slate-500 font-medium">Click on the map to mark the exact spot of the issue.</p>
                </div>
                
                {isUsingFallback && (
                  <div className="bg-amber-50 border border-amber-200 p-4 rounded-2xl flex items-start gap-3 mb-4">
                    <AlertCircle className="text-amber-500 flex-shrink-0 mt-0.5" size={20} />
                    <div>
                      <p className="text-sm font-bold text-amber-800">Using default location</p>
                      <p className="text-xs text-amber-600">{geoError} Please click on the map to set the correct location.</p>
                    </div>
                  </div>
                )}

                <div className="h-[400px] w-full rounded-[2rem] overflow-hidden border-4 border-slate-100 mb-8 shadow-inner relative">
                  {geoLoading ? (
                    <div className="h-full w-full flex flex-col items-center justify-center bg-slate-50">
                      <Loader2 className="animate-spin text-primary mb-4" size={40} />
                      <p className="text-slate-500 font-medium">Getting your location...</p>
                      <p className="text-slate-400 text-sm mt-1">Please allow location access when prompted</p>
                    </div>
                  ) : position ? (
                    <MapContainer center={position} zoom={17} className="h-full w-full">
                      <TileLayer url={MAP_TILES} attribution={MAP_ATTRIBUTION} />
                      <LocationMarker position={position} setPosition={setPosition} />
                      <SearchField />
                      <LocateControl onFound={setPosition} />
                    </MapContainer>
                  ) : (
                    <div className="h-full w-full flex flex-col items-center justify-center bg-slate-50">
                      <AlertCircle className="text-slate-400 mb-4" size={40} />
                      <p className="text-slate-500 font-medium">Unable to load map</p>
                      <button onClick={refreshLocation} className="mt-4 px-4 py-2 bg-primary text-white rounded-lg font-medium flex items-center gap-2">
                        <Navigation size={16} /> Retry Location
                      </button>
                    </div>
                  )}
                </div>
                <div className="bg-blue-50 p-6 rounded-2xl flex items-start gap-4 mb-8">
                    <div className="p-2 bg-primary text-white rounded-lg"><MapIcon size={20} /></div>
                    <div>
                        <p className="text-sm font-bold text-slate-800">Precision Lock</p>
                        <p className="text-xs text-slate-500 font-medium">
                          Current coordinates: {position?.lat.toFixed(6)}, {position?.lng.toFixed(6)}
                          {geoPosition?.accuracy && <span className="ml-2">(±{Math.round(geoPosition.accuracy)}m accuracy)</span>}
                        </p>
                    </div>
                </div>
                <button onClick={() => setStep(2)} disabled={!position} className="w-full py-5 bg-primary text-white rounded-[1.5rem] font-extrabold shadow-xl shadow-primary/20 hover:bg-blue-800 transition-all flex items-center justify-center gap-2 disabled:bg-slate-300 disabled:shadow-none">
                    Confirm & Proceed <ArrowRight size={20} />
                </button>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                <div className="mb-8 text-center">
                    <h2 className="text-3xl font-extrabold mb-2 text-slate-900">Visual Evidence</h2>
                    <p className="text-slate-500 font-medium">Please provide a clear photo of the infrastructure damage.</p>
                </div>
                <div className="group relative w-full aspect-video bg-slate-50 rounded-[2rem] border-4 border-dashed border-slate-200 flex flex-col items-center justify-center overflow-hidden transition-colors hover:border-primary/30 mb-8">
                    {photoPreview ? (
                        <img src={photoPreview} className="w-full h-full object-cover" />
                    ) : (
                        <>
                            <div className="w-20 h-20 bg-white rounded-full shadow-lg flex items-center justify-center text-primary mb-4 group-hover:scale-110 transition-transform">
                                <Camera size={32} />
                            </div>
                            <p className="text-lg font-bold text-slate-400">Click to capture or upload</p>
                        </>
                    )}
                    <input type="file" accept="image/*" capture="environment" onChange={handlePhotoChange} className="absolute inset-0 opacity-0 cursor-pointer" />
                </div>
                <div className="flex gap-4">
                    <button onClick={() => setStep(1)} className="flex-1 py-5 bg-slate-100 text-slate-600 rounded-[1.5rem] font-bold">Change Location</button>
                    <button onClick={() => setStep(3)} disabled={!photo} className="flex-[2] py-5 bg-primary text-white rounded-[1.5rem] font-extrabold disabled:bg-slate-200 shadow-xl shadow-primary/20">Next Step</button>
                </div>
              </motion.div>
            )}

            {step === 3 && (
              <motion.div key="step3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                <div className="mb-10 text-center">
                    <h2 className="text-3xl font-extrabold mb-2 text-slate-900">Final Details</h2>
                    <p className="text-slate-500 font-medium">Help us prioritize this issue by providing a category and short description.</p>
                </div>
                <div className="space-y-8 mb-10">
                    <div className="space-y-2">
                        <label className="text-sm font-bold text-slate-700 ml-1">Issue Category</label>
                        <select 
                            className="w-full p-4 bg-slate-100/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-primary outline-none font-medium transition-all"
                            value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)}
                        >
                            <option value="">Choose a category...</option>
                            {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-bold text-slate-700 ml-1">Notes (Optional)</label>
                        <textarea 
                            rows="4" placeholder="Describe the severity or any landmark..."
                            className="w-full p-4 bg-slate-100/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-primary outline-none font-medium transition-all"
                            value={description} onChange={(e) => setDescription(e.target.value)}
                        />
                    </div>
                </div>
                <button 
                    onClick={handleSubmit} disabled={loading || !selectedCategory}
                    className="w-full py-5 bg-primary text-white rounded-[1.5rem] font-extrabold shadow-xl shadow-primary/20 flex items-center justify-center gap-2"
                >
                    {loading ? <Loader2 className="animate-spin" /> : <>Submit Report to GHMC <Check size={20} /></>}
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        
        <div className="mt-12 bg-primary text-white p-6 rounded-[2rem] flex items-center gap-6 shadow-xl shadow-primary/20">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center"><Info size={24} /></div>
            <p className="text-sm font-medium leading-relaxed">
                Your report will be automatically grouped with others in the same area to ensure faster processing.
            </p>
        </div>
      </main>
    </div>
  )
}
