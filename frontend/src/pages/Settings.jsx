import { useEffect, useState } from 'react'

import {
  fetchScanStatus,
  fetchSettings,
  fetchMediaRoots,
  fetchUpdateStatus,
  installDependency,
  resetBrowseSession,
  updateSettings,
} from '../api'

import MediaFoldersEditor from '../components/MediaFoldersEditor'

function SettingToggle({ testId, label, description, checked, disabled, onChange }) {
  return (
    <label className="flex items-start justify-between gap-4 cursor-pointer">
      <div className="min-w-0">
        <span className="block text-sm font-medium text-gray-200">{label}</span>
        {description && (
          <span className="block text-sm text-gray-400 mt-1">{description}</span>
        )}
      </div>
      <span className="relative inline-flex shrink-0">
        <input
          type="checkbox"
          role="switch"
          data-testid={testId}
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only peer"
        />
        <span
          className={`block h-6 w-11 rounded-full transition-colors peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-couch-red ${
            checked ? 'bg-couch-red' : 'bg-gray-600'
          } ${disabled ? 'opacity-50' : ''}`}
          aria-hidden="true"
        />
        <span
          className={`pointer-events-none absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
            checked ? 'translate-x-5' : 'translate-x-0'
          }`}
          aria-hidden="true"
        />
      </span>
    </label>
  )
}

function formatLastScanStats(stats) {
  if (!stats) {
    return null
  }
  const parts = []
  if (stats.movies != null) {
    parts.push(`${stats.movies} movies`)
  }
  if (stats.episodes != null) {
    parts.push(`${stats.episodes} episodes`)
  }
  if (parts.length === 0) {
    return null
  }
  let text = `Last scan: ${parts.join(', ')}`
  if (stats.errors > 0) {
    text += ` · ${stats.errors} errors`
  }
  return text
}

function DependencyStatus({
  testId,
  label,
  description,
  installed,
  path,
  downloadUrl,
  installing,
  canInstall,
  onInstall,
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between" data-testid={testId}>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${
              installed ? 'bg-green-500' : 'bg-amber-400'
            }`}
            aria-hidden="true"
          />
          <span className="text-sm font-medium text-gray-200">{label}</span>
          <span
            className={`text-xs font-medium ${installed ? 'text-green-400' : 'text-amber-300'}`}
            data-testid={`${testId}-status`}
          >
            {installed ? 'Installed' : 'Not found'}
          </span>
        </div>
        <p className="mt-1 text-sm text-gray-400">{description}</p>
        {installed && path && (
          <p className="mt-1 text-xs text-gray-500 break-all" data-testid={`${testId}-path`}>
            {path}
          </p>
        )}
      </div>
      {!installed && downloadUrl && (
        <div className="flex shrink-0 flex-wrap gap-2">
          <a
            href={downloadUrl}
            target="_blank"
            rel="noopener noreferrer"
            data-testid={`${testId}-download`}
            className="rounded border border-gray-600 px-4 py-2 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-700"
          >
            Download
          </a>
          {canInstall && (
            <button
              type="button"
              data-testid={`${testId}-install`}
              onClick={onInstall}
              disabled={installing}
              className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-600 disabled:opacity-50"
            >
              {installing ? 'Starting...' : 'Install (winget)'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default function Settings({ scanning, onScan, onBrowseRefresh }) {
  const [settings, setSettings] = useState(null)
  const [mediaRoots, setMediaRoots] = useState([])
  const [scanStatus, setScanStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [foldersChanged, setFoldersChanged] = useState(false)
  const [thumbnailNotice, setThumbnailNotice] = useState(null)
  const [installingDep, setInstallingDep] = useState(null)
  const [installNotice, setInstallNotice] = useState(null)
  const [updateStatus, setUpdateStatus] = useState(null)
  const [checkingUpdates, setCheckingUpdates] = useState(false)

  const isDevMode =
    import.meta.env.MODE === 'development' || import.meta.env.APP_ENV === 'development'

  async function loadSettings() {
    setLoading(true)
    try {
      setError(null)
      const [settingsData, mediaRootsData, statusData, updateData] = await Promise.all([
        fetchSettings(),
        fetchMediaRoots(),
        fetchScanStatus().catch(() => null),
        fetchUpdateStatus().catch(() => null),
      ])
      setSettings(settingsData)
      setMediaRoots(mediaRootsData.roots || [])
      if (statusData) {
        setScanStatus(statusData)
      }
      if (updateData) {
        setUpdateStatus(updateData)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSettings()
  }, [])

  function handleMediaRootsChange(roots) {
    setMediaRoots(roots)
    setFoldersChanged(true)
    setActionError(null)
  }

  async function handleRescan() {
    setActionError(null)
    try {
      const status = await onScan()
      if (status) {
        setScanStatus(status)
      } else {
        const latest = await fetchScanStatus()
        setScanStatus(latest)
      }
      setFoldersChanged(false)
      const settingsData = await fetchSettings()
      setSettings(settingsData)
    } catch (e) {
      setActionError(e.message)
    }
  }

  async function handleInstallDependency(name) {
    setActionError(null)
    setInstallNotice(null)
    setInstallingDep(name)
    try {
      const result = await installDependency(name)
      setInstallNotice(result.message)
      if (result.already_installed) {
        const settingsData = await fetchSettings()
        setSettings(settingsData)
      }
    } catch (e) {
      setActionError(e.message)
    } finally {
      setInstallingDep(null)
    }
  }

  async function handleRefreshDependencies() {
    setActionError(null)
    try {
      const settingsData = await fetchSettings()
      setSettings(settingsData)
      setInstallNotice(null)
    } catch (e) {
      setActionError(e.message)
    }
  }

  async function handleCheckUpdates() {
    setActionError(null)
    setCheckingUpdates(true)
    try {
      const updateData = await fetchUpdateStatus({ refresh: true })
      setUpdateStatus(updateData)
    } catch (e) {
      setActionError(e.message)
    } finally {
      setCheckingUpdates(false)
    }
  }

  async function handleToggle(key, value) {
    const previous = settings
    setActionError(null)
    setSettings((current) => ({ ...current, [key]: value }))
    try {
      const data = await updateSettings({ [key]: value })
      setSettings(data)

      if (key === 'browse_row_random') {
        resetBrowseSession()
        onBrowseRefresh?.()
      }

      if (key === 'auto_generate_thumbnails' && value && !previous.auto_generate_thumbnails) {
        setThumbnailNotice(
          'Thumbnail generation started in the background. Posters will appear over time.'
        )
      }
    } catch (e) {
      setSettings(previous)
      setActionError(e.message)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-20 text-gray-400" data-testid="page-loading">
        Loading settings...
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-20" data-testid="page-error">
        <p className="text-red-400 mb-4">{error}</p>
        <button
          type="button"
          data-testid="settings-retry-load"
          onClick={loadSettings}
          className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-600"
        >
          Retry
        </button>
      </div>
    )
  }

  const lastScanText = formatLastScanStats(scanStatus?.last_stats)
  const diagnostics = settings.diagnostics
  const canRescan = mediaRoots.length > 0

  return (
    <div data-testid="settings-page" className="max-w-2xl">
      <h1 className="text-2xl font-bold text-white mb-8">Settings</h1>

      {actionError && (
        <div
          role="alert"
          data-testid="settings-action-error"
          className="mb-6 rounded-lg border border-red-700 bg-red-900/40 px-4 py-3 text-sm text-red-200"
        >
          {actionError}
        </div>
      )}

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-300 mb-4">Required software</h2>
        <div className="rounded-lg border border-gray-800 bg-couch-gray/40 p-5 space-y-6" data-testid="settings-dependencies">
          <DependencyStatus
            testId="settings-dependency-vlc"
            label="VLC media player"
            description="Opens and plays your movies and TV episodes."
            installed={diagnostics?.vlc_found}
            path={diagnostics?.vlc_path}
            downloadUrl={diagnostics?.vlc_download_url}
            installing={installingDep === 'vlc'}
            canInstall={diagnostics?.winget_available}
            onInstall={() => handleInstallDependency('vlc')}
          />
          <DependencyStatus
            testId="settings-dependency-ffmpeg"
            label="ffmpeg"
            description="Extracts poster and episode thumbnails from your video files."
            installed={diagnostics?.ffmpeg_available}
            downloadUrl={diagnostics?.ffmpeg_download_url}
            installing={installingDep === 'ffmpeg'}
            canInstall={diagnostics?.winget_available}
            onInstall={() => handleInstallDependency('ffmpeg')}
          />
          <div className="flex flex-wrap items-center gap-3 border-t border-gray-700 pt-4">
            <button
              type="button"
              data-testid="settings-dependencies-refresh"
              onClick={handleRefreshDependencies}
              className="rounded border border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-700"
            >
              Refresh status
            </button>
            {installNotice && (
              <p className="text-sm text-gray-400" data-testid="settings-install-notice">
                {installNotice}
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-300 mb-4">Library</h2>
        <div className="space-y-8 rounded-lg border border-gray-800 bg-couch-gray/40 p-5">
          <div data-testid="settings-media-folders-section">
            <h3 className="text-sm font-semibold text-gray-200">Media folders</h3>
            <p className="mt-1 mb-4 text-sm text-gray-400">
              Where your movies and TV shows live on this PC.
            </p>
            <MediaFoldersEditor roots={mediaRoots} onChange={handleMediaRootsChange} />
          </div>

          <div className="border-t border-gray-700 pt-6">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">Scan library</h3>
            <button
              data-testid="rescan-library"
              onClick={handleRescan}
              disabled={scanning || !canRescan}
              className="rounded bg-couch-red px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-couch-red-dark disabled:opacity-50"
            >
              {scanning ? 'Scanning...' : 'Rescan Library'}
            </button>
            <p className="mt-2 text-sm text-gray-400">
              Import new files from your media folders.
            </p>
            {!canRescan && (
              <p className="mt-2 text-sm text-gray-500" data-testid="settings-rescan-disabled-hint">
                Add at least one media folder before scanning.
              </p>
            )}
            {foldersChanged && (
              <p className="mt-2 text-sm text-amber-300" data-testid="settings-rescan-prompt">
                Folders updated — rescan to pick up changes.
              </p>
            )}
            {lastScanText && (
              <p className="mt-2 text-sm text-gray-400" data-testid="settings-last-scan-stats">
                {lastScanText}
              </p>
            )}
          </div>

          <div className="space-y-6">
            <SettingToggle
              testId="settings-scan-on-startup-toggle"
              label="Automatically rescan on startup"
              description="Applies the next time the server starts."
              checked={settings.scan_on_startup}
              onChange={(value) => handleToggle('scan_on_startup', value)}
            />

            <SettingToggle
              testId="settings-browse-row-random-toggle"
              label="Randomize home row order"
              description="Shuffle movies and TV shows within each browse row on the home page. Order stays the same until you start a new browser session. When off, items are sorted alphabetically."
              checked={settings.browse_row_random}
              onChange={(value) => handleToggle('browse_row_random', value)}
            />
          </div>
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-300 mb-4">Thumbnails</h2>
        <div className="rounded-lg border border-gray-800 bg-couch-gray/40 p-5 space-y-3">
          <SettingToggle
            testId="settings-auto-thumbnails-toggle"
            label="Auto-generate thumbnails"
            description="Extract posters for movies and show tiles in the background. Episode thumbnails are generated when you open a show. When off, thumbnails are created only when you play or mark items watched."
            checked={settings.auto_generate_thumbnails}
            onChange={(value) => handleToggle('auto_generate_thumbnails', value)}
          />
          {thumbnailNotice && (
            <p className="text-sm text-gray-400" data-testid="settings-thumbnail-notice">
              {thumbnailNotice}
            </p>
          )}
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-300 mb-4">Playback</h2>
        <div className="space-y-6 rounded-lg border border-gray-800 bg-couch-gray/40 p-5">
          <SettingToggle
            testId="settings-simple-vlc-toggle"
            label="Simple VLC launch"
            description="Open files in VLC with no extra options. Hides the playback options below. Use this if your VLC version has compatibility issues."
            checked={settings.simple_vlc_playback}
            onChange={(value) => handleToggle('simple_vlc_playback', value)}
          />

          {settings.simple_vlc_playback ? (
            <p className="text-sm text-gray-400" data-testid="settings-vlc-simple-note">
              Playback options are not used in simple mode.
            </p>
          ) : (
            <div data-testid="settings-vlc-options" className="ml-1 space-y-6 border-l border-gray-700 pl-5">
              <SettingToggle
                testId="settings-vlc-subtitles-toggle"
                label="Enable subtitles"
                description="Turn on subtitles in VLC when playing. Uses detected subtitle files or the first embedded subtitle track."
                checked={settings.vlc_subtitles_on}
                onChange={(value) => handleToggle('vlc_subtitles_on', value)}
              />

              <SettingToggle
                testId="settings-vlc-resume-toggle"
                label="Remember playback position"
                description="Save your place while watching and resume from that position the next time you play."
                checked={settings.vlc_resume_playback}
                onChange={(value) => handleToggle('vlc_resume_playback', value)}
              />

              <div className="space-y-6">
                <SettingToggle
                  testId="settings-vlc-tv-playlist-toggle"
                  label="TV binge playlists"
                  description="Queue all remaining unwatched episodes in a show when you play an episode."
                  checked={settings.vlc_tv_playlist}
                  onChange={(value) => handleToggle('vlc_tv_playlist', value)}
                />

                {settings.vlc_tv_playlist ? (
                  <div
                    data-testid="settings-vlc-playlist-options"
                    className="ml-1 space-y-6 border-l border-gray-700 pl-5"
                  >
                    <SettingToggle
                      testId="settings-vlc-playlist-advance-toggle"
                      label="Auto-advance to next episode"
                      description="Prevent VLC from repeating the current episode and continue to the next item in the playlist."
                      checked={settings.vlc_playlist_advance}
                      onChange={(value) => handleToggle('vlc_playlist_advance', value)}
                    />
                  </div>
                ) : (
                  <p className="text-sm text-gray-500" data-testid="settings-vlc-playlist-advance-hint">
                    Enable TV binge playlists to configure auto-advance.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-300 mb-4">Metadata</h2>
        <div className="rounded-lg border border-gray-800 bg-couch-gray/40 p-5">
          <SettingToggle
            testId="settings-wikipedia-toggle"
            label="Wikipedia plot summaries"
            description="Fetch plot summaries from Wikipedia on show detail pages. Fully offline when disabled."
            checked={settings.metadata_enabled}
            onChange={(value) => handleToggle('metadata_enabled', value)}
          />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-gray-300 mb-4">About</h2>
        <div className="rounded-lg border border-gray-800 bg-couch-gray/40 p-5 space-y-3">
          {updateStatus?.update_available && (
            <div
              data-testid="settings-update-available"
              className="rounded-lg border border-couch-red/40 bg-couch-red/10 px-4 py-3 text-sm text-gray-200"
            >
              <p>
                Version{' '}
                <span className="font-medium text-white">{updateStatus.latest_version}</span> is
                available.
              </p>
              {(updateStatus.download_url || updateStatus.release_url) && (
                <a
                  href={updateStatus.download_url || updateStatus.release_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="settings-update-download"
                  className="mt-2 inline-block rounded bg-couch-red px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-couch-red-dark"
                >
                  Download update
                </a>
              )}
            </div>
          )}

          <p className="text-sm text-gray-300">
            Version{' '}
            <span data-testid="settings-version" className="text-white">
              {settings.version}{isDevMode ? ' (dev)' : ''}
            </span>
          </p>

          {diagnostics && (
            <div className="space-y-2 text-sm text-gray-400" data-testid="settings-diagnostics">
              <p data-testid="settings-diagnostics-library-counts">
                Library:{' '}
                <span className="text-gray-200">
                  {diagnostics.library_counts.movies} movies,{' '}
                  {diagnostics.library_counts.shows} shows,{' '}
                  {diagnostics.library_counts.episodes} episodes
                </span>
              </p>
            </div>
          )}

          <a
            href={settings.github_url}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="settings-github-link"
            className="inline-block text-sm text-couch-red hover:text-couch-red-light transition-colors"
          >
            View on GitHub
          </a>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button
              type="button"
              data-testid="settings-check-updates"
              onClick={handleCheckUpdates}
              disabled={checkingUpdates}
              className="rounded border border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-700 disabled:opacity-50"
            >
              {checkingUpdates ? 'Checking...' : 'Check for updates'}
            </button>
            {updateStatus?.checked && !updateStatus.update_available && (
              <p className="text-sm text-gray-400" data-testid="settings-update-current">
                You are on the latest version.
              </p>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
