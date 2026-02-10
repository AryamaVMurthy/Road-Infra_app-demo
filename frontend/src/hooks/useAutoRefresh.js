import { useEffect, useRef } from 'react'

export const useAutoRefresh = (
  callback,
  {
    intervalMs = 30000,
    enabled = true,
    runOnMount = true
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

    if (runOnMount) {
      callbackRef.current()
    }

    const intervalId = setInterval(() => {
      callbackRef.current()
    }, intervalMs)

    return () => clearInterval(intervalId)
  }, [enabled, intervalMs, runOnMount])
}
