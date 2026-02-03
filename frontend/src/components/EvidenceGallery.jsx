import React from 'react'
import { Camera } from 'lucide-react'
import { cn } from '../utils/utils'

export function EvidenceGallery({ issueId, status, apiUrl }) {
    const isResolved = status === 'RESOLVED' || status === 'CLOSED';
    
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
                <div className="flex items-center justify-between px-2">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Initial Condition (Before)</p>
                    <span className="px-2 py-0.5 bg-rose-50 text-rose-600 rounded text-[9px] font-black">REPORTED</span>
                </div>
                <div className="aspect-video bg-slate-100 rounded-[2rem] overflow-hidden border-8 border-white shadow-2xl relative group">
                    <img 
                        src={`${apiUrl}/media/${issueId}/before`} 
                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" 
                        alt="Initial Evidence" 
                    />
                </div>
            </div>

            <div className="space-y-4">
                <div className="flex items-center justify-between px-2">
                    <p className="text-[10px] font-black text-emerald-500 uppercase tracking-[0.2em]">Restoration Proof (After)</p>
                    {isResolved && <span className="px-2 py-0.5 bg-emerald-50 text-emerald-600 rounded text-[9px] font-black">RESOLVED</span>}
                </div>
                <div className={cn(
                    "aspect-video rounded-[2rem] overflow-hidden border-8 shadow-2xl flex items-center justify-center relative group",
                    isResolved ? "border-emerald-50 bg-white" : "border-slate-50 bg-slate-50 border-dashed"
                )}>
                    {isResolved ? (
                        <img 
                            src={`${apiUrl}/media/${issueId}/after`} 
                            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" 
                            alt="Resolution Evidence" 
                        />
                    ) : (
                        <div className="text-center p-10 space-y-4">
                            <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto text-slate-200 shadow-inner">
                                <Camera size={28} />
                            </div>
                            <p className="text-[11px] font-black text-slate-300 uppercase tracking-widest leading-relaxed">
                                Field Work in Progress.<br/>Resolution proof pending.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
