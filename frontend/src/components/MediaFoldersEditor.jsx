import { useState } from 'react'
import { pickMediaFolder, updateMediaRoots } from '../api'

const TYPE_LABELS = {
  movies: 'Movies',
  tv: 'TV',
}

export default function MediaFoldersEditor({
  roots,
  onChange,
  browseTestIdPrefix = 'settings',
  listTestId = 'settings-media-folders',
}) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [manualPath, setManualPath] = useState('')
  const [manualType, setManualType] = useState('movies')

  async function persist(nextRoots) {
    setSaving(true)
    setError(null)
    try {
      const data = await updateMediaRoots(nextRoots)
      onChange(data.roots)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleBrowse(type) {
    setError(null)
    try {
      const result = await pickMediaFolder()
      if (result.cancelled || !result.path) {
        return
      }
      const nextRoots = [...roots, { path: result.path, type }]
      await persist(nextRoots)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleRemove(index) {
    const nextRoots = roots.filter((_, i) => i !== index)
    await persist(nextRoots)
  }

  async function handleManualAdd(event) {
    event.preventDefault()
    const path = manualPath.trim()
    if (!path) {
      return
    }
    const nextRoots = [...roots, { path, type: manualType }]
    setManualPath('')
    await persist(nextRoots)
  }

  return (
    <div data-testid={listTestId}>
      {roots.length === 0 ? (
        <p className="text-sm text-gray-400" data-testid={`${browseTestIdPrefix}-media-folders-empty`}>
          No media folders configured yet.
        </p>
      ) : (
        <ul className="space-y-2">
          {roots.map((root, index) => (
            <li
              key={`${root.type}-${root.path}`}
              data-testid={`${browseTestIdPrefix}-media-root-${index}`}
              className="flex items-center justify-between gap-3 rounded border border-gray-700 bg-black/20 px-3 py-2"
            >
              <div className="min-w-0">
                <span className="mr-2 inline-block rounded bg-gray-700 px-2 py-0.5 text-xs font-medium text-gray-200">
                  {TYPE_LABELS[root.type] || root.type}
                </span>
                <span className="text-sm text-gray-200 break-all">{root.path}</span>
              </div>
              <button
                type="button"
                data-testid={`${browseTestIdPrefix}-remove-media-root-${index}`}
                onClick={() => handleRemove(index)}
                disabled={saving}
                className="shrink-0 text-sm text-gray-400 hover:text-white disabled:opacity-50"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          data-testid={`${browseTestIdPrefix}-add-movies-folder`}
          onClick={() => handleBrowse('movies')}
          disabled={saving}
          className="rounded bg-gray-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-600 disabled:opacity-50"
        >
          Browse for movies folder
        </button>
        <button
          type="button"
          data-testid={`${browseTestIdPrefix}-add-tv-folder`}
          onClick={() => handleBrowse('tv')}
          disabled={saving}
          className="rounded bg-gray-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-600 disabled:opacity-50"
        >
          Browse for TV folder
        </button>
      </div>

      <form onSubmit={handleManualAdd} className="mt-4 space-y-2">
        <label className="block text-sm text-gray-400" htmlFor={`${browseTestIdPrefix}-media-path-input`}>
          Or paste a folder path
        </label>
        <div className="flex flex-wrap gap-2">
          <select
            value={manualType}
            onChange={(e) => setManualType(e.target.value)}
            data-testid={`${browseTestIdPrefix}-media-type-select`}
            className="rounded border border-gray-700 bg-black/30 px-3 py-2 text-sm text-white"
          >
            <option value="movies">Movies</option>
            <option value="tv">TV</option>
          </select>
          <input
            id={`${browseTestIdPrefix}-media-path-input`}
            type="text"
            value={manualPath}
            onChange={(e) => setManualPath(e.target.value)}
            placeholder="D:\Movies"
            data-testid={`${browseTestIdPrefix}-media-path-input`}
            className="min-w-[16rem] flex-1 rounded border border-gray-700 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-gray-500"
          />
          <button
            type="submit"
            data-testid={`${browseTestIdPrefix}-media-path-add`}
            disabled={saving || !manualPath.trim()}
            className="rounded bg-gray-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-600 disabled:opacity-50"
          >
            Add folder
          </button>
        </div>
      </form>

      {saving && (
        <p className="mt-2 text-sm text-gray-400" data-testid={`${browseTestIdPrefix}-media-folders-saving`}>
          Saving...
        </p>
      )}
      {error && (
        <p className="mt-2 text-sm text-red-400" data-testid={`${browseTestIdPrefix}-media-folders-error`}>
          {error}
        </p>
      )}
    </div>
  )
}
