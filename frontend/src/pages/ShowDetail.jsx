import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchShow, playItem, setSeasonWatchStatus, setWatchStatus } from '../api'

export default function ShowDetail() {
  const { id } = useParams()
  const [show, setShow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [seasonUpdating, setSeasonUpdating] = useState(null)

  async function loadShow() {
    try {
      setError(null)
      const data = await fetchShow(id)
      setShow(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadShow()
  }, [id])

  async function handlePlay(episodeId) {
    try {
      await playItem('episode', episodeId)
      await loadShow()
    } catch (e) {
      alert(e.message)
    }
  }

  async function handleToggleWatched(episode, watched) {
    try {
      await setWatchStatus('episode', episode.id, watched)
      await loadShow()
    } catch (e) {
      alert(e.message)
    }
  }

  async function handleSeasonWatchStatus(season, watched) {
    setSeasonUpdating(season.season)
    try {
      try {
        await setSeasonWatchStatus(show.id, season.season, watched)
      } catch (e) {
        if (e.status !== 404 && e.status !== 405) throw e
        await Promise.all(
          season.episodes.map((ep) => setWatchStatus('episode', ep.id, watched))
        )
      }
      await loadShow()
    } catch (e) {
      alert(e.message)
    } finally {
      setSeasonUpdating(null)
    }
  }

  function findUpNext() {
    if (!show) return null
    for (const season of show.seasons) {
      for (const ep of season.episodes) {
        if (!ep.watched) return ep
      }
    }
    return null
  }

  if (loading) {
    return (
      <div className="text-center py-20 text-gray-400" data-testid="page-loading">
        Loading...
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-red-400 text-center py-20" data-testid="page-error">
        {error}
      </div>
    )
  }

  if (!show) return null

  const upNext = findUpNext()

  return (
    <div data-testid="show-detail">
      <div className="flex gap-8 mb-10">
        <div className="w-48 flex-shrink-0">
          <div className="aspect-[2/3] rounded-md overflow-hidden bg-couch-gray">
            {show.poster_url ? (
              <img src={show.poster_url} alt={show.title} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center p-4 text-center text-gray-400">
                {show.title}
              </div>
            )}
          </div>
        </div>
        <div className="flex-1">
          <h1 className="text-3xl font-bold mb-2">{show.title}</h1>
          {show.category && (
            <p className="text-sm text-gray-400 mb-4">{show.category}</p>
          )}
          {show.overview && (
            <p className="text-gray-300 leading-relaxed max-w-2xl">{show.overview}</p>
          )}
          {upNext && (
            <button
              data-testid="play-up-next"
              onClick={() => handlePlay(upNext.id)}
              className="mt-6 bg-couch-red hover:bg-red-700 text-white font-semibold px-6 py-2 rounded transition-colors"
            >
              Play S{String(upNext.season).padStart(2, '0')}E{String(upNext.episode).padStart(2, '0')}
            </button>
          )}
        </div>
      </div>

      {show.seasons.map((season) => (
        <section key={season.season} className="mb-8">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <h2 className="text-lg font-semibold text-gray-300">
              Season {season.season}
            </h2>
            <div className="flex gap-2">
              <button
                type="button"
                data-testid={`mark-season-${season.season}-watched`}
                disabled={seasonUpdating === season.season}
                onClick={() => handleSeasonWatchStatus(season, true)}
                className="text-xs text-gray-300 hover:text-white border border-gray-600 hover:border-gray-400 px-3 py-1 rounded transition-colors disabled:opacity-50"
              >
                Mark all watched
              </button>
              <button
                type="button"
                data-testid={`mark-season-${season.season}-unwatched`}
                disabled={seasonUpdating === season.season}
                onClick={() => handleSeasonWatchStatus(season, false)}
                className="text-xs text-gray-300 hover:text-white border border-gray-600 hover:border-gray-400 px-3 py-1 rounded transition-colors disabled:opacity-50"
              >
                Mark all unwatched
              </button>
            </div>
          </div>
          <div className="space-y-2">
            {season.episodes.map((ep) => {
              const isUpNext = upNext && upNext.id === ep.id
              return (
                <div
                  key={ep.id}
                  role="button"
                  tabIndex={0}
                  data-testid={`play-episode-${ep.id}`}
                  onClick={() => handlePlay(ep.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handlePlay(ep.id)
                    }
                  }}
                  className={`flex items-center gap-4 p-3 rounded-lg cursor-pointer ${
                    ep.watched ? 'opacity-60' : ''
                  } ${
                    isUpNext ? 'bg-couch-gray ring-1 ring-couch-red' : 'bg-couch-gray/50'
                  }`}
                >
                  <span className="text-sm font-mono text-gray-400 w-16">
                    S{String(ep.season).padStart(2, '0')}E{String(ep.episode).padStart(2, '0')}
                  </span>
                  <span className="flex-1 text-sm">
                    {ep.title || `Episode ${ep.episode}`}
                    {ep.has_subtitles && (
                      <span className="ml-2 text-xs text-gray-500">CC</span>
                    )}
                  </span>
                  <label
                    className="cursor-pointer"
                    aria-label={ep.watched ? 'Mark as unwatched' : 'Mark as watched'}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      data-testid={`watched-episode-${ep.id}`}
                      checked={ep.watched}
                      onChange={(e) => {
                        e.stopPropagation()
                        handleToggleWatched(ep, e.target.checked)
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="sr-only peer"
                    />
                    <span
                      className={`flex h-5 w-5 items-center justify-center rounded border transition-colors ${
                        ep.watched
                          ? 'border-couch-red bg-couch-red text-white'
                          : 'border-gray-500 text-transparent hover:border-gray-400'
                      }`}
                      aria-hidden="true"
                    >
                      <svg viewBox="0 0 12 12" className="h-3 w-3 fill-current">
                        <path d="M4.5 9L1.5 6l1-1 2 2 4-4 1 1-5 5z" />
                      </svg>
                    </span>
                  </label>
                </div>
              )
            })}
          </div>
        </section>
      ))}
    </div>
  )
}
