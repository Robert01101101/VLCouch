import { useCallback, useEffect, useRef, useState } from 'react'

import { fetchPlaybackSession } from './api'

/** Poll session position for UI; reload page data less often. */
export const PLAYBACK_SESSION_POLL_MS = 3000

/** Slightly slower than backend PLAYBACK_POLL_INTERVAL_SECONDS (5s). */
export const PLAYBACK_REFRESH_MS = 8000

export function episodeOnShow(show, episodeId) {
  if (!show || episodeId == null) return false
  for (const season of show.seasons || []) {
    for (const ep of season.episodes || []) {
      if (ep.id === episodeId) return true
    }
  }
  return false
}

export function sessionAppliesToShow(session, show) {
  if (!session?.active) return false
  if (session.current_item_type === 'movie') return false
  return episodeOnShow(show, session.current_item_id)
}

export function sessionPlayingEpisodeId(session) {
  if (!session?.active || session.current_item_type !== 'episode') return null
  return session.current_item_id
}

export function sessionProgressPercent(session) {
  if (!session?.active) return null
  if (session.progress_percent != null) return session.progress_percent
  const position = session.position_seconds
  const duration = session.duration_seconds
  if (position == null || duration == null || duration <= 0) return null
  return Math.min(100, Math.round((position / duration) * 1000) / 10)
}

/**
 * Refresh page data while VLC playback is tracked, and once when a session ends.
 * No polling when idle — keeps network use low.
 */
export function usePlaybackRefresh(reload, { enabled = true, shouldRefresh, kick = 0 } = {}) {
  const [session, setSession] = useState({ active: false })
  const reloading = useRef(false)
  const wasTracking = useRef(false)
  const reloadRef = useRef(reload)
  const shouldRefreshRef = useRef(shouldRefresh)

  reloadRef.current = reload
  shouldRefreshRef.current = shouldRefresh

  const matches = useCallback((session) => {
    const fn = shouldRefreshRef.current
    return typeof fn === 'function' ? fn(session) : true
  }, [])

  useEffect(() => {
    if (!enabled) {
      setSession({ active: false })
      return undefined
    }

    let cancelled = false
    let sessionIntervalId = null
    let reloadIntervalId = null

    async function reloadIfNeeded(session) {
      const tracking = Boolean(session?.active && matches(session))
      if (!tracking && !wasTracking.current) return tracking

      if (reloading.current) return tracking

      reloading.current = true
      try {
        await reloadRef.current()
      } catch {
        // Keep current UI if a background refresh fails.
      } finally {
        reloading.current = false
      }
      return tracking
    }

    function clearIntervals() {
      if (sessionIntervalId) {
        clearInterval(sessionIntervalId)
        sessionIntervalId = null
      }
      if (reloadIntervalId) {
        clearInterval(reloadIntervalId)
        reloadIntervalId = null
      }
    }

    function startIntervals() {
      if (sessionIntervalId || reloadIntervalId) return
      sessionIntervalId = setInterval(() => {
        pollSession(false)
      }, PLAYBACK_SESSION_POLL_MS)
      reloadIntervalId = setInterval(() => {
        pollSession(true)
      }, PLAYBACK_REFRESH_MS)
    }

    async function pollSession(reloadShow) {
      if (cancelled) return
      try {
        const session = await fetchPlaybackSession()
        if (cancelled) return

        setSession(session ?? { active: false })

        const tracking = Boolean(session?.active && matches(session))
        const sessionEnded = wasTracking.current && !tracking

        if (reloadShow || sessionEnded) {
          await reloadIfNeeded(session)
        }

        wasTracking.current = tracking

        if (tracking) {
          startIntervals()
        } else {
          clearIntervals()
        }
      } catch {
        // Ignore transient session fetch errors.
      }
    }

    async function tick() {
      await pollSession(true)
    }

    function onVisible() {
      if (document.visibilityState === 'visible') tick()
    }

    tick()
    document.addEventListener('visibilitychange', onVisible)

    return () => {
      cancelled = true
      clearIntervals()
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [enabled, matches, kick])

  return session
}
