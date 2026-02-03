const CACHE_NAME = 'urban-infra-v1';
const DB_NAME = 'UrbanInfraDB';
const RESOLUTIONS_STORE = 'workerResolutions';
const API_BASE = '/api/v1';

const STATIC_ASSETS = [
  '/',
  '/index.html',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) return;
  
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request).then((response) => {
        if (response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    }).catch(() => caches.match('/'))
  );
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-resolutions') {
    event.waitUntil(syncResolutions());
  }
});

async function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 2);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getPendingResolutions() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(RESOLUTIONS_STORE, 'readonly');
    const store = tx.objectStore(RESOLUTIONS_STORE);
    const request = store.getAll();
    request.onsuccess = () => {
      resolve(request.result.filter((r) => r.status === 'pending'));
    };
    request.onerror = () => reject(request.error);
  });
}

async function markSynced(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(RESOLUTIONS_STORE, 'readwrite');
    const store = tx.objectStore(RESOLUTIONS_STORE);
    const getReq = store.get(id);
    getReq.onsuccess = () => {
      const data = getReq.result;
      if (data) {
        data.status = 'synced';
        store.put(data);
      }
      resolve();
    };
    getReq.onerror = () => reject(getReq.error);
  });
}

async function removeResolution(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(RESOLUTIONS_STORE, 'readwrite');
    const store = tx.objectStore(RESOLUTIONS_STORE);
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function syncResolutions() {
  const resolutions = await getPendingResolutions();
  if (resolutions.length === 0) return;

  const db = await openDB();
  const token = await getAuthToken();

  for (const resolution of resolutions) {
    try {
      const formData = new FormData();
      formData.append('photo', resolution.photo, 'resolution.jpg');

      const response = await fetch(`${API_BASE}/worker/tasks/${resolution.issueId}/resolve`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (response.ok) {
        await removeResolution(db, resolution.id);
        notifyClients('resolution-synced', { issueId: resolution.issueId });
      } else if (response.status >= 400 && response.status < 500) {
        await removeResolution(db, resolution.id);
        notifyClients('resolution-failed', { issueId: resolution.issueId, error: 'Invalid request' });
      }
    } catch (err) {
      console.error('Sync failed for resolution:', resolution.id, err);
    }
  }
}

async function getAuthToken() {
  const clients = await self.clients.matchAll();
  for (const client of clients) {
    try {
      const response = await new Promise((resolve) => {
        const channel = new MessageChannel();
        channel.port1.onmessage = (e) => resolve(e.data);
        client.postMessage({ type: 'GET_AUTH_TOKEN' }, [channel.port2]);
        setTimeout(() => resolve(null), 1000);
      });
      if (response?.token) return response.token;
    } catch {}
  }
  return null;
}

function notifyClients(type, data) {
  self.clients.matchAll().then((clients) => {
    clients.forEach((client) => client.postMessage({ type, ...data }));
  });
}

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
