import { useEffect, useState, useCallback } from 'react';
import api from '../services/api';
import { offlineService } from '../services/offline';

export const useWorkerOfflineSync = (onSyncComplete) => {
  const [pendingCount, setPendingCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);

  const refreshPendingCount = useCallback(async () => {
    try {
      const pending = await offlineService.getPendingResolutions();
      setPendingCount(pending.length);
    } catch {
      setPendingCount(0);
    }
  }, []);

  const syncResolutions = useCallback(async () => {
    if (!navigator.onLine) return;

    let resolutions = [];
    try {
      resolutions = await offlineService.getPendingResolutions();
    } catch {
      return;
    }

    if (resolutions.length === 0) return;

    setIsSyncing(true);

    for (const resolution of resolutions) {
      const formData = new FormData();
      formData.append('photo', resolution.photo, 'resolution.jpg');

      try {
        await api.post(`/worker/tasks/${resolution.issueId}/resolve`, formData);
        await offlineService.removeResolution(resolution.id);
        if (onSyncComplete) onSyncComplete(resolution.issueId, true);
      } catch (err) {
        console.error(`Failed to sync resolution for issue ${resolution.issueId}:`, err);
        if (err.response?.status >= 400 && err.response?.status < 500) {
          await offlineService.removeResolution(resolution.id);
          if (onSyncComplete) onSyncComplete(resolution.issueId, false);
        }
      }
    }

    setIsSyncing(false);
    refreshPendingCount();
  }, [onSyncComplete, refreshPendingCount]);

  useEffect(() => {
    refreshPendingCount();

    const handleOnline = () => syncResolutions();
    window.addEventListener('online', handleOnline);

    const handleSWMessage = (event) => {
      if (event.data?.type === 'resolution-synced') {
        refreshPendingCount();
        if (onSyncComplete) onSyncComplete(event.data.issueId, true);
      } else if (event.data?.type === 'resolution-failed') {
        refreshPendingCount();
        if (onSyncComplete) onSyncComplete(event.data.issueId, false);
      } else if (event.data?.type === 'GET_AUTH_TOKEN') {
        const token = localStorage.getItem('auth_token');
        event.ports[0]?.postMessage({ token });
      }
    };
    navigator.serviceWorker?.addEventListener('message', handleSWMessage);

    if (navigator.onLine) {
      syncResolutions();
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      navigator.serviceWorker?.removeEventListener('message', handleSWMessage);
    };
  }, [syncResolutions, refreshPendingCount, onSyncComplete]);

  return { pendingCount, isSyncing, syncResolutions, refreshPendingCount };
};
