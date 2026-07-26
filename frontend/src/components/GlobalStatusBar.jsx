import { useEffect, useState } from 'react'
import { fetchScanStatus, fetchThumbnailStatus } from '../api'

const ACTIVE_POLL_MS = 2000
const IDLE_POLL_MS = 10000

export default function GlobalStatusBar() {
  const [scanRunning, setScanRunning] = useState(false)
  const [thumbnailsBusy, setThumbnailsBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    let timeoutId

    async function poll() {
      let active = false
      try {
        const [scan, thumbs] = await Promise.all([
          fetchScanStatus().catch(() => ({ running: false })),
          fetchThumbnailStatus().catch(() => ({ busy: false })),
        ])
        if (cancelled) return
        setScanRunning(Boolean(scan.running))
        setThumbnailsBusy(Boolean(thumbs.busy))
        active = Boolean(scan.running) || Boolean(thumbs.busy)
      } catch {
        // Keep polling on transient errors.
      }
      if (!cancelled) {
        timeoutId = setTimeout(poll, active ? ACTIVE_POLL_MS : IDLE_POLL_MS)
      }
    }

    poll()
    return () => {
      cancelled = true
      clearTimeout(timeoutId)
    }
  }, [])

  if (!scanRunning && !thumbnailsBusy) {
    return null
  }

  return (
    <div
      className="border-b border-gray-800 bg-black/40 px-6 py-2"
      data-testid="global-status-bar"
    >
      <div className="mx-auto flex max-w-[1920px] flex-wrap items-center gap-4 text-sm text-gray-300">
        {scanRunning && (
          <span className="flex items-center gap-2" data-testid="global-status-scanning">
            <span className="h-2 w-2 animate-pulse rounded-full bg-couch-red" aria-hidden="true" />
            Scanning library…
          </span>
        )}
        {thumbnailsBusy && (
          <span className="flex items-center gap-2" data-testid="global-status-thumbnails">
            <span className="h-2 w-2 animate-pulse rounded-full bg-couch-red" aria-hidden="true" />
            Generating thumbnails…
          </span>
        )}
      </div>
    </div>
  )
}
