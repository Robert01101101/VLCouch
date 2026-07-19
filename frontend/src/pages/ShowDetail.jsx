import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchShow, openShowFolder, playItem, setSeasonWatchStatus, setShowWatchStatus, setWatchStatus } from '../api'
import { sessionAppliesToShow, sessionPlayingEpisodeId, sessionProgressPercent, usePlaybackRefresh } from '../playbackRefresh'
import { showMissingThumbnails, usePollForThumbnails } from '../thumbnailPolling'

export default function ShowDetail() {
  const { id } = useParams()
  const [show, setShow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [seasonUpdating, setSeasonUpdating] = useState(null)
  const [showUpdating, setShowUpdating] = useState(false)
  const [expandedSeasons, setExpandedSeasons] = useState({})
  const [playbackKick, setPlaybackKick] = useState(0)
  const [openingFolder, setOpeningFolder] = useState(false)
  const showRef = useRef(show)
  showRef.current = show

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

  const refreshThumbnails = useCallback(async () => {
    try {
      const data = await fetchShow(id)
      setShow(data)
    } catch {
      // Keep current content if a background poll fails.
    }
  }, [id])

  const shouldRefreshPlayback = useCallback(
    (session) => sessionAppliesToShow(session, showRef.current),
    []
  )

  useEffect(() => {
    setLoading(true)
    loadShow()
  }, [id])

  usePollForThumbnails(!loading && showMissingThumbnails(show), refreshThumbnails)

  const playbackSession = usePlaybackRefresh(refreshThumbnails, {
    enabled: !loading && Boolean(show),
    shouldRefresh: shouldRefreshPlayback,
    kick: playbackKick,
  })

  const playingEpisodeId = sessionPlayingEpisodeId(playbackSession)
  const playingProgressPercent = sessionProgressPercent(playbackSession)

  async function handleOpenFolder() {
    setOpeningFolder(true)
    try {
      await openShowFolder(show.id)
    } catch (e) {
      alert(e.message)
    } finally {
      setOpeningFolder(false)
    }
  }

  async function handlePlay(episodeId) {
    try {
      await playItem('episode', episodeId)
      setPlaybackKick((k) => k + 1)
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

  async function handleShowWatchStatus(watched) {
    setShowUpdating(true)
    try {
      try {
        await setShowWatchStatus(show.id, watched)
      } catch (e) {
        if (e.status !== 404 && e.status !== 405) throw e
        await Promise.all(
          show.seasons.map((season) =>
            setSeasonWatchStatus(show.id, season.season, watched).catch(async (seasonError) => {
              if (seasonError.status !== 404 && seasonError.status !== 405) throw seasonError
              await Promise.all(
                season.episodes.map((ep) => setWatchStatus('episode', ep.id, watched))
              )
            })
          )
        )
      }
      await loadShow()
    } catch (e) {
      alert(e.message)
    } finally {
      setShowUpdating(false)
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
    let inProgress = null
    for (const season of show.seasons) {
      for (const ep of season.episodes) {
        if (!ep.watched && (ep.position_seconds ?? 0) >= 30) {
          if (
            !inProgress
            || (ep.progress_percent ?? 0) > (inProgress.progress_percent ?? 0)
          ) {
            inProgress = ep
          }
        }
      }
    }
    if (inProgress) return inProgress
    for (const season of show.seasons) {
      for (const ep of season.episodes) {
        if (!ep.watched) return ep
      }
    }
    return null
  }

  function episodePlayLabel(ep) {
    if ((ep.position_seconds ?? 0) >= 30) {
      return `Resume S${String(ep.season).padStart(2, '0')}E${String(ep.episode).padStart(2, '0')}`
    }
    return `Play S${String(ep.season).padStart(2, '0')}E${String(ep.episode).padStart(2, '0')}`
  }

  // Initialize expanded state for seasons
  useEffect(() => {
    if (show && show.seasons) {
      const initialExpanded = {}
      show.seasons.forEach(season => {
        // Default to collapsed if all episodes are watched, otherwise expanded
        const allWatched = season.episodes.every(ep => ep.watched)
        initialExpanded[season.season] = !allWatched
      })
      setExpandedSeasons(initialExpanded)
    }
  }, [show])

  function toggleSeason(seasonNumber) {
    setExpandedSeasons(prev => ({
      ...prev,
      [seasonNumber]: !prev[seasonNumber]
    }))
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
          <div className="mt-6 flex flex-wrap items-center gap-2">
            {upNext && (
              <button
                data-testid="play-up-next"
                onClick={() => handlePlay(upNext.id)}
                className="bg-couch-red hover:bg-couch-red-dark text-white font-semibold px-6 py-2 rounded transition-colors"
              >
                {episodePlayLabel(upNext)}
              </button>
            )}
            {show.media_folder && (
              <button
                type="button"
                data-testid="open-show-folder"
                disabled={openingFolder}
                onClick={handleOpenFolder}
                className="text-sm text-gray-300 hover:text-white border border-gray-600 hover:border-gray-400 px-4 py-2 rounded transition-colors disabled:opacity-50"
              >
                Open folder
              </button>
            )}
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <button
                type="button"
                data-testid="mark-show-watched"
                disabled={showUpdating}
                onClick={() => handleShowWatchStatus(true)}
                className="text-sm text-gray-300 hover:text-white border border-gray-600 hover:border-gray-400 px-4 py-2 rounded transition-colors disabled:opacity-50"
              >
                Mark all watched
              </button>
              <button
                type="button"
                data-testid="mark-show-unwatched"
                disabled={showUpdating}
                onClick={() => handleShowWatchStatus(false)}
                className="text-sm text-gray-300 hover:text-white border border-gray-600 hover:border-gray-400 px-4 py-2 rounded transition-colors disabled:opacity-50"
              >
                Mark all unwatched
              </button>
            </div>
          </div>
        </div>
      </div>

      {show.seasons.map((season) => (
        <section key={season.season} className="mb-8">
          <div 
            className="flex flex-wrap items-center justify-between gap-3 mb-3 cursor-pointer"
            onClick={() => toggleSeason(season.season)}
          >
            <div className="flex items-center gap-2">
              <svg 
                className={`w-4 h-4 transition-transform ${expandedSeasons[season.season] ? 'rotate-90' : ''}`}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M9 18l6-6-6-6" />
              </svg>
              <h2 className="text-lg font-semibold text-gray-300">
                Season {season.season}
              </h2>
            </div>
            {expandedSeasons[season.season] && (
              <div className="flex gap-2">
                <button
                  type="button"
                  data-testid={`mark-season-${season.season}-watched`}
                  disabled={seasonUpdating === season.season}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleSeasonWatchStatus(season, true)
                  }}
                  className="text-xs text-gray-300 hover:text-white border border-gray-600 hover:border-gray-400 px-3 py-1 rounded transition-colors disabled:opacity-50 opacity-70"
                >
                  Mark watched
                </button>
                <button
                  type="button"
                  data-testid={`mark-season-${season.season}-unwatched`}
                  disabled={seasonUpdating === season.season}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleSeasonWatchStatus(season, false)
                  }}
                  className="text-xs text-gray-300 hover:text-white border border-gray-600 hover:border-gray-400 px-3 py-1 rounded transition-colors disabled:opacity-50 opacity-70"
                >
                  Mark unwatched
                </button>
              </div>
            )}
          </div>
          {expandedSeasons[season.season] && (
            <div className="space-y-2">
              {season.episodes.map((ep) => {
                const isPlaying = playingEpisodeId === ep.id
                const isUpNext = upNext && upNext.id === ep.id
                const showRing = isPlaying || (Boolean(isUpNext) && playingEpisodeId == null)
                const showProgress =
                  isPlaying ||
                  (ep.progress_percent != null && ep.progress_percent > 0 && !ep.watched)
                const progressWidth = Math.min(
                  100,
                  isPlaying
                    ? (playingProgressPercent ?? ep.progress_percent ?? 0)
                    : (ep.progress_percent ?? 0)
                )
                return (
                  <div
                    key={ep.id}
                    role="button"
                    tabIndex={0}
                    data-testid={`play-episode-${ep.id}`}
                    data-playing={isPlaying ? 'true' : undefined}
                    onClick={() => handlePlay(ep.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handlePlay(ep.id)
                      }
                    }}
                    className={`flex items-center gap-4 p-3 rounded-lg cursor-pointer ${
                      ep.watched && !isPlaying ? 'opacity-60' : ''
                    } ${
                      showRing
                        ? 'bg-couch-gray ring-1 ring-couch-red'
                        : 'bg-couch-gray/50'
                    }`}
                  >
                    <div className="w-16 flex-shrink-0">
                      {ep.thumbnail_url ? (
                        <img
                          src={ep.thumbnail_url}
                          alt="Episode thumbnail"
                          className="w-full h-9 object-cover rounded"
                        />
                      ) : (
                        <div className="bg-couch-gray/50 border border-dashed border-gray-600 w-full h-9 rounded flex items-center justify-center text-xs text-gray-500">
                          No thumbnail
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-mono text-gray-400 w-16 block">
                        S{String(ep.season).padStart(2, '0')}E{String(ep.episode).padStart(2, '0')}
                      </span>
                      <span className="text-sm block truncate">
                        {ep.title || `Episode ${ep.episode}`}
                        {ep.has_subtitles && (
                          <span className="ml-2 text-xs text-gray-500">CC</span>
                        )}
                      </span>
                      {showProgress && (
                        <div
                          className="mt-1 h-1 w-full max-w-xs rounded-full bg-gray-700 overflow-hidden"
                          data-testid={`episode-progress-${ep.id}`}
                        >
                          <div
                            className="h-full bg-couch-red"
                            style={{ width: `${progressWidth}%` }}
                          />
                        </div>
                      )}
                    </div>
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
          )}
        </section>
      ))}
    </div>
  )
}
