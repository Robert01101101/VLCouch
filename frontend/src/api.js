const API_BASE = ''
const BROWSE_SESSION_KEY = 'vlcouch-browse-session'

export function getBrowseSessionId() {
  if (typeof sessionStorage === 'undefined') {
    return ''
  }
  let id = sessionStorage.getItem(BROWSE_SESSION_KEY)
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem(BROWSE_SESSION_KEY, id)
  }
  return id
}

export async function fetchBrowse() {
  const params = new URLSearchParams({ browse_session: getBrowseSessionId() })
  const res = await fetch(`${API_BASE}/api/browse?${params}`)
  if (!res.ok) throw new Error('Failed to fetch browse data')
  return res.json()
}

export async function searchLibrary(query) {
  const params = new URLSearchParams({ q: query })
  const res = await fetch(`${API_BASE}/api/search?${params}`)
  if (!res.ok) throw new Error('Failed to search library')
  return res.json()
}

export async function fetchMovies() {
  const res = await fetch(`${API_BASE}/api/movies`)
  if (!res.ok) throw new Error('Failed to fetch movies')
  return res.json()
}

export async function fetchShows() {
  const res = await fetch(`${API_BASE}/api/shows`)
  if (!res.ok) throw new Error('Failed to fetch shows')
  return res.json()
}

export async function fetchShow(id) {
  const res = await fetch(`${API_BASE}/api/shows/${id}`)
  if (!res.ok) throw new Error('Failed to fetch show')
  return res.json()
}

export async function fetchContinueWatching() {
  const res = await fetch(`${API_BASE}/api/continue-watching`)
  if (!res.ok) throw new Error('Failed to fetch continue watching')
  return res.json()
}

export async function playItem(itemType, itemId, { fromStart = false } = {}) {
  const params = fromStart ? '?from_start=true' : ''
  const res = await fetch(`${API_BASE}/api/play/${itemType}/${itemId}${params}`, {
    method: 'POST',
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to play')
  }
  return res.json()
}

export async function fetchPlaybackSession() {
  const res = await fetch(`${API_BASE}/api/playback/session`)
  if (!res.ok) throw new Error('Failed to fetch playback session')
  return res.json()
}

export async function setWatchStatus(itemType, itemId, watched) {
  const res = await fetch(`${API_BASE}/api/watch-status/${itemType}/${itemId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ watched }),
  })
  if (!res.ok) throw new Error('Failed to update watch status')
  return res.json()
}

export async function setSeasonWatchStatus(showId, season, watched) {
  const res = await fetch(`${API_BASE}/api/shows/${showId}/seasons/${season}/watch-status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ watched }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const err = new Error(data.detail || 'Failed to update season watch status')
    err.status = res.status
    throw err
  }
  return res.json()
}

export async function setShowWatchStatus(showId, watched) {
  const res = await fetch(`${API_BASE}/api/shows/${showId}/watch-status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ watched }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const err = new Error(data.detail || 'Failed to update show watch status')
    err.status = res.status
    throw err
  }
  return res.json()
}

export async function triggerScan() {
  const res = await fetch(`${API_BASE}/api/scan`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to start scan')
  return res.json()
}

export async function fetchScanStatus() {
  const res = await fetch(`${API_BASE}/api/scan/status`)
  if (!res.ok) throw new Error('Failed to fetch scan status')
  return res.json()
}

/** Poll until background scan finishes (full library scans can take a while). */
export async function waitForScanComplete({
  pollMs = 2000,
  timeoutMs = 300000,
} = {}) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const status = await fetchScanStatus()
    if (!status.running) {
      return status
    }
    await new Promise((resolve) => setTimeout(resolve, pollMs))
  }
  throw new Error('Scan timed out')
}

export async function fetchSettings() {
  const res = await fetch(`${API_BASE}/api/settings`)
  if (!res.ok) throw new Error('Failed to fetch settings')
  return res.json()
}

export async function updateSettings(patch) {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  if (!res.ok) throw new Error('Failed to update settings')
  return res.json()
}

export async function fetchMediaRoots() {
  const res = await fetch(`${API_BASE}/api/media-roots`)
  if (!res.ok) throw new Error('Failed to fetch media folders')
  return res.json()
}

export async function updateMediaRoots(roots) {
  const res = await fetch(`${API_BASE}/api/media-roots`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ roots }),
  })
  if (!res.ok) throw new Error('Failed to update media folders')
  return res.json()
}

export async function pickMediaFolder() {
  const res = await fetch(`${API_BASE}/api/media-roots/pick-folder`, {
    method: 'POST',
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to open folder picker')
  }
  return res.json()
}
