import { render } from '@testing-library/react'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

import { useAutoRefresh } from '../hooks/useAutoRefresh'


function TestHarness({ callback, options }) {
  useAutoRefresh(callback, options)
  return null
}


describe('useAutoRefresh', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('runs on mount and at the configured interval', () => {
    const callback = vi.fn()

    render(
      <TestHarness
        callback={callback}
        options={{ intervalMs: 5000, runOnMount: true }}
      />
    )

    expect(callback).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(5000)
    expect(callback).toHaveBeenCalledTimes(2)

    vi.advanceTimersByTime(10000)
    expect(callback).toHaveBeenCalledTimes(4)
  })

  it('refreshes immediately on window focus and visible tab restore when enabled', () => {
    const callback = vi.fn()

    render(
      <TestHarness
        callback={callback}
        options={{
          intervalMs: 30000,
          runOnMount: false,
          refreshOnFocus: true,
          refreshOnVisibility: true,
        }}
      />
    )

    expect(callback).not.toHaveBeenCalled()

    window.dispatchEvent(new Event('focus'))
    expect(callback).toHaveBeenCalledTimes(1)

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      value: 'visible',
    })
    document.dispatchEvent(new Event('visibilitychange'))
    expect(callback).toHaveBeenCalledTimes(2)
  })
})
