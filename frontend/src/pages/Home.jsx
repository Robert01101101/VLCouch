import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import HeroBanner from '../components/HeroBanner'
import Row from '../components/Row'
import { fetchBrowse, playItem } from '../api'
import { browseMissingThumbnails, usePollForThumbnails } from '../thumbnailPolling'

export default function Home({ refreshKey = 0 }) {
  const location = useLocation()
  const [hero, setHero] = useState(null)
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function loadData() {
    try {
      setError(null)
      const data = await fetchBrowse()
      setHero(data.hero ?? null)
      setRows(data.rows || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const refreshThumbnails = useCallback(async () => {
    try {
      const data = await fetchBrowse()
      setHero(data.hero ?? null)
      setRows(data.rows || [])
    } catch {
      // Keep current content if a background poll fails.
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [refreshKey, location.key])

  usePollForThumbnails(
    !loading && browseMissingThumbnails({ hero, rows }),
    refreshThumbnails
  )

  async function handlePlayMovie(movie) {
    try {
      await playItem('movie', movie.id)
      await loadData()
    } catch (e) {
      alert(e.message)
    }
  }

  function rowProps(row) {
    if (row.item_type === 'movie') {
      return {
        getLink: undefined,
        onPlay: handlePlayMovie,
      }
    }
    if (row.item_type === 'show') {
      return {
        getLink: (item) => `/shows/${item.id}`,
        onPlay: undefined,
      }
    }
    return {
      getLink: (item) =>
        item.item_type === 'show' ? `/shows/${item.id}` : undefined,
      onPlay: (item) => {
        if (item.item_type === 'movie') handlePlayMovie(item)
      },
    }
  }

  const hasContent = hero || rows.some((row) => row.items?.length > 0)

  if (loading) {
    return (
      <div className="text-center py-20 text-gray-400" data-testid="page-loading">
        Loading library...
      </div>
    )
  }

  return (
    <div className="pb-12">
      <HeroBanner hero={hero} onPlayed={loadData} />

      {error && (
        <div
          className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded mb-6 mx-6 max-w-7xl lg:mx-auto"
          data-testid="page-error"
        >
          {error}
        </div>
      )}

      {!hasContent && (
        <div className="text-center py-20 text-gray-400 px-6 max-w-7xl mx-auto" data-testid="page-empty">
          <p className="mb-2">No media found.</p>
          <p className="text-sm">Configure MEDIA_ROOTS in .env and rescan the library in Settings.</p>
        </div>
      )}

      <div className={hero ? 'relative z-10 pt-10' : 'pt-4'}>
        {rows.map((row) => {
          const props = rowProps(row)
          const subtitle =
            row.total && row.total > row.items.length
              ? `${row.items.length} of ${row.total}`
              : null
          return (
            <Row
              key={row.id}
              rowId={row.id}
              title={row.item_type === 'show' ? `[TV] ${row.title}` : row.title}
              subtitle={subtitle}
              items={row.items}
              getLink={props.getLink}
              onPlay={props.onPlay}
            />
          )
        })}
      </div>
    </div>
  )
}
