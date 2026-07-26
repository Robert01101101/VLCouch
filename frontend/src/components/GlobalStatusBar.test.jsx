import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import GlobalStatusBar from './GlobalStatusBar'
import * as api from '../api'

vi.mock('../api')

describe('GlobalStatusBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.fetchScanStatus.mockResolvedValue({ running: false, last_stats: null })
    api.fetchThumbnailStatus.mockResolvedValue({ busy: false, queue_size: 0, in_flight: 0 })
  })

  it('renders nothing when scan and thumbnails are idle', async () => {
    render(<GlobalStatusBar />)

    await waitFor(() => {
      expect(api.fetchScanStatus).toHaveBeenCalled()
      expect(api.fetchThumbnailStatus).toHaveBeenCalled()
    })
    expect(screen.queryByTestId('global-status-bar')).not.toBeInTheDocument()
  })

  it('shows scanning indicator when library scan is running', async () => {
    api.fetchScanStatus.mockResolvedValue({ running: true, last_stats: null })

    render(<GlobalStatusBar />)

    expect(await screen.findByTestId('global-status-bar')).toBeInTheDocument()
    expect(screen.getByTestId('global-status-scanning')).toHaveTextContent('Scanning library')
    expect(screen.queryByTestId('global-status-thumbnails')).not.toBeInTheDocument()
  })

  it('shows thumbnail indicator when worker is busy', async () => {
    api.fetchThumbnailStatus.mockResolvedValue({ busy: true, queue_size: 2, in_flight: 1 })

    render(<GlobalStatusBar />)

    expect(await screen.findByTestId('global-status-bar')).toBeInTheDocument()
    expect(screen.getByTestId('global-status-thumbnails')).toHaveTextContent('Generating thumbnails')
    expect(screen.queryByTestId('global-status-scanning')).not.toBeInTheDocument()
  })

  it('shows both indicators when scan and thumbnails are active', async () => {
    api.fetchScanStatus.mockResolvedValue({ running: true, last_stats: null })
    api.fetchThumbnailStatus.mockResolvedValue({ busy: true, queue_size: 1, in_flight: 1 })

    render(<GlobalStatusBar />)

    expect(await screen.findByTestId('global-status-bar')).toBeInTheDocument()
    expect(screen.getByTestId('global-status-scanning')).toBeInTheDocument()
    expect(screen.getByTestId('global-status-thumbnails')).toBeInTheDocument()
  })
})
