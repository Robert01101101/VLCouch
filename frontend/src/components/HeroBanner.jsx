import { useState } from 'react'
import { playItem } from '../api'

function formatEpisodeCode(season, episode) {
  return `S${String(season).padStart(2, '0')}E${String(episode).padStart(2, '0')}`
}

export default function HeroBanner({ hero, onPlayed }) {
  const [playing, setPlaying] = useState(false)

  if (!hero) return null

  const isEpisode = hero.item_type === 'episode'
  const headline = isEpisode ? hero.show_title : hero.title
  const subtitle = isEpisode
    ? `${formatEpisodeCode(hero.season, hero.episode)} — ${hero.episode_title || 'Episode'}`
    : hero.year
      ? `${hero.year}`
      : null
  const imageUrl = hero.thumbnail_url || hero.poster_url
  const description = hero.overview?.trim() || null

  async function handlePlay() {
    setPlaying(true)
    try {
      const itemType = isEpisode ? 'episode' : 'movie'
      const itemId = isEpisode ? (hero.episode_id ?? hero.id) : hero.id
      await playItem(itemType, itemId)
      onPlayed?.()
    } catch (e) {
      alert(e.message)
    } finally {
      setPlaying(false)
    }
  }

  return (
    <section
      data-testid="hero-banner"
      className="relative w-full h-[50vh] min-h-[320px] max-h-[720px] overflow-hidden bg-couch-gray"
    >
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={headline}
          className="absolute inset-0 w-full h-full object-cover object-center"
        />
      ) : (
        <div className="absolute inset-0 bg-couch-gray" />
      )}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: [
            'linear-gradient(to top, #141414 0%, rgb(20 20 20 / 0.6) 24%, rgb(20 20 20 / 0.22) 40%, rgb(20 20 20 / 0) 55%)',
            'linear-gradient(to top right, rgb(20 20 20 / 0.82) 0%, rgb(20 20 20 / 0.28) 32%, rgb(20 20 20 / 0) 58%)',
          ].join(', '),
        }}
      />

      <div className="relative h-full flex flex-col justify-end px-6 sm:px-12 lg:px-16 pb-10 sm:pb-14 max-w-3xl">
        <p className="text-sm font-medium text-gray-300 mb-2 drop-shadow">
          {isEpisode ? 'Continue Watching' : 'Watch Again'}
        </p>
        <h1 className="text-3xl sm:text-5xl font-bold mb-2 drop-shadow-lg leading-tight">
          {headline}
        </h1>
        {subtitle && (
          <p className="text-base sm:text-xl text-gray-200 mb-3 drop-shadow">{subtitle}</p>
        )}
        {description && (
          <p className="text-sm sm:text-base text-gray-300 mb-5 line-clamp-3 drop-shadow max-w-2xl">
            {description}
          </p>
        )}
        <div>
          <button
            data-testid="hero-play"
            onClick={handlePlay}
            disabled={playing}
            className="inline-flex items-center gap-2 bg-white hover:bg-white/90 text-black font-bold px-8 py-2.5 rounded transition-colors disabled:opacity-50"
          >
            <span aria-hidden="true">▶</span>
            {playing ? 'Playing...' : 'Play'}
          </button>
        </div>
      </div>
    </section>
  )
}
