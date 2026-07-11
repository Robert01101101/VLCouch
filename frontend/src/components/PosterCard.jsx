import { Link } from 'react-router-dom'

export default function PosterCard({ item, to, onPlay, testId }) {
  const title = item.title
  const subtitle = item.year
    ? `${item.year}`
    : item.episode_count
      ? `${item.episode_count} episodes`
      : null

  const cardTestId =
    testId || `poster-card-${item.item_type || 'item'}-${item.id}`

  const showProgress =
    item.watched_count != null &&
    item.total_episodes != null &&
    item.total_episodes > 0

  const progressPercent = showProgress
    ? Math.min(100, (item.watched_count / item.total_episodes) * 100)
    : 0

  const inner = (
    <div className="relative aspect-[2/3] rounded-md overflow-hidden bg-couch-gray shadow-lg">
      {item.poster_url ? (
        <img
          src={item.poster_url}
          alt={title}
          className="w-full h-full object-cover"
          loading="lazy"
        />
      ) : (
        <div className="w-full h-full bg-couch-gray" aria-hidden="true" />
      )}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/95 via-black/55 to-transparent px-3 pb-3 pt-14">
        <p className="text-sm font-semibold leading-snug line-clamp-2 drop-shadow-sm">{title}</p>
        {subtitle && <p className="text-xs text-gray-300 mt-1 drop-shadow-sm">{subtitle}</p>}
      </div>
      {showProgress && (
        <div
          className="absolute bottom-0 left-0 right-0 h-1 bg-black/70"
          data-testid={`${cardTestId}-progress`}
        >
          <div
            className="h-full bg-couch-red transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      )}
    </div>
  )

  const cardClass =
    'group relative flex-shrink-0 w-40 sm:w-48 transition-transform duration-200 hover:scale-105 hover:z-10 text-left'

  if (to) {
    return (
      <Link to={to} className={cardClass} data-testid={cardTestId}>
        {inner}
      </Link>
    )
  }

  if (onPlay) {
    return (
      <button
        type="button"
        data-testid={cardTestId}
        onClick={() => onPlay(item)}
        className={`${cardClass} cursor-pointer`}
      >
        {inner}
      </button>
    )
  }

  return (
    <div className={cardClass} data-testid={cardTestId}>
      {inner}
    </div>
  )
}
