import { useState, useEffect } from 'react'
import api from '../../services/api'
import { 
    Camera, Send, ArrowLeft, Loader2,
    ShieldCheck, X, CheckCircle2, TriangleAlert
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import { useNavigate } from 'react-router-dom'
import { useGeolocation } from '../../hooks/useGeolocation'
import { InteractiveMap, Marker } from '../../components/InteractiveMap'


export default function ReportIssue() {
  const [description, setDescription] = useState('')
  const [photo, setPhoto] = useState(null)
  const [photoPreview, setPhotoPreview] = useState(null)
  const [position, setPosition] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [step, setStep] = useState(1)
  const [submissionResult, setSubmissionResult] = useState(null)
  const navigate = useNavigate()

  const { loading: geoLoading, position: geoPosition } = useGeolocation()

  useEffect(() => {
    if (!geoLoading && geoPosition && !position) {
      setPosition(geoPosition)
    }
  }, [geoLoading, geoPosition, position])

  const handlePhotoChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      setPhoto(file)
      setPhotoPreview(URL.createObjectURL(file))
    }
  }

  const handleSubmit = async () => {
    if (!position || !photo) {
      alert("Please complete all required fields")
      return
    }

    setSubmitting(true)
    const formData = new FormData()
    formData.append('description', description)
    formData.append('lat', position.lat)
    formData.append('lng', position.lng)
    formData.append('photo', photo)

    try {
      const response = await api.post('/issues/report', formData)
      setSubmissionResult({ kind: 'accepted', ...response.data })
      setStep(3)
      setTimeout(() => navigate('/citizen/my-reports'), 3000)
    } catch (err) {
      const rejection = err?.response?.data
      if (err?.response?.status === 422 && rejection?.submission_id) {
        setSubmissionResult({ kind: 'rejected', ...rejection })
        setStep(3)
      } else {
        alert("Failed to submit report. Please try again.")
      }
    } finally {
      setSubmitting(false)
    }
  }

  const isRejectedSubmission = submissionResult?.kind === 'rejected'

  return (
    <div className="min-h-screen bg-[#FDFDFD] flex flex-col font-sans">
      <header className="px-6 py-6 flex items-center justify-between sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-50">
        <button onClick={() => navigate(-1)} className="w-10 h-10 bg-slate-50 rounded-xl flex items-center justify-center text-slate-400 hover:text-primary transition-all">
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-sm font-black tracking-[0.2em] uppercase text-slate-900">New Incident Report</h1>
        <div className="w-10 h-10"></div>
      </header>

      <main className="flex-1 max-w-2xl mx-auto w-full p-6 pt-10">
        <div className="flex gap-2 mb-12">
            {[1, 2].map((i) => (
                <div key={i} className={cn("h-1.5 flex-1 rounded-full transition-all duration-500", step >= i ? "bg-primary shadow-[0_0_15px_rgba(59,130,246,0.5)]" : "bg-slate-100")}></div>
            ))}
        </div>

        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div 
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-10"
            >
                <div className="space-y-2">
                    <h2 className="text-4xl font-black text-slate-900 tracking-tight">Capture Evidence</h2>
                    <p className="text-slate-500 font-medium">Start by providing clear visual context of the issue.</p>
                </div>

                <div className="relative group">
                    <input 
                        type="file" 
                        accept="image/*" 
                        capture="environment"
                        onChange={handlePhotoChange}
                        className="hidden" 
                        id="photo-upload"
                    />
                    <label 
                        htmlFor="photo-upload"
                        className={cn(
                            "block aspect-square w-full rounded-[3rem] border-4 border-dashed cursor-pointer transition-all relative overflow-hidden",
                            photoPreview ? "border-primary shadow-2xl" : "border-slate-100 bg-slate-50 hover:bg-slate-100 hover:border-slate-200"
                        )}
                    >
                        {photoPreview ? (
                            <img src={photoPreview} className="w-full h-full object-cover" alt="Preview" />
                        ) : (
                            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                                <div className="w-20 h-20 bg-white rounded-3xl shadow-xl flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
                                    <Camera size={32} />
                                </div>
                                <p className="text-xs font-black text-slate-400 uppercase tracking-widest">Tap to Capture</p>
                            </div>
                        )}
                    </label>
                    {photoPreview && (
                        <button onClick={(e) => { e.preventDefault(); setPhoto(null); setPhotoPreview(null); }} className="absolute -top-3 -right-3 w-10 h-10 bg-slate-900 text-white rounded-2xl flex items-center justify-center shadow-xl">
                            <X size={20} />
                        </button>
                    )}
                </div>

                <button 
                    disabled={!photo}
                    onClick={() => setStep(2)}
                    className="w-full py-6 bg-slate-900 text-white rounded-[2rem] font-black shadow-2xl disabled:bg-slate-200 disabled:shadow-none transition-all active:scale-[0.98] flex items-center justify-center gap-3"
                >
                    Continue to Location <Send size={18} />
                </button>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div 
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-10"
            >
                <div className="space-y-2">
                    <h2 className="text-4xl font-black text-slate-900 tracking-tight">Pin Location</h2>
                    <p className="text-slate-500 font-medium">Verify the exact coordinates for the response team.</p>
                </div>

                <div className="h-[400px] w-full rounded-[2rem] overflow-hidden border-4 border-slate-100 mb-8 shadow-inner relative">
                  {geoLoading && !position ? (
                    <div className="h-full w-full flex flex-col items-center justify-center bg-slate-50">
                      <Loader2 className="animate-spin text-primary mb-4" size={40} />
                      <p className="text-slate-500 font-medium">Getting your location...</p>
                      <p className="text-slate-400 text-sm mt-1">Please allow location access when prompted</p>
                    </div>
                  ) : (
                    <InteractiveMap
                      initialViewState={{
                        longitude: position?.lng || 77.5946,
                        latitude: position?.lat || 12.9716,
                        zoom: 17
                      }}
                      onLocationSelect={(latlng) => setPosition(latlng)}
                      onClick={(e) => setPosition({ lat: e.lngLat.lat, lng: e.lngLat.lng })}
                    >
                      {position && <Marker longitude={position.lng} latitude={position.lat} />}
                    </InteractiveMap>
                  )}
                </div>

                <div className="space-y-4">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">Notes For Classifier And Field Team (Optional)</label>
                    <textarea 
                        className="w-full p-6 bg-slate-50 rounded-[2rem] border-2 border-transparent focus:border-primary focus:bg-white transition-all outline-none font-medium text-slate-700 resize-none"
                        rows="4"
                        placeholder="Provide any extra details that might help the field force..."
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                    />
                </div>

                <div className="flex gap-4">
                    <button 
                        onClick={() => setStep(1)}
                        className="p-6 bg-slate-100 text-slate-500 rounded-[2rem] font-black active:scale-95 transition-all"
                    >
                        Back
                    </button>
                    <button 
                        disabled={submitting || !position}
                        onClick={handleSubmit}
                        className="flex-1 py-6 bg-primary text-white rounded-[2rem] font-black shadow-2xl shadow-primary/20 disabled:bg-slate-200 transition-all active:scale-[0.98] flex items-center justify-center gap-3"
                    >
                        {submitting ? (
                            <> <Loader2 className="animate-spin" size={20} /> Transmitting... </>
                        ) : (
                            <> Broadcast Report <ShieldCheck size={20} /> </>
                        )}
                    </button>
                </div>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div 
              key="step3"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="py-20 flex flex-col items-center text-center space-y-8"
            >
                {isRejectedSubmission ? (
                  <div className="w-full max-w-xl rounded-[2.5rem] border border-red-200 bg-[radial-gradient(circle_at_top,_rgba(254,202,202,0.7),_rgba(255,255,255,1)_58%)] px-8 py-10 shadow-[0_28px_80px_rgba(153,27,27,0.16)]">
                    <div className="mx-auto flex w-fit items-center gap-3 rounded-full border border-red-200 bg-red-50 px-5 py-2 text-[11px] font-black uppercase tracking-[0.24em] text-red-700">
                      <span className="h-2.5 w-2.5 rounded-full bg-red-600 shadow-[0_0_18px_rgba(220,38,38,0.75)]"></span>
                      Screening Blocked
                    </div>
                    <div className="mt-8 flex flex-col items-center space-y-6">
                      <div className="flex h-32 w-32 items-center justify-center rounded-[3rem] border border-red-200 bg-gradient-to-br from-red-50 via-red-100 to-rose-200 text-red-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_24px_50px_rgba(220,38,38,0.16)]">
                        <TriangleAlert size={68} className="drop-shadow-[0_10px_24px_rgba(153,27,27,0.28)]" />
                      </div>
                      <div className="space-y-3">
                        <h2 className="text-4xl font-black text-red-950">Report Rejected</h2>
                        <p className="mx-auto max-w-md text-base font-semibold leading-7 text-red-900">
                          Intake screening blocked this submission before it entered the civic issue workflow.
                        </p>
                      </div>
                      <div className="w-full rounded-[2rem] border border-red-200/80 bg-white/80 px-6 py-5 text-left shadow-inner">
                        <p className="text-[11px] font-black uppercase tracking-[0.22em] text-red-600">Next step</p>
                        <p className="mt-3 text-sm font-medium leading-6 text-slate-700">
                          Try again with a clearer photo of a real civic issue. Avoid unrelated, obstructed, or low-information images.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="w-32 h-32 bg-emerald-50 rounded-[3rem] flex items-center justify-center text-emerald-500 shadow-inner">
                        <CheckCircle2 size={64} className="animate-bounce" />
                    </div>
                    <div className="space-y-3">
                        <h2 className="text-4xl font-black text-slate-900">Successfully Logged</h2>
                        <p className="text-slate-500 font-medium max-w-xs mx-auto">Your report has been received by the central dispatch system.</p>
                    </div>
                    <div className="pt-10">
                      <p className="text-slate-500 font-medium max-w-xs mx-auto">Accepted for review. A government admin will assign the category.</p>
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest animate-pulse mt-4">Redirecting to Dashboard...</p>
                    </div>
                  </>
                )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}
