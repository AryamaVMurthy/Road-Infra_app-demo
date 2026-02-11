import api from './api';

const adminService = {
  // Worker management
  getWorkers: () => api.get('/admin/workers'),
  getWorkersWithStats: () => api.get('/admin/workers-with-stats'),
  getWorkerAnalytics: () => api.get('/admin/worker-analytics'),
  bulkInviteWorkers: (emails) => api.post('/admin/bulk-invite', { emails }),
  deactivateWorker: (workerId) => api.post(`/admin/deactivate-worker?worker_id=${workerId}`),
  activateWorker: (workerId) => api.post(`/admin/activate-worker?worker_id=${workerId}`),

  // Issue management
  getIssues: () => api.get('/admin/issues'),
  updateIssueStatus: (issueId, status) => api.post(`/admin/update-status?issue_id=${issueId}&status=${status}`),
  updateIssuePriority: (issueId, priority) => api.post(`/admin/update-priority?issue_id=${issueId}&priority=${priority}`),
  approveIssue: (issueId) => api.post(`/admin/approve?issue_id=${issueId}`),
  rejectIssue: (issueId, reason) => api.post(`/admin/reject?issue_id=${issueId}&reason=${reason}`),
  assignWorker: (issueId, workerId) => api.post(`/admin/assign?issue_id=${issueId}&worker_id=${workerId}`),
  bulkAssign: (issueIds, workerId) => api.post('/admin/bulk-assign', { issue_ids: issueIds, worker_id: workerId }),

  // Dashboard
  getDashboardStats: () => api.get('/admin/dashboard-stats'),

  // System (IT Admin) features
  getAuthorities: () => api.get('/admin/authorities'),
  createAuthority: (data) => api.post('/admin/authorities', data),
  updateAuthority: (id, data) => api.put(`/admin/authorities/${id}`, data),
  deleteAuthority: (id) => api.delete(`/admin/authorities/${id}`),
  
  getIssueTypes: () => api.get('/admin/issue-types'),
  createIssueType: (data) => api.post('/admin/issue-types', data),
  updateIssueType: (id, data) => api.put(`/admin/issue-types/${id}`, data),
  deleteIssueType: (id) => api.delete(`/admin/issue-types/${id}`),
  
  createManualIssue: (data) => api.post('/admin/manual-issues', data),
  
  // Audit Logs
  getAuditLogs: (filters = {}) => {
      const query = new URLSearchParams()
      if (filters.action) query.append('action', filters.action)
      if (filters.startDate) query.append('start_date', filters.startDate)
      if (filters.endDate) query.append('end_date', filters.endDate)
      return api.get(`/analytics/audit-all?${query.toString()}`)
  },
};

export default adminService;
