const DB_NAME = 'UrbanInfraDB';
const REPORTS_STORE = 'offlineReports';
const RESOLUTIONS_STORE = 'workerResolutions';
const DB_VERSION = 2;

let dbInstance = null;

export const offlineService = {
  init: () => {
    if (dbInstance) return Promise.resolve(dbInstance);
    
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      
      request.onupgradeneeded = (e) => {
        const db = e.target.result;
        // Citizen reports store
        if (!db.objectStoreNames.contains(REPORTS_STORE)) {
          db.createObjectStore(REPORTS_STORE, { keyPath: 'id', autoIncrement: true });
        }
        // Worker resolutions store
        if (!db.objectStoreNames.contains(RESOLUTIONS_STORE)) {
          const store = db.createObjectStore(RESOLUTIONS_STORE, { keyPath: 'id', autoIncrement: true });
          store.createIndex('issueId', 'issueId', { unique: false });
          store.createIndex('status', 'status', { unique: false });
        }
      };
      
      request.onsuccess = () => {
        dbInstance = request.result;
        resolve(dbInstance);
      };
      request.onerror = () => reject(request.error);
    });
  },

  // ============ CITIZEN REPORTS ============
  saveReport: async (reportData) => {
    const db = await offlineService.init();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(REPORTS_STORE, 'readwrite');
      const store = transaction.objectStore(REPORTS_STORE);
      const request = store.add(reportData);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  },

  getReports: async () => {
    const db = await offlineService.init();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(REPORTS_STORE, 'readonly');
      const store = transaction.objectStore(REPORTS_STORE);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  },

  removeReport: async (id) => {
    const db = await offlineService.init();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(REPORTS_STORE, 'readwrite');
      const store = transaction.objectStore(REPORTS_STORE);
      const request = store.delete(id);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  },

  // ============ WORKER RESOLUTIONS ============
  saveResolution: async (issueId, photoBlob, taskData = {}) => {
    const db = await offlineService.init();
    const resolution = {
      issueId,
      photo: photoBlob,
      timestamp: new Date().toISOString(),
      status: 'pending',
      taskData, // category_name, priority, etc. for optimistic UI
    };
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(RESOLUTIONS_STORE, 'readwrite');
      const store = transaction.objectStore(RESOLUTIONS_STORE);
      const request = store.add(resolution);
      request.onsuccess = () => {
        // Try to register background sync
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
          navigator.serviceWorker.ready.then(sw => {
            sw.sync.register('sync-resolutions').catch(console.error);
          });
        }
        resolve(request.result);
      };
      request.onerror = () => reject(request.error);
    });
  },

  getResolutions: async (status = null) => {
    const db = await offlineService.init();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(RESOLUTIONS_STORE, 'readonly');
      const store = transaction.objectStore(RESOLUTIONS_STORE);
      const request = store.getAll();
      request.onsuccess = () => {
        let results = request.result;
        if (status) {
          results = results.filter(r => r.status === status);
        }
        resolve(results);
      };
      request.onerror = () => reject(request.error);
    });
  },

  getPendingResolutions: async () => {
    return offlineService.getResolutions('pending');
  },

  markResolutionSynced: async (id) => {
    const db = await offlineService.init();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(RESOLUTIONS_STORE, 'readwrite');
      const store = transaction.objectStore(RESOLUTIONS_STORE);
      const getRequest = store.get(id);
      
      getRequest.onsuccess = () => {
        const data = getRequest.result;
        if (data) {
          data.status = 'synced';
          const putRequest = store.put(data);
          putRequest.onsuccess = () => resolve();
          putRequest.onerror = () => reject(putRequest.error);
        } else {
          resolve();
        }
      };
      getRequest.onerror = () => reject(getRequest.error);
    });
  },

  removeResolution: async (id) => {
    const db = await offlineService.init();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(RESOLUTIONS_STORE, 'readwrite');
      const store = transaction.objectStore(RESOLUTIONS_STORE);
      const request = store.delete(id);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  },

  // Check if an issue has a pending offline resolution
  hasPendingResolution: async (issueId) => {
    const pending = await offlineService.getPendingResolutions();
    return pending.some(r => r.issueId === issueId);
  },
};
