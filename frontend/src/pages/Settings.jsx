import { useEffect, useState } from 'react'

import { fetchSettings, updateSettings, fetchMediaRoots } from '../api'

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



export default function Settings({ scanning, onScan }) {

  const [settings, setSettings] = useState(null)

  const [mediaRoots, setMediaRoots] = useState([])

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState(null)

  const [savingKey, setSavingKey] = useState(null)

  const isDevMode =
    import.meta.env.MODE === 'development' || import.meta.env.APP_ENV === 'development'



  async function loadSettings() {

    try {

      setError(null)

      const [settingsData, mediaRootsData] = await Promise.all([

        fetchSettings(),

        fetchMediaRoots(),

      ])

      setSettings(settingsData)

      setMediaRoots(mediaRootsData.roots || [])

    } catch (e) {

      setError(e.message)

    } finally {

      setLoading(false)

    }

  }



  useEffect(() => {

    loadSettings()

  }, [])



  async function handleToggle(key, value) {

    const previous = settings

    setSettings((current) => ({ ...current, [key]: value }))

    setSavingKey(key)

    try {

      const data = await updateSettings({ [key]: value })

      setSettings(data)

    } catch (e) {

      setSettings(previous)

      alert(e.message)

    } finally {

      setSavingKey(null)

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

      <div className="text-red-400 text-center py-20" data-testid="page-error">

        {error}

      </div>

    )

  }



  return (

    <div data-testid="settings-page" className="max-w-2xl">

      <h1 className="text-2xl font-bold text-white mb-8">Settings</h1>



      <section className="mb-10">

        <h2 className="text-lg font-semibold text-gray-300 mb-4">Media folders</h2>

        <div className="rounded-lg border border-gray-800 bg-couch-gray/40 p-5">

          <p className="mb-4 text-sm text-gray-400">

            Choose where your movies and TV shows live on this PC.

          </p>

          <MediaFoldersEditor roots={mediaRoots} onChange={setMediaRoots} />

        </div>

      </section>



      <section className="mb-10">

        <h2 className="text-lg font-semibold text-gray-300 mb-4">Library</h2>

        <div className="space-y-6 rounded-lg border border-gray-800 bg-couch-gray/40 p-5">

          <div>

            <button

              data-testid="rescan-library"

              onClick={onScan}

              disabled={scanning}

              className="rounded bg-couch-red px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-couch-red-dark disabled:opacity-50"

            >

              {scanning ? 'Scanning...' : 'Rescan Library'}

            </button>

            <p className="mt-2 text-sm text-gray-400">

              Scan your media folders and import new files.

            </p>

          </div>

          <SettingToggle

            testId="settings-scan-on-startup-toggle"

            label="Automatically rescan on startup"

            description="Applies the next time the server starts."

            checked={settings.scan_on_startup}

            disabled={savingKey === 'scan_on_startup'}

            onChange={(value) => handleToggle('scan_on_startup', value)}

          />

          <SettingToggle

            testId="settings-browse-row-random-toggle"

            label="Randomize home row order"

            description="Shuffle movies and TV shows within each browse row on the home page. Order stays the same until you close the app. When off, items are sorted alphabetically."

            checked={settings.browse_row_random}

            disabled={savingKey === 'browse_row_random'}

            onChange={(value) => handleToggle('browse_row_random', value)}

          />

        </div>

      </section>



      <section className="mb-10">

        <h2 className="text-lg font-semibold text-gray-300 mb-4">Thumbnails</h2>

        <div className="rounded-lg border border-gray-800 bg-couch-gray/40 p-5">

          <SettingToggle

            testId="settings-auto-thumbnails-toggle"

            label="Auto-generate thumbnails"

            description="Extract posters for movies and show tiles in the background. Episode thumbnails are generated when you open a show. When off, thumbnails are created only when you play or mark items watched."

            checked={settings.auto_generate_thumbnails}

            disabled={savingKey === 'auto_generate_thumbnails'}

            onChange={(value) => handleToggle('auto_generate_thumbnails', value)}

          />

        </div>

      </section>



      <section className="mb-10">

        <h2 className="text-lg font-semibold text-gray-300 mb-4">Playback</h2>

        <div className="space-y-6 rounded-lg border border-gray-800 bg-couch-gray/40 p-5">

          <SettingToggle

            testId="settings-simple-vlc-toggle"

            label="Simple VLC launch"

            description="Open files in VLC with no extra options. Disables the playback options below. Use this if your VLC version has compatibility issues."

            checked={settings.simple_vlc_playback}

            disabled={savingKey === 'simple_vlc_playback'}

            onChange={(value) => handleToggle('simple_vlc_playback', value)}

          />

          <div

            data-testid="settings-vlc-options"

            className={`ml-1 space-y-6 border-l border-gray-700 pl-5 ${

              settings.simple_vlc_playback ? 'opacity-50' : ''

            }`}

          >

            <SettingToggle

              testId="settings-vlc-subtitles-toggle"

              label="Enable subtitles"

              description="Turn on subtitles in VLC when playing. Uses detected subtitle files or the first embedded subtitle track."

              checked={settings.vlc_subtitles_on}

              disabled={settings.simple_vlc_playback || savingKey === 'vlc_subtitles_on'}

              onChange={(value) => handleToggle('vlc_subtitles_on', value)}

            />

            <SettingToggle

              testId="settings-vlc-resume-toggle"

              label="Remember playback position"

              description="Save your place while watching and resume from that position the next time you play."

              checked={settings.vlc_resume_playback}

              disabled={settings.simple_vlc_playback || savingKey === 'vlc_resume_playback'}

              onChange={(value) => handleToggle('vlc_resume_playback', value)}

            />

            <SettingToggle

              testId="settings-vlc-tv-playlist-toggle"

              label="TV binge playlists"

              description="Queue all remaining unwatched episodes in a show when you play an episode."

              checked={settings.vlc_tv_playlist}

              disabled={settings.simple_vlc_playback || savingKey === 'vlc_tv_playlist'}

              onChange={(value) => handleToggle('vlc_tv_playlist', value)}

            />

            <SettingToggle

              testId="settings-vlc-playlist-advance-toggle"

              label="Auto-advance to next episode"

              description="Prevent VLC from repeating the current episode and continue to the next item in the playlist."

              checked={settings.vlc_playlist_advance}

              disabled={settings.simple_vlc_playback || savingKey === 'vlc_playlist_advance'}

              onChange={(value) => handleToggle('vlc_playlist_advance', value)}

            />

          </div>

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

            disabled={savingKey === 'metadata_enabled'}

            onChange={(value) => handleToggle('metadata_enabled', value)}

          />

        </div>

      </section>



      <section>

        <h2 className="text-lg font-semibold text-gray-300 mb-4">About</h2>

        <div className="rounded-lg border border-gray-800 bg-couch-gray/40 p-5 space-y-3">

          <p className="text-sm text-gray-300">

            Version{' '}

            <span data-testid="settings-version" className="text-white">

              {settings.version}{isDevMode ? ' (dev)' : ''}

            </span>

          </p>

          <a

            href={settings.github_url}

            target="_blank"

            rel="noopener noreferrer"

            data-testid="settings-github-link"

            className="inline-block text-sm text-couch-red hover:text-couch-red-light transition-colors"

          >

            View on GitHub

          </a>

        </div>

      </section>

    </div>

  )

}

