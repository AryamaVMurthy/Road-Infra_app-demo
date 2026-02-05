import { describe, it, expect, vi } from 'vitest';
import { offlineService } from '../services/offline';

// Simple mock for IndexedDB
const mockIndexedDB = {
    open: vi.fn().mockReturnValue({
        onupgradeneeded: null,
        onsuccess: null,
        onerror: null,
        result: {
            transaction: () => ({
                objectStore: () => ({
                    add: () => ({ onsuccess: null }),
                    getAll: () => ({ onsuccess: null }),
                    delete: () => ({ onsuccess: null })
                })
            }),
            objectStoreNames: { contains: () => true }
        }
    })
};

global.indexedDB = mockIndexedDB;

describe('offlineService', () => {
    it('initializes IndexedDB', async () => {
        // Since initializing real IDB in JSDOM is tricky, we verify the logic flow
        const initPromise = offlineService.init();
        const openRequest = mockIndexedDB.open.mock.results[0].value;
        if (openRequest.onsuccess) openRequest.onsuccess();
        
        const db = await initPromise;
        expect(db).toBeDefined();
    });
});
