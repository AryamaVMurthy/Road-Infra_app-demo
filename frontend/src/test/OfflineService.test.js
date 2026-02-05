import { describe, it, expect, beforeEach, vi } from 'vitest'
import { offlineService } from '../services/offline'

const storeFactory = () => {
  const data = new Map()
  return {
    add: (value) => {
      const id = data.size + 1
      const record = { ...value, id }
      data.set(id, record)
      const request = { result: id, onsuccess: null, onerror: null }
      queueMicrotask(() => request.onsuccess?.())
      return request
    },
    getAll: () => {
      const request = { result: Array.from(data.values()), onsuccess: null, onerror: null }
      queueMicrotask(() => request.onsuccess?.())
      return request
    },
    delete: (id) => {
      data.delete(id)
      const request = { onsuccess: null, onerror: null }
      queueMicrotask(() => request.onsuccess?.())
      return request
    },
    get: (id) => {
      const request = { result: data.get(id), onsuccess: null, onerror: null }
      queueMicrotask(() => request.onsuccess?.())
      return request
    },
    put: (value) => {
      data.set(value.id, value)
      const request = { onsuccess: null, onerror: null }
      queueMicrotask(() => request.onsuccess?.())
      return request
    },
    createIndex: () => {},
  }
}

const createIndexedDbMock = () => {
  const stores = {
    offlineReports: storeFactory(),
    workerResolutions: storeFactory(),
  }

  const db = {
    objectStoreNames: {
      contains: (name) => Boolean(stores[name]),
    },
    createObjectStore: (name) => stores[name],
    transaction: (name) => ({ objectStore: () => stores[name] }),
  }

  return {
    open: () => {
      const request = { result: db, onsuccess: null, onerror: null, onupgradeneeded: null }
      queueMicrotask(() => {
        request.onupgradeneeded?.({ target: { result: db } })
        request.onsuccess?.()
      })
      return request
    },
  }
}

describe('offlineService', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    global.indexedDB = createIndexedDbMock()
    global.navigator = {
      serviceWorker: {
        ready: Promise.resolve({ sync: { register: vi.fn().mockResolvedValue(undefined) } }),
      },
    }
    global.window = { SyncManager: function () {} }
  })

  it('stores and retrieves offline reports', async () => {
    const id = await offlineService.saveReport({ title: 'Report 1' })
    const reports = await offlineService.getReports()

    expect(id).toBe(1)
    expect(reports).toHaveLength(1)
    expect(reports[0].title).toBe('Report 1')
  })

  it('stores and marks worker resolutions as synced', async () => {
    const id = await offlineService.saveResolution('issue-1', new Blob(['x']))
    let pending = await offlineService.getPendingResolutions()
    expect(pending).toHaveLength(1)

    await offlineService.markResolutionSynced(id)
    pending = await offlineService.getPendingResolutions()
    expect(pending).toHaveLength(0)
  })
})
