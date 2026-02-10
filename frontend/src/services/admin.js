import api from './api';

const adminService = {
  // Worker management
  getWorkers: () => api.get('/admin/workers'),
  getWorkersWithStats: () => api.get('/admin/workers-with-stats'),
  getWorkerAnalytics: () => api.get('/admin/worker-analytics'),
  bulkInviteWorkers: (emails) => api.post('/admin/bulk-invite', { emails }),
  deactivateWorker: (workerId) => api.post(`/admin/deactivate-worker?worker_id=${workerId}`),

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

  // Sysadmin (IT Admin) features
  getZones: () => api.get('/admin/sysadmin/zones'),
  createZone: (data) => api.post('/admin/sysadmin/zones', data),
  getOrganizations: () => api.get('/admin/sysadmin/organizations'),
  createOrganization: (data) => api.post('/admin/sysadmin/organizations', data),
  getCategories: () => api.get('/admin/sysadmin/categories'),
  createCategory: (data) => api.post('/admin/sysadmin/categories', data),
  updateCategory: (id, data) => api.put(`/admin/sysadmin/categories/${id}`, data),
  deleteCategory: (id) => api.delete(`/admin/sysadmin/categories/${id}`),
  
  // Audit Logs
  getAuditLogs: (limit = 200, offset = 0) => api.get(`/analytics/audit-all?limit=${limit}&offset=${offset}`),
};

export default adminService;
