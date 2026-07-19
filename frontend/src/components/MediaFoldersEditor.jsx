import { useState } from 'react'
import { pickMediaFolder, updateMediaRoots } from '../api'

const TYPE_ORDER = ['movies', 'tv']

const TYPE_LABELS = {
  movies: 'Movies',
  tv: 'TV',
}

function buildDisplayRows(roots) {
  const rows = []

  for (const type of TYPE_ORDER) {
    const matches = roots
      .map((root, index) => ({ root, index }))
      .filter(({ root }) => root.type === type)

    if (matches.length === 0) {
      rows.push({ type, root: null, index: null, showLabel: true })
      continue
    }

    matches.forEach(({ root, index }, matchIndex) => {
      rows.push({
        type,
        root,
        index,
        showLabel: matchIndex === 0,
      })
    })
  }

  return rows
}

export default function MediaFoldersEditor({
  roots,
  onChange,
  browseTestIdPrefix = 'settings',
  listTestId = 'settings-media-folders',
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [manualPath, setManualPath] = useState('')
  const [manualType, setManualType] = useState('movies')

  const displayRows = buildDisplayRows(roots)

  async function persist(nextRoots) {
    setBusy(true)
    setError(null)
    try {
      const data = await updateMediaRoots(nextRoots)
      onChange(data.roots)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function handlePick(type, index) {
    setError(null)
    try {
      const result = await pickMediaFolder()
      if (result.cancelled || !result.path) {
        return
      }

      let nextRoots
      if (index !== null) {
        nextRoots = roots.map((root, i) =>
          i === index ? { ...root, path: result.path } : root
        )
      } else {
        nextRoots = [...roots, { path: result.path, type }]
      }
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
      <ul className="space-y-2">
        {displayRows.map((row) => {
          const rowKey = row.index ?? `${row.type}-empty`
          const rowTestId =
            row.index !== null
              ? `${browseTestIdPrefix}-media-root-${row.index}`
              : `${browseTestIdPrefix}-media-row-${row.type}`

          return (
            <li
              key={rowKey}
              data-testid={rowTestId}
              className="flex items-start gap-3 rounded-md bg-black/20 px-3 py-2.5"
            >
              <div className="w-16 shrink-0 pt-0.5">
                {row.showLabel ? (
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                    {TYPE_LABELS[row.type]}
                  </p>
                ) : null}
              </div>

              <div className="min-w-0 flex-1">
                {row.root ? (
                  <button
                    type="button"
                    data-testid={`${rowTestId}-path`}
                    onClick={() => handlePick(row.type, row.index)}
                    disabled={busy}
                    className="text-left text-sm text-gray-200 break-all hover:text-white disabled:opacity-50"
                  >
                    {row.root.path}
                  </button>
                ) : (
                  <button
                    type="button"
                    data-testid={`${rowTestId}-choose`}
                    onClick={() => handlePick(row.type, null)}
                    disabled={busy}
                    className="text-sm text-couch-red hover:text-couch-red-light disabled:opacity-50"
                  >
                    Choose folder...
                  </button>
                )}
              </div>

              {row.root ? (
                <button
                  type="button"
                  data-testid={`${browseTestIdPrefix}-remove-media-root-${row.index}`}
                  onClick={() => handleRemove(row.index)}
                  disabled={busy}
                  className="shrink-0 text-sm text-gray-400 hover:text-white disabled:opacity-50"
                >
                  Remove
                </button>
              ) : (
                <span className="w-14 shrink-0" aria-hidden="true" />
              )}
            </li>
          )
        })}
      </ul>

      <details className="mt-3">
        <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-300">
          Paste folder path instead
        </summary>
        <form onSubmit={handleManualAdd} className="mt-2 flex flex-wrap gap-2">
          <select
            value={manualType}
            onChange={(e) => setManualType(e.target.value)}
            data-testid={`${browseTestIdPrefix}-media-type-select`}
            disabled={busy}
            className="rounded border border-gray-700 bg-black/30 px-3 py-2 text-sm text-white disabled:opacity-50"
          >
            <option value="movies">Movies</option>
            <option value="tv">TV</option>
          </select>
          <input
            type="text"
            value={manualPath}
            onChange={(e) => setManualPath(e.target.value)}
            placeholder="D:\Movies"
            data-testid={`${browseTestIdPrefix}-media-path-input`}
            disabled={busy}
            className="min-w-[16rem] flex-1 rounded border border-gray-700 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-gray-500 disabled:opacity-50"
          />
          <button
            type="submit"
            data-testid={`${browseTestIdPrefix}-media-path-add`}
            disabled={busy || !manualPath.trim()}
            className="rounded bg-gray-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-600 disabled:opacity-50"
          >
            Add
          </button>
        </form>
      </details>

      {error && (
        <p
          className="mt-2 text-sm text-red-400"
          data-testid={`${browseTestIdPrefix}-media-folders-error`}
        >
          {error}
        </p>
      )}
    </div>
  )
}
