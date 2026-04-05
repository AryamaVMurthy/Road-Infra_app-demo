import { useEffect, useRef } from 'react'

export const useAutoRefresh = (
  callback,
  {
    intervalMs = 30000,
    enabled = true,
    runOnMount = true,
    refreshOnFocus = false,
    refreshOnVisibility = false
  } = {}
) => {
  const callbackRef = useRef(callback)

  useEffect(() => {
    callbackRef.current = callback
  }, [callback])

  useEffect(() => {
    if (!enabled) {
      return undefined
    }

    const runRefresh = () => {
      callbackRef.current()
    }

    if (runOnMount) {
      runRefresh()
    }

    const intervalId = setInterval(() => {
      runRefresh()
    }, intervalMs)

    const handleFocus = () => {
      if (refreshOnFocus) {
        runRefresh()
      }
    }

    const handleVisibilityChange = () => {
      if (refreshOnVisibility && document.visibilityState === 'visible') {
        runRefresh()
      }
    }

    if (refreshOnFocus) {
      window.addEventListener('focus', handleFocus)
    }

    if (refreshOnVisibility) {
      document.addEventListener('visibilitychange', handleVisibilityChange)
    }

    return () => {
      clearInterval(intervalId)
      if (refreshOnFocus) {
        window.removeEventListener('focus', handleFocus)
      }
      if (refreshOnVisibility) {
        document.removeEventListener('visibilitychange', handleVisibilityChange)
      }
    }
  }, [enabled, intervalMs, refreshOnFocus, refreshOnVisibility, runOnMount])
}
