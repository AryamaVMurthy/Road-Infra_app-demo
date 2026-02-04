import React, { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { MoreVertical, ChevronRight, UserPlus, UserMinus, ArrowRight, Search, X, Flag } from 'lucide-react'
import { cn } from '../../../../utils/utils'

const KANBAN_STATUSES = [
  { value: 'REPORTED', label: 'Reported', color: 'bg-rose-500' },
  { value: 'ASSIGNED', label: 'Assigned', color: 'bg-blue-500' },
  { value: 'IN_PROGRESS', label: 'In Progress', color: 'bg-amber-500' },
  { value: 'RESOLVED', label: 'Resolved', color: 'bg-emerald-500' },
  { value: 'CLOSED', label: 'Closed', color: 'bg-slate-400' },
]

const PRIORITIES = [
  { value: 'P1', label: 'P1 - Critical', color: 'bg-rose-500' },
  { value: 'P2', label: 'P2 - High', color: 'bg-amber-500' },
  { value: 'P3', label: 'P3 - Medium', color: 'bg-blue-500' },
  { value: 'P4', label: 'P4 - Low', color: 'bg-slate-400' },
]

/**
 * IssueActionsDropdown - Comprehensive actions menu for issue cards
 * 
 * Features:
 * - Assign/Reassign workers
 * - Unassign workers
 * - Change status
 * - Shows worker workload indicators
 * 
 * @param {Object} issue - Issue data object
 * @param {Array} workers - List of available workers
 * @param {Function} onUpdate - Callback after action completion
 * @param {Object} api - API instance for making requests
 */
export const IssueActionsDropdown = ({ issue, workers, onUpdate, api }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [activeSubmenu, setActiveSubmenu] = useState(null)
  const [loading, setLoading] = useState(false)
  const [workerSearchQuery, setWorkerSearchQuery] = useState('')
  const dropdownRef = React.useRef(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false)
        setActiveSubmenu(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  /**
   * Handle worker reassignment
   */
  const handleReassign = async (workerId) => {
    setLoading(true)
    try {
      await api.post(`/admin/reassign?issue_id=${issue.id}&worker_id=${workerId}`)
      setIsOpen(false)
      setActiveSubmenu(null)
      onUpdate()
    } catch (err) {
      alert('Reassignment failed')
    }
    setLoading(false)
  }

  /**
   * Handle worker unassignment
   */
  const handleUnassign = async () => {
    setLoading(true)
    try {
      await api.post(`/admin/unassign?issue_id=${issue.id}`)
      setIsOpen(false)
      onUpdate()
    } catch (err) {
      alert('Unassignment failed')
    }
    setLoading(false)
  }

  /**
   * Handle status change
   */
  const handleStatusChange = async (newStatus) => {
    if (newStatus === issue.status) return
    setLoading(true)
    try {
      await api.post(`/admin/update-status?issue_id=${issue.id}&status=${newStatus}`)
      setIsOpen(false)
      setActiveSubmenu(null)
      onUpdate()
    } catch (err) {
      alert('Status update failed')
    }
    setLoading(false)
  }

  const handlePriorityChange = async (newPriority) => {
    if (newPriority === issue.priority) return
    setLoading(true)
    try {
      await api.post(`/admin/update-priority?issue_id=${issue.id}&priority=${newPriority}`)
      setIsOpen(false)
      setActiveSubmenu(null)
      onUpdate()
    } catch (err) {
      alert('Priority update failed')
    }
    setLoading(false)
  }

  const handleAssign = async (workerId) => {
    setLoading(true)
    try {
      await api.post(`/admin/assign?issue_id=${issue.id}&worker_id=${workerId}`)
      setIsOpen(false)
      setActiveSubmenu(null)
      onUpdate()
    } catch (err) {
      alert('Assignment failed')
    }
    setLoading(false)
  }

  const hasWorker = !!issue.worker_id

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Dropdown trigger button */}
      <button
        onClick={(e) => { 
          e.stopPropagation()
          setIsOpen(!isOpen)
          setActiveSubmenu(null)
        }}
        className="flex items-center justify-center w-8 h-8 bg-slate-100 text-slate-500 rounded-lg hover:bg-slate-200 hover:text-slate-700 transition-all"
      >
        <MoreVertical size={16} />
      </button>
      
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="absolute top-full right-0 mt-2 w-56 bg-white rounded-xl shadow-2xl border border-slate-100 z-[100] overflow-visible"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Assignment Section */}
            {!hasWorker ? (
              <AssignSection 
                workers={workers}
                onAssign={handleAssign}
                onHover={() => {
                  setActiveSubmenu('assign')
                  setWorkerSearchQuery('')
                }}
                onLeave={() => setActiveSubmenu(null)}
                isActive={activeSubmenu === 'assign'}
                loading={loading}
                searchQuery={workerSearchQuery}
                onSearchChange={setWorkerSearchQuery}
              />
            ) : (
              <ReassignSection
                workers={workers}
                currentWorkerId={issue.worker_id}
                onReassign={handleReassign}
                onUnassign={handleUnassign}
                onHoverReassign={() => {
                  setActiveSubmenu('reassign')
                  setWorkerSearchQuery('')
                }}
                onLeaveReassign={() => setActiveSubmenu(null)}
                isReassignActive={activeSubmenu === 'reassign'}
                loading={loading}
                searchQuery={workerSearchQuery}
                onSearchChange={setWorkerSearchQuery}
              />
            )}
            
            {/* Status Change Section */}
            <div className="border-t border-slate-100">
              <StatusSection
                currentStatus={issue.status}
                onStatusChange={handleStatusChange}
                onHover={() => setActiveSubmenu('status')}
                onLeave={() => setActiveSubmenu(null)}
                isActive={activeSubmenu === 'status'}
                loading={loading}
              />
            </div>

            {/* Priority Change Section */}
            <div className="border-t border-slate-100">
              <PrioritySection
                currentPriority={issue.priority}
                onPriorityChange={handlePriorityChange}
                onHover={() => setActiveSubmenu('priority')}
                onLeave={() => setActiveSubmenu(null)}
                isActive={activeSubmenu === 'priority'}
                loading={loading}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * AssignSection - Component for assigning a new worker
 */
const AssignSection = ({ workers, onAssign, onHover, onLeave, isActive, loading, searchQuery, onSearchChange }) => {
  const buttonRef = useRef(null)
  return (
    <div 
      className="relative"
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
    >
      <button ref={buttonRef} className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left">
        <div className="flex items-center gap-3">
          <UserPlus size={14} className="text-primary" />
          <span className="text-sm font-bold text-slate-700">Assign Worker</span>
        </div>
        <ChevronRight size={14} className="text-slate-400" />
      </button>
      
      <AnimatePresence>
        {isActive && (
          <WorkerSubmenu 
            workers={workers}
            onSelect={onAssign}
            loading={loading}
            title="Select Worker"
            searchQuery={searchQuery}
            onSearchChange={onSearchChange}
            parentRef={buttonRef}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * ReassignSection - Component for reassigning or unassigning
 */
const ReassignSection = ({ 
  workers, 
  currentWorkerId, 
  onReassign, 
  onUnassign,
  onHoverReassign,
  onLeaveReassign,
  isReassignActive,
  loading,
  searchQuery,
  onSearchChange
}) => {
  const buttonRef = useRef(null)
  return (
    <>
      <div 
        className="relative"
        onMouseEnter={onHoverReassign}
        onMouseLeave={onLeaveReassign}
      >
        <button ref={buttonRef} className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left">
          <div className="flex items-center gap-3">
            <UserPlus size={14} className="text-blue-500" />
            <span className="text-sm font-bold text-slate-700">Reassign Worker</span>
          </div>
          <ChevronRight size={14} className="text-slate-400" />
        </button>
        
        <AnimatePresence>
          {isReassignActive && (
            <WorkerSubmenu 
              workers={workers}
              onSelect={onReassign}
              loading={loading}
              title="Reassign to"
              currentWorkerId={currentWorkerId}
              searchQuery={searchQuery}
              onSearchChange={onSearchChange}
              parentRef={buttonRef}
            />
          )}
        </AnimatePresence>
      </div>
      
      <button 
      onClick={onUnassign}
      disabled={loading}
      className="w-full px-4 py-3 flex items-center gap-3 hover:bg-red-50 transition-colors text-left disabled:opacity-50"
    >
      <UserMinus size={14} className="text-red-500" />
      <span className="text-sm font-bold text-red-600">Unassign Worker</span>
    </button>
  </>
  )
}

const StatusSection = ({ 
  currentStatus, 
  onStatusChange,
  onHover,
  onLeave,
  isActive,
  loading 
}) => (
  <div 
    className="relative"
    onMouseEnter={onHover}
    onMouseLeave={onLeave}
  >
    <button className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left">
      <div className="flex items-center gap-3">
        <ArrowRight size={14} className="text-slate-500" />
        <span className="text-sm font-bold text-slate-700">Move to Status</span>
      </div>
      <ChevronRight size={14} className="text-slate-400" />
    </button>
    
    <AnimatePresence>
      {isActive && (
        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 10 }}
          className="absolute right-full top-0 mr-1 w-48 bg-white rounded-xl shadow-2xl border border-slate-100 overflow-hidden"
          style={{ zIndex: 9999 }}
        >
          <div className="p-3 border-b border-slate-100 bg-slate-50">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Change Status</p>
          </div>
          <div className="py-1">
            {KANBAN_STATUSES.map(status => (
              <button
                key={status.value}
                onClick={() => onStatusChange(status.value)}
                disabled={loading || status.value === currentStatus}
                className={cn(
                  "w-full px-4 py-2.5 flex items-center gap-3 hover:bg-slate-50 transition-colors disabled:opacity-50 text-left",
                  status.value === currentStatus && "bg-primary/5"
                )}
              >
                <div className={cn("w-2 h-2 rounded-full", status.color)}></div>
                <span className="text-sm font-medium text-slate-700">{status.label}</span>
              </button>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  </div>
)

const PrioritySection = ({ 
  currentPriority, 
  onPriorityChange,
  onHover,
  onLeave,
  isActive,
  loading 
}) => (
  <div 
    className="relative"
    onMouseEnter={onHover}
    onMouseLeave={onLeave}
  >
    <button className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left">
      <div className="flex items-center gap-3">
        <Flag size={14} className="text-amber-500" />
        <span className="text-sm font-bold text-slate-700">Change Priority</span>
      </div>
      <ChevronRight size={14} className="text-slate-400" />
    </button>
    
    <AnimatePresence>
      {isActive && (
        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 10 }}
          className="absolute right-full top-0 mr-1 w-48 bg-white rounded-xl shadow-2xl border border-slate-100 overflow-hidden"
          style={{ zIndex: 9999 }}
        >
          <div className="p-3 border-b border-slate-100 bg-slate-50">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Set Priority</p>
          </div>
          <div className="py-1">
            {PRIORITIES.map(priority => (
              <button
                key={priority.value}
                onClick={() => onPriorityChange(priority.value)}
                disabled={loading || priority.value === currentPriority}
                className={cn(
                  "w-full px-4 py-2.5 flex items-center gap-3 hover:bg-slate-50 transition-colors disabled:opacity-50 text-left",
                  priority.value === currentPriority && "bg-primary/5"
                )}
              >
                <div className={cn("w-2 h-2 rounded-full", priority.color)}></div>
                <span className="text-sm font-medium text-slate-700">{priority.label}</span>
              </button>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  </div>
)

const WorkerSubmenu = ({ workers, onSelect, loading, title, currentWorkerId, searchQuery, onSearchChange, parentRef }) => {
  const filteredWorkers = workers.filter(worker => {
    const query = searchQuery.toLowerCase()
    const name = (worker.full_name || '').toLowerCase()
    const email = (worker.email || '').toLowerCase()
    return name.includes(query) || email.includes(query)
  })

  const [position, setPosition] = useState({ top: 0, left: 0 })
  const submenuRef = useRef(null)

  useEffect(() => {
    if (parentRef?.current) {
      const rect = parentRef.current.getBoundingClientRect()
      const submenuWidth = 288
      let left = rect.left - submenuWidth - 4
      if (left < 10) {
        left = rect.right + 4
      }
      setPosition({
        top: rect.top,
        left: left
      })
    }
  }, [parentRef])

  return createPortal(
    <motion.div
      ref={submenuRef}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="fixed w-72 bg-white rounded-xl shadow-2xl border border-slate-100 overflow-hidden"
      style={{ 
        zIndex: 99999,
        top: position.top,
        left: position.left
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="p-3 border-b border-slate-100 bg-slate-50">
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{title}</p>
      </div>
      
      <div className="p-2 border-b border-slate-100">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search workers..."
            className="w-full pl-9 pr-8 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
            onClick={(e) => e.stopPropagation()}
          />
          {searchQuery && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onSearchChange('')
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 flex items-center justify-center text-slate-400 hover:text-slate-600"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>
      
      <div className="max-h-64 overflow-y-auto">
        {filteredWorkers.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-slate-400">No workers found</p>
            {searchQuery && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onSearchChange('')
                }}
                className="mt-2 text-xs text-primary hover:underline"
              >
                Clear search
              </button>
            )}
          </div>
        ) : (
          filteredWorkers.map(worker => (
            <button
              key={worker.id}
              onClick={() => onSelect(worker.id)}
              disabled={loading || worker.id === currentWorkerId}
              className={cn(
                "w-full px-4 py-2.5 flex items-center justify-between hover:bg-slate-50 transition-colors disabled:opacity-50",
                worker.id === currentWorkerId && "bg-primary/5"
              )}
            >
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 bg-primary/10 rounded-lg flex items-center justify-center text-primary font-black text-[10px]">
                  {worker.full_name?.[0] || 'W'}
                </div>
                <div className="text-left">
                  <span className="text-sm font-medium text-slate-700 block truncate max-w-[140px]">
                    {worker.full_name || worker.email}
                  </span>
                  {worker.full_name && (
                    <span className="text-[10px] text-slate-400 truncate max-w-[140px] block">
                      {worker.email}
                    </span>
                  )}
                </div>
              </div>
              {worker.id === currentWorkerId ? (
                <span className="text-[9px] font-black text-primary uppercase">Current</span>
              ) : (
                <span className={cn(
                  "px-1.5 py-0.5 rounded text-[9px] font-black",
                  worker.active_task_count === 0 ? "bg-emerald-50 text-emerald-600" :
                  worker.active_task_count <= 2 ? "bg-blue-50 text-blue-600" :
                  "bg-amber-50 text-amber-600"
                )}>
                  {worker.active_task_count}
                </span>
              )}
            </button>
          ))
        )}
      </div>
      
      {searchQuery && filteredWorkers.length > 0 && (
        <div className="px-3 py-1.5 border-t border-slate-100 bg-slate-50/50">
          <p className="text-[10px] text-slate-400">
            Showing {filteredWorkers.length} of {workers.length} workers
          </p>
        </div>
      )}
    </motion.div>,
    document.body
  )
}

export default IssueActionsDropdown
