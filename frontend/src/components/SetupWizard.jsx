import { Link } from 'react-router-dom'
import MediaFoldersEditor from './MediaFoldersEditor'

export default function SetupWizard({ roots, onRootsChange, scanning, onScan }) {
  const canScan = roots.length > 0

  return (
    <div
      data-testid="setup-wizard"
      className="mx-auto max-w-2xl rounded-lg border border-gray-800 bg-couch-gray/40 px-6 py-8 text-left"
    >
      <h2 className="text-2xl font-bold text-white mb-2">Welcome to VLCouch</h2>
      <p className="text-gray-400 mb-6">
        Point VLCouch at your movie and TV folders, then scan your library to get started.
      </p>

      <MediaFoldersEditor
        roots={roots}
        onChange={onRootsChange}
        browseTestIdPrefix="setup"
        listTestId="setup-media-folders"
      />

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          data-testid="setup-wizard-scan"
          onClick={onScan}
          disabled={!canScan || scanning}
          className="rounded bg-couch-red px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-couch-red-dark disabled:opacity-50"
        >
          {scanning ? 'Scanning library...' : 'Scan library'}
        </button>
        <Link
          to="/settings"
          data-testid="setup-wizard-settings-link"
          className="text-sm text-gray-400 hover:text-white transition-colors"
        >
          More settings
        </Link>
      </div>

      {!canScan && (
        <p className="mt-3 text-sm text-gray-500">
          Add at least one folder before scanning.
        </p>
      )}
    </div>
  )
}
