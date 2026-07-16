import { useEffect, useRef } from 'react'

const POLL_MS = 3000

export function browseMissingThumbnails({ hero, rows }) {
  if (hero && !hero.thumbnail_url && !hero.poster_url) return true
  for (const row of rows || []) {
    for (const item of row.items || []) {
      if (!item.poster_url) return true
    }
  }
  return false
}

export function showMissingThumbnails(show) {
  if (!show) return false
  if (!show.poster_url) return true
  for (const season of show.seasons || []) {
    for (const ep of season.episodes || []) {
      if (!ep.thumbnail_url) return true
    }
  }
  return false
}

export function usePollForThumbnails(needsPoll, reload) {
  const reloading = useRef(false)

  useEffect(() => {
    if (!needsPoll) return undefined

    const id = setInterval(async () => {
      if (reloading.current) return
      reloading.current = true
      try {
        await reload()
      } finally {
        reloading.current = false
      }
    }, POLL_MS)

    return () => clearInterval(id)
  }, [needsPoll, reload])
}
