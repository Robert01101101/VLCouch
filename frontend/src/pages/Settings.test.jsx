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
    version: '0.1.0',
    github_url: 'https://github.com/Robert01101101/VLCouch',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    api.fetchSettings.mockResolvedValue(defaultSettings)
    api.fetchMediaRoots.mockResolvedValue({ roots: [] })
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

  it('shows error state', async () => {
    api.fetchSettings.mockRejectedValue(new Error('Network error'))
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(await screen.findByTestId('page-error')).toHaveTextContent('Network error')
  })

  it('renders settings sections', async () => {
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(await screen.findByTestId('settings-page')).toBeInTheDocument()
    expect(screen.getByTestId('settings-media-folders')).toBeInTheDocument()
    expect(screen.getByTestId('rescan-library')).toBeInTheDocument()
    expect(screen.getByTestId('settings-wikipedia-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-scan-on-startup-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-auto-thumbnails-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-simple-vlc-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('settings-version')).toHaveTextContent('0.1.0')
    expect(screen.getByTestId('settings-github-link')).toHaveAttribute(
      'href',
      'https://github.com/Robert01101101/VLCouch'
    )
  })

  it('appends dev to version in development mode', async () => {
    vi.stubEnv('MODE', 'development')
    render(<Settings scanning={false} onScan={vi.fn()} />)
    expect(await screen.findByTestId('settings-version')).toHaveTextContent('0.1.0 (dev)')
    vi.unstubAllEnvs()
  })

  it('calls onScan when rescan is clicked', async () => {
    const onScan = vi.fn()
    render(<Settings scanning={false} onScan={onScan} />)
    await screen.findByTestId('rescan-library')
    fireEvent.click(screen.getByTestId('rescan-library'))
    expect(onScan).toHaveBeenCalled()
  })

  it('updates wikipedia toggle', async () => {
    render(<Settings scanning={false} onScan={vi.fn()} />)
    const toggle = await screen.findByTestId('settings-wikipedia-toggle')
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalledWith({ metadata_enabled: true })
    })
  })

  it('updates auto thumbnails toggle', async () => {
    render(<Settings scanning={false} onScan={vi.fn()} />)
    const toggle = await screen.findByTestId('settings-auto-thumbnails-toggle')
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalledWith({ auto_generate_thumbnails: false })
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
})
