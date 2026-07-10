import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { playItem, searchLibrary } from '../api'

export default function SearchBar() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setResults([])
      setOpen(false)
      return
    }

    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const data = await searchLibrary(trimmed)
        setResults(data.results || [])
        setOpen(true)
      } catch {
        setResults([])
        setOpen(false)
      } finally {
        setLoading(false)
      }
    }, 250)

    return () => clearTimeout(timer)
  }, [query])

  function handleBlur() {
    window.setTimeout(() => setOpen(false), 150)
  }

  async function handlePlayMovie(item) {
    try {
      await playItem('movie', item.id)
    } catch (e) {
      alert(e.message)
    }
  }

  return (
    <div className="relative w-full max-w-md">
      <input
        type="search"
        data-testid="library-search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        onBlur={handleBlur}
        placeholder="Search movies and shows..."
        className="w-full bg-couch-gray/80 border border-gray-600 rounded px-4 py-2 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-gray-400"
      />
      {open && (
        <div
          className="absolute top-full left-0 right-0 mt-2 bg-gray-900 border border-gray-700 rounded shadow-xl max-h-80 overflow-y-auto z-50"
          data-testid="search-results"
        >
          {loading && (
            <p className="px-4 py-3 text-sm text-gray-400">Searching...</p>
          )}
          {!loading && results.length === 0 && (
            <p className="px-4 py-3 text-sm text-gray-400">No results found.</p>
          )}
          {!loading &&
            results.map((item) => {
              const subtitle =
                item.item_type === 'movie'
                  ? item.year
                    ? `${item.year}`
                    : 'Movie'
                  : item.episode_count
                    ? `${item.episode_count} episodes`
                    : 'TV Show'
              const href =
                item.item_type === 'show' ? `/shows/${item.id}` : undefined

              const row = (
                <div className="px-4 py-3 hover:bg-gray-800 transition-colors">
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-gray-400">{subtitle}</p>
                </div>
              )

              if (href) {
                return (
                  <Link
                    key={`${item.item_type}-${item.id}`}
                    to={href}
                    data-testid={`search-result-${item.item_type}-${item.id}`}
                    onMouseDown={(e) => e.preventDefault()}
                  >
                    {row}
                  </Link>
                )
              }

              return (
                <button
                  key={`${item.item_type}-${item.id}`}
                  type="button"
                  data-testid={`search-result-${item.item_type}-${item.id}`}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handlePlayMovie(item)}
                  className="w-full text-left"
                >
                  {row}
                </button>
              )
            })}
        </div>
      )}
    </div>
  )
}
