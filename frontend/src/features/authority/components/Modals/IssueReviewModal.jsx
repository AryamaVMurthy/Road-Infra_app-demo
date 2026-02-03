import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle, AlertCircle, MapPin, Clock, User, MessageSquare } from 'lucide-react'
import { cn } from '../../../../utils/utils'
import { API_URL } from '../../../../services/api'

/**
 * IssueReviewModal - Modal for reviewing issue details and resolution
 * 
 * Features:
 * - Before/after photo comparison
 * - Issue details display
 * - Approve/Reject actions for resolved issues
 * - Rejection reason input
 * 
 * @param {Object} issue - Issue data to review
 * @param {Function} onClose - Close modal callback
 * @param {Function} onApprove - Approve issue callback
 * @param {Function} onReject - Reject issue callback (with reason)
 * @param {boolean} submitting - Whether an action is in progress
 */
export const IssueReviewModal = ({ issue, onClose, onApprove, onReject, submitting }) => {
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)

  if (!issue) return null

  const isResolved = issue.status === 'RESOLVED'
  const isClosed = issue.status === 'CLOSED'

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }} 
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-[2000] flex items-center justify-center p-4 sm:p-12"
      >
        <motion.div 
          initial={{ scale: 0.9, y: 20 }} 
          animate={{ scale: 1, y: 0 }} 
          className="bg-white rounded-[3rem] w-full max-w-6xl flex flex-col max-h-[90vh] shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="p-6 sm:p-8 border-b flex justify-between items-center bg-white sticky top-0 z-10">
            <div>
              <h3 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                Infrastructure Intelligence Console
              </h3>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">
                Incident Ticket #{issue.id.slice(0,8)} • Category: {issue.category_name}
                {issue.eta_duration && (
                  <span className="ml-4 text-amber-600">• ETA: {issue.eta_duration}</span>
                )}
              </p>
            </div>
            <button 
              onClick={onClose} 
              className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-slate-100 text-slate-500 hover:text-red-500 flex items-center justify-center transition-all hover:bg-slate-200"
            >
              <X size={20} />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 flex flex-col lg:flex-row gap-6 sm:gap-8 p-6 sm:p-10 overflow-auto bg-slate-50/50">
            {/* Before Photo */}
            <PhotoPanel
              title="Before Reconstruction"
              subtitle="Initial Report"
              imageUrl={`${API_URL}/media/${issue.id}/before`}
              timestamp={issue.created_at}
              color="rose"
              label="INITIAL"
            />

            {/* After Photo (if resolved/closed) */}
            <PhotoPanel
              title="Resolution Verification"
              subtitle={isResolved || isClosed ? "Field Resolution" : "Awaiting Resolution"}
              imageUrl={(isResolved || isClosed) ? `${API_URL}/media/${issue.id}/after` : null}
              timestamp={issue.resolved_at}
              color="emerald"
              label="FIELD"
              placeholder={!isResolved && !isClosed}
            />
          </div>

          {/* Issue Details */}
          <div className="px-6 sm:px-10 py-4 bg-white border-t">
            <IssueDetails issue={issue} />
          </div>

          {/* Actions Footer */}
          {isResolved && (
            <div className="p-6 sm:p-8 bg-white border-t">
              {!showRejectForm ? (
                <ActionButtons
                  onApprove={() => onApprove(issue.id)}
                  onReject={() => setShowRejectForm(true)}
                  submitting={submitting}
                />
              ) : (
                <RejectForm
                  reason={rejectReason}
                  onReasonChange={setRejectReason}
                  onCancel={() => {
                    setShowRejectForm(false)
                    setRejectReason('')
                  }}
                  onSubmit={() => onReject(issue.id, rejectReason)}
                  submitting={submitting}
                />
              )}
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

/**
 * PhotoPanel - Displays before/after photos
 */
const PhotoPanel = ({ title, subtitle, imageUrl, timestamp, color, label, placeholder = false }) => {
  const colorClasses = {
    rose: {
      bg: 'bg-rose-100',
      text: 'text-rose-600',
      border: 'border-white'
    },
    emerald: {
      bg: 'bg-emerald-100',
      text: 'text-emerald-600',
      border: 'border-emerald-50'
    }
  }

  const colors = colorClasses[color]

  return (
    <div className="flex-1 flex flex-col gap-4 sm:gap-6 min-h-[300px]">
      {/* Panel Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center font-black text-[10px]", colors.bg, colors.text)}>
            {label}
          </div>
          <h4 className="font-black text-slate-900 text-sm sm:text-base">{title}</h4>
        </div>
        <span className="text-[10px] font-black text-slate-400 uppercase">
          {timestamp ? new Date(timestamp).toLocaleString() : subtitle}
        </span>
      </div>

      {/* Image Container */}
      <div className={cn("flex-1 bg-white rounded-[2.5rem] overflow-hidden shadow-2xl flex items-center justify-center", colors.border, !placeholder && "border-8")}>
        {placeholder ? (
          <div className="text-center p-10 space-y-4">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto text-slate-200 shadow-inner">
              <Clock size={28} />
            </div>
            <p className="text-slate-400 font-bold">Awaiting Field Resolution</p>
          </div>
        ) : (
          <img 
            src={imageUrl} 
            className="w-full h-full object-cover" 
            alt={title}
            onError={(e) => {
              e.target.style.display = 'none'
              e.target.nextSibling.style.display = 'flex'
            }}
          />
        )}
        <div className="hidden text-center p-10">
          <AlertCircle size={40} className="text-slate-300 mx-auto mb-2" />
          <p className="text-slate-400">Image not available</p>
        </div>
      </div>
    </div>
  )
}

/**
 * IssueDetails - Displays issue metadata
 */
const IssueDetails = ({ issue }) => (
  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
    <DetailItem 
      icon={MapPin}
      label="Location"
      value={issue.address || 'GPS Coordinates'}
    />
    <DetailItem 
      icon={User}
      label="Reporter"
      value={issue.worker_name || 'Unknown'}
    />
    <DetailItem 
      icon={Clock}
      label="Status"
      value={issue.status}
      highlight
    />
    <DetailItem 
      icon={MessageSquare}
      label="Priority"
      value={issue.priority}
    />
  </div>
)

/**
 * DetailItem - Individual detail row
 */
const DetailItem = ({ icon: Icon, label, value, highlight = false }) => (
  <div className="flex items-start gap-3">
    <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center text-slate-400 flex-shrink-0">
      <Icon size={16} />
    </div>
    <div>
      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
      <p className={cn(
        "text-sm font-bold",
        highlight ? "text-primary" : "text-slate-700"
      )}>
        {value}
      </p>
    </div>
  </div>
)

/**
 * ActionButtons - Approve/Reject buttons
 */
const ActionButtons = ({ onApprove, onReject, submitting }) => (
  <div className="flex items-center justify-between">
    <div className="flex items-center gap-3">
      <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center text-emerald-600">
        <CheckCircle size={20} />
      </div>
      <div>
        <p className="font-black text-slate-900">Resolution Verification</p>
        <p className="text-xs text-slate-400">Review the after photo and approve or reject</p>
      </div>
    </div>
    <div className="flex gap-3">
      <button
        onClick={onReject}
        disabled={submitting}
        className="px-6 py-3 bg-slate-100 text-slate-600 rounded-2xl font-bold hover:bg-slate-200 transition-all disabled:opacity-50"
      >
        Reject
      </button>
      <button
        onClick={onApprove}
        disabled={submitting}
        className="px-8 py-3 bg-emerald-600 text-white rounded-2xl font-bold hover:bg-emerald-700 transition-all shadow-xl shadow-emerald-200 disabled:opacity-50 flex items-center gap-2"
      >
        {submitting ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <CheckCircle size={18} />
            Approve & Close
          </>
        )}
      </button>
    </div>
  </div>
)

/**
 * RejectForm - Form for submitting rejection reason
 */
const RejectForm = ({ reason, onReasonChange, onCancel, onSubmit, submitting }) => (
  <div className="space-y-4">
    <div className="flex items-center gap-3 mb-4">
      <div className="w-10 h-10 bg-rose-100 rounded-xl flex items-center justify-center text-rose-600">
        <AlertCircle size={20} />
      </div>
      <div>
        <p className="font-black text-slate-900">Reject Resolution</p>
        <p className="text-xs text-slate-400">Provide a reason for rejection</p>
      </div>
    </div>

    <textarea
      value={reason}
      onChange={(e) => onReasonChange(e.target.value)}
      placeholder="Explain why this resolution is insufficient..."
      className="w-full p-4 bg-slate-50 border-2 border-slate-200 rounded-2xl focus:border-rose-400 focus:bg-white outline-none transition-all resize-none"
      rows={3}
    />

    <div className="flex gap-3 justify-end">
      <button
        onClick={onCancel}
        disabled={submitting}
        className="px-6 py-3 bg-slate-100 text-slate-600 rounded-2xl font-bold hover:bg-slate-200 transition-all disabled:opacity-50"
      >
        Cancel
      </button>
      <button
        onClick={onSubmit}
        disabled={!reason.trim() || submitting}
        className="px-8 py-3 bg-rose-600 text-white rounded-2xl font-bold hover:bg-rose-700 transition-all shadow-xl shadow-rose-200 disabled:opacity-50 disabled:shadow-none flex items-center gap-2"
      >
        {submitting ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <AlertCircle size={18} />
            Confirm Rejection
          </>
        )}
      </button>
    </div>
  </div>
)

export default IssueReviewModal
