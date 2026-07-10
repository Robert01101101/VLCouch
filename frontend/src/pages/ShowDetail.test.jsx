import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ShowDetail from './ShowDetail'
import * as api from '../api'

vi.mock('../api')

const mockShow = {
  id: 1,
  title: 'Breaking Bad',
  overview: 'A chemistry teacher turns to crime.',
  seasons: [
    {
      season: 1,
      episodes: [
        { id: 10, season: 1, episode: 1, title: 'Pilot', watched: false },
        { id: 11, season: 1, episode: 2, title: 'Cat\'s in the Bag...', watched: false },
      ],
    },
  ],
}

function renderShow() {
  return render(
    <MemoryRouter initialEntries={['/shows/1']}>
      <Routes>
        <Route path="/shows/:id" element={<ShowDetail />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ShowDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.fetchShow.mockResolvedValue(mockShow)
  })

  it('renders episode list', async () => {
    renderShow()
    await screen.findByTestId('show-detail')
    expect(screen.getByRole('heading', { level: 1, name: 'Breaking Bad' })).toBeInTheDocument()
    expect(screen.getByText('Pilot')).toBeInTheDocument()
    expect(screen.getByTestId('watched-episode-10')).toBeInTheDocument()
  })

  it('calls setWatchStatus when watched checkbox toggled', async () => {
    api.setWatchStatus.mockResolvedValue({ watched: true })
    renderShow()
    await screen.findByTestId('show-detail')
    fireEvent.click(screen.getByTestId('watched-episode-10'))
    await waitFor(() => {
      expect(api.setWatchStatus).toHaveBeenCalledWith('episode', 10, true)
    })
    expect(api.playItem).not.toHaveBeenCalled()
  })

  it('calls playItem when episode row clicked', async () => {
    api.playItem.mockResolvedValue({})
    renderShow()
    await screen.findByTestId('show-detail')
    fireEvent.click(screen.getByTestId('play-episode-10'))
    await waitFor(() => {
      expect(api.playItem).toHaveBeenCalledWith('episode', 10)
    })
    await waitFor(() => {
      expect(api.fetchShow).toHaveBeenCalledTimes(2)
    })
  })
})
