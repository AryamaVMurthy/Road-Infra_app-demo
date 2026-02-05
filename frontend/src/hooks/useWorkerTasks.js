import { useCallback, useEffect, useState } from 'react'
import api from '../services/api'

export const useWorkerTasks = (onError) => {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/worker/tasks')
      setTasks(res.data)
    } catch (err) {
      if (onError) {
        onError('Failed to fetch tasks')
      }
    }
    setLoading(false)
  }, [onError])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  return { tasks, setTasks, loading, fetchTasks }
}
