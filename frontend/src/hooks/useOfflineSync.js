import { useEffect } from 'react';
import api from '../services/api';
import { offlineService } from '../services/offline';

export const useOfflineSync = () => {
  useEffect(() => {
    const syncReports = async () => {
      if (!navigator.onLine) return;

      let reports = [];
      try {
        reports = await offlineService.getReports();
      } catch (e) {
        console.error("IndexedDB not ready");
        return;
      }
      
      if (reports.length === 0) return;

      console.log(`Syncing ${reports.length} offline reports...`);

      for (const report of reports) {
        const formData = new FormData();
        formData.append('category_id', report.category_id);
        formData.append('lat', report.lat);
        formData.append('lng', report.lng);
        formData.append('reporter_email', report.reporter_email);
        formData.append('photo', report.photo);
        formData.append('description', report.description || '');

        try {
          await api.post('/issues/report', formData);
          await offlineService.removeReport(report.id);
          console.log(`Report ${report.id} synced successfully.`);
        } catch (err) {
          console.error(`Failed to sync report ${report.id}:`, err);
        }
      }
    };

    window.addEventListener('online', syncReports);
    // Initial check
    syncReports();

    return () => window.removeEventListener('online', syncReports);
  }, []);
};
