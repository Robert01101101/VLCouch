import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from './Settings'
import * as api from '../api'

vi.mock('../api')

describe('Settings', () => {
  const defaultSettings = {
    metadata_enabled: false,
    scan_on_startup: false,
    auto_generate_thumbnails: true,
    simple_vlc_playback: false,
    vlc_subtitles_on: false,
    vlc_resume_playback: true,
    vlc_tv_playlist: true,
    vlc_playlist_advance: true,
    browse_row_random: false,
    version: '0.1.0',
    github_url: 'https://github.com/Robert01101101/VLCouch',
    diagnostics: {
      vlc_path: 'C:\\Program Files\\VideoLAN\\VLC\\vlc.exe',
      vlc_found: true,
      vlc_download_url: 'https://www.videolan.org/vlc/',
      ffmpeg_available: true,
      ffmpeg_download_url: 'https://ffmpeg.org/download.html',
      winget_available: true,
      library_counts: { movies: 2, shows: 1, episodes: 5 },
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    api.fetchSettings.mockResolvedValue(defaultSettings)
    api.fetchMediaRoots.mockResolvedValue({ roots: [] })
    api.fetchScanStatus.mockResolvedValue({ running: false, last_stats: null })
    api.updateSettings.mockImplementation(async (patch) => ({
      ...defaultSettings,
      ...patch,
    }))
    api.updateMediaRoots.mockImplementation(async (roots) => ({ roots }))
  })

  it('shows loading state', () => {
    api.fetchSettings.mockReturnValue(new Promise(() => {}))
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(screen.getByTestId('page-loading')).toBeInTheDocument()
  })

  it('shows error state with retry', async () => {
    api.fetchSettings.mockRejectedValue(new Error('Network error'))
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(await screen.findByTestId('page-error')).toHaveTextContent('Network error')
    expect(screen.getByTestId('settings-retry-load')).toBeInTheDocument()
  })

  it('renders settings sections', async () => {
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(await screen.findByTestId('settings-page')).toBeInTheDocument()
    expect(screen.getByTestId('settings-media-folders-section')).toBeInTheDocument()
    expect(screen.getByTestId('settings-media-folders')).toBeInTheDocument()
    expect(screen.getByTestId('rescan-library')).toBeInTheDocument()
    expect(screen.getByTestId('settings-wikipedia-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-scan-on-startup-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-browse-row-random-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-auto-thumbnails-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-simple-vlc-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-vlc-options')).toBeInTheDocument()
    expect(screen.getByTestId('settings-vlc-subtitles-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-vlc-resume-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-vlc-tv-playlist-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-vlc-playlist-advance-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-version')).toHaveTextContent('0.1.0')
    expect(screen.getByTestId('settings-github-link')).toHaveAttribute(
      'href',
      'https://github.com/Robert01101101/VLCouch'
    )
    expect(screen.getByTestId('settings-diagnostics')).toBeInTheDocument()
    expect(screen.getByTestId('settings-dependencies')).toBeInTheDocument()
    expect(screen.getByTestId('settings-dependency-vlc-status')).toHaveTextContent('Installed')
    expect(screen.getByTestId('settings-dependency-ffmpeg-status')).toHaveTextContent('Installed')
    expect(screen.getByTestId('settings-diagnostics-library-counts')).toHaveTextContent(
      '2 movies, 1 shows, 5 episodes'
    )
  })

  it('appends dev to version in development mode', async () => {
    vi.stubEnv('MODE', 'development')
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(await screen.findByTestId('settings-version')).toHaveTextContent('0.1.0 (dev)')
    vi.unstubAllEnvs()
  })

  it('disables rescan when no media folders are configured', async () => {
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(await screen.findByTestId('rescan-library')).toBeDisabled()
    expect(screen.getByTestId('settings-rescan-disabled-hint')).toBeInTheDocument()
  })

  it('calls onScan when rescan is clicked', async () => {
    api.fetchMediaRoots.mockResolvedValue({
      roots: [{ path: 'D:\\Movies', type: 'movies' }],
    })
    const onScan = vi.fn().mockResolvedValue({
      running: false,
      last_stats: { movies: 1, episodes: 0, errors: 0 },
    })
    render(<Settings scanning={false} onScan={onScan} />)
    await screen.findByTestId('rescan-library')
    fireEvent.click(screen.getByTestId('rescan-library'))
    await waitFor(() => {
      expect(onScan).toHaveBeenCalled()
    })
    expect(await screen.findByTestId('settings-last-scan-stats')).toHaveTextContent(
      'Last scan: 1 movies'
    )
  })

  it('shows rescan prompt after media folders change', async () => {
    api.fetchMediaRoots.mockResolvedValue({
      roots: [{ path: 'D:\\Movies', type: 'movies' }],
    })
    render(<Settings scanning={false} onScan={vi.fn()} />)
    await screen.findByTestId('settings-media-folders')
    fireEvent.change(screen.getByTestId('settings-media-path-input'), {
      target: { value: 'D:\\TV' },
    })
    fireEvent.click(screen.getByTestId('settings-media-path-add'))
    expect(await screen.findByTestId('settings-rescan-prompt')).toBeInTheDocument()
  })

  it('updates browse row random toggle and refreshes browse', async () => {
    const onBrowseRefresh = vi.fn()
    render(<Settings scanning={false} onScan={vi.fn()} onBrowseRefresh={onBrowseRefresh} />)
    const toggle = await screen.findByTestId('settings-browse-row-random-toggle')
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalledWith({ browse_row_random: true })
      expect(api.resetBrowseSession).toHaveBeenCalled()
      expect(onBrowseRefresh).toHaveBeenCalled()
    })
  })

  it('updates wikipedia toggle', async () => {
    render(<Settings scanning={false} onScan={vi.fn()} />)
    const toggle = await screen.findByTestId('settings-wikipedia-toggle')
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalledWith({ metadata_enabled: true })
    })
  })

  it('shows thumbnail notice when enabling auto thumbnails', async () => {
    api.fetchSettings.mockResolvedValue({
      ...defaultSettings,
      auto_generate_thumbnails: false,
    })
    render(<Settings scanning={false} onScan={vi.fn()} />)
    const toggle = await screen.findByTestId('settings-auto-thumbnails-toggle')
    fireEvent.click(toggle)
    expect(await screen.findByTestId('settings-thumbnail-notice')).toHaveTextContent(
      'Thumbnail generation started in the background'
    )
  })

  it('shows action error when toggle save fails', async () => {
    api.updateSettings.mockRejectedValue(new Error('Save failed'))
    render(<Settings scanning={false} onScan={vi.fn()} />)
    const toggle = await screen.findByTestId('settings-wikipedia-toggle')
    fireEvent.click(toggle)
    expect(await screen.findByTestId('settings-action-error')).toHaveTextContent('Save failed')
  })

  it('hides vlc options when simple vlc is enabled', async () => {
    api.fetchSettings.mockResolvedValue({
      ...defaultSettings,
      simple_vlc_playback: true,
    })
    render(<Settings scanning={false} onScan={vi.fn()} />)
    await screen.findByTestId('settings-vlc-simple-note')
    expect(screen.queryByTestId('settings-vlc-options')).not.toBeInTheDocument()
  })

  it('hides auto-advance when tv playlists are disabled', async () => {
    api.fetchSettings.mockResolvedValue({
      ...defaultSettings,
      vlc_tv_playlist: false,
    })
    render(<Settings scanning={false} onScan={vi.fn()} />)
    await screen.findByTestId('settings-vlc-playlist-advance-hint')
    expect(screen.queryByTestId('settings-vlc-playlist-advance-toggle')).not.toBeInTheDocument()
  })

  it('updates vlc subtitles toggle', async () => {
    render(<Settings scanning={false} onScan={vi.fn()} />)
    const toggle = await screen.findByTestId('settings-vlc-subtitles-toggle')
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalledWith({ vlc_subtitles_on: true })
    })
  })

  it('updates simple vlc toggle', async () => {
    render(<Settings scanning={false} onScan={vi.fn()} />)
    const toggle = await screen.findByTestId('settings-simple-vlc-toggle')
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalledWith({ simple_vlc_playback: true })
    })
  })

  it('shows install buttons when dependencies are missing', async () => {
    api.fetchSettings.mockResolvedValue({
      ...defaultSettings,
      diagnostics: {
        vlc_path: null,
        vlc_found: false,
        vlc_download_url: 'https://www.videolan.org/vlc/',
        ffmpeg_available: false,
        ffmpeg_download_url: 'https://ffmpeg.org/download.html',
        winget_available: true,
        library_counts: { movies: 0, shows: 0, episodes: 0 },
      },
    })
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(await screen.findByTestId('settings-dependency-vlc-download')).toHaveAttribute(
      'href',
      'https://www.videolan.org/vlc/'
    )
    expect(screen.getByTestId('settings-dependency-vlc-install')).toHaveTextContent(
      'Install (winget)'
    )
    expect(screen.getByTestId('settings-dependency-ffmpeg-download')).toBeInTheDocument()
    expect(screen.getByTestId('settings-dependency-ffmpeg-install')).toBeInTheDocument()
  })

  it('shows download only when winget is unavailable', async () => {
    api.fetchSettings.mockResolvedValue({
      ...defaultSettings,
      diagnostics: {
        vlc_path: null,
        vlc_found: false,
        vlc_download_url: 'https://www.videolan.org/vlc/',
        ffmpeg_available: false,
        ffmpeg_download_url: 'https://ffmpeg.org/download.html',
        winget_available: false,
        library_counts: { movies: 0, shows: 0, episodes: 0 },
      },
    })
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(await screen.findByTestId('settings-dependency-vlc-download')).toBeInTheDocument()
    expect(screen.queryByTestId('settings-dependency-vlc-install')).not.toBeInTheDocument()
  })

  it('starts dependency install and shows notice', async () => {
    api.fetchSettings.mockResolvedValue({
      ...defaultSettings,
      diagnostics: {
        vlc_path: null,
        vlc_found: false,
        vlc_download_url: 'https://www.videolan.org/vlc/',
        ffmpeg_available: true,
        ffmpeg_download_url: 'https://ffmpeg.org/download.html',
        winget_available: true,
        library_counts: { movies: 0, shows: 0, episodes: 0 },
      },
    })
    api.installDependency.mockResolvedValue({
      started: true,
      message: 'Installation started. Complete any prompts.',
    })
    render(<Settings scanning={false} onScan={vi.fn()} />)
    fireEvent.click(await screen.findByTestId('settings-dependency-vlc-install'))
    await waitFor(() => {
      expect(api.installDependency).toHaveBeenCalledWith('vlc')
    })
    expect(await screen.findByTestId('settings-install-notice')).toHaveTextContent(
      'Installation started'
    )
  })
})
