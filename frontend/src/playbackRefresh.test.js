import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'

import * as api from './api'
import {
  PLAYBACK_REFRESH_MS,
  episodeOnShow,
  sessionAppliesToShow,
  sessionPlayingEpisodeId,
  sessionProgressPercent,
  usePlaybackRefresh,
} from './playbackRefresh'

vi.mock('./api')

describe('playbackRefresh helpers', () => {
  it('episodeOnShow finds episode in nested seasons', () => {
    const show = {
      seasons: [{ episodes: [{ id: 10 }, { id: 11 }] }],
    }
    expect(episodeOnShow(show, 11)).toBe(true)
    expect(episodeOnShow(show, 99)).toBe(false)
  })

  it('sessionAppliesToShow matches episode on show', () => {
    const show = { seasons: [{ episodes: [{ id: 5 }] }] }
    expect(
      sessionAppliesToShow(
        { active: true, current_item_type: 'episode', current_item_id: 5 },
        show
      )
    ).toBe(true)
    expect(
      sessionAppliesToShow(
        { active: true, current_item_type: 'movie', current_item_id: 1 },
        show
      )
    ).toBe(false)
  })

  it('sessionPlayingEpisodeId returns episode id for active episode session', () => {
    expect(
      sessionPlayingEpisodeId({
        active: true,
        current_item_type: 'episode',
        current_item_id: 5,
      })
    ).toBe(5)
    expect(sessionPlayingEpisodeId({ active: false })).toBeNull()
    expect(
      sessionPlayingEpisodeId({
        active: true,
        current_item_type: 'movie',
        current_item_id: 1,
      })
    ).toBeNull()
  })

  it('sessionProgressPercent reads live session position', () => {
    expect(
      sessionProgressPercent({
        active: true,
        progress_percent: 92.4,
      })
    ).toBe(92.4)
    expect(
      sessionProgressPercent({
        active: true,
        position_seconds: 2700,
        duration_seconds: 3600,
      })
    ).toBe(75)
    expect(sessionProgressPercent({ active: false })).toBeNull()
  })
})

describe('usePlaybackRefresh', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    api.fetchPlaybackSession.mockResolvedValue({ active: false })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('does not reload when playback is idle', async () => {
    const reload = vi.fn()
    renderHook(() => usePlaybackRefresh(reload))

    await act(async () => {
      await Promise.resolve()
    })

    expect(reload).not.toHaveBeenCalled()
    expect(api.fetchPlaybackSession).toHaveBeenCalledTimes(1)

    await act(async () => {
      vi.advanceTimersByTime(PLAYBACK_REFRESH_MS * 2)
    })

    expect(reload).not.toHaveBeenCalled()
    expect(api.fetchPlaybackSession).toHaveBeenCalledTimes(1)
  })

  it('polls and reloads while a tracked session is active', async () => {
    const session = {
      active: true,
      current_item_type: 'episode',
      current_item_id: 10,
    }
    api.fetchPlaybackSession.mockResolvedValue(session)
    const reload = vi.fn().mockResolvedValue(undefined)

    const { result } = renderHook(() => usePlaybackRefresh(reload))

    await act(async () => {
      await Promise.resolve()
    })
    expect(reload).toHaveBeenCalledTimes(1)
    expect(result.current).toEqual(session)

    await act(async () => {
      vi.advanceTimersByTime(PLAYBACK_REFRESH_MS)
      await Promise.resolve()
    })
    expect(reload).toHaveBeenCalledTimes(2)
    expect(api.fetchPlaybackSession.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('reloads once when a tracked session ends', async () => {
    api.fetchPlaybackSession
      .mockResolvedValueOnce({
        active: true,
        current_item_type: 'episode',
        current_item_id: 10,
      })
      .mockResolvedValueOnce({ active: false })

    const reload = vi.fn().mockResolvedValue(undefined)
    renderHook(() => usePlaybackRefresh(reload))

    await act(async () => {
      await Promise.resolve()
    })
    expect(reload).toHaveBeenCalledTimes(1)

    await act(async () => {
      vi.advanceTimersByTime(PLAYBACK_REFRESH_MS)
      await Promise.resolve()
    })
    expect(reload).toHaveBeenCalledTimes(2)
  })

  it('respects shouldRefresh filter', async () => {
    api.fetchPlaybackSession.mockResolvedValue({
      active: true,
      current_item_type: 'episode',
      current_item_id: 99,
    })
    const reload = vi.fn()
    const shouldRefresh = vi.fn(() => false)

    renderHook(() => usePlaybackRefresh(reload, { shouldRefresh }))

    await act(async () => {
      await Promise.resolve()
    })

    expect(reload).not.toHaveBeenCalled()
    expect(shouldRefresh).toHaveBeenCalled()
  })

  it('re-checks session when kick increments after play', async () => {
    api.fetchPlaybackSession.mockResolvedValue({
      active: true,
      current_item_type: 'episode',
      current_item_id: 10,
    })
    const reload = vi.fn().mockResolvedValue(undefined)
    const { rerender } = renderHook(
      ({ kick }) => usePlaybackRefresh(reload, { kick }),
      { initialProps: { kick: 0 } }
    )

    await act(async () => {
      await Promise.resolve()
    })
    expect(reload).toHaveBeenCalledTimes(1)

    rerender({ kick: 1 })
    await act(async () => {
      await Promise.resolve()
    })
    expect(reload).toHaveBeenCalledTimes(2)
    expect(api.fetchPlaybackSession.mock.calls.length).toBeGreaterThanOrEqual(2)
  })
})
