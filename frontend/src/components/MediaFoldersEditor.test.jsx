import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MediaFoldersEditor from './MediaFoldersEditor'
import * as api from '../api'

vi.mock('../api')

describe('MediaFoldersEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.updateMediaRoots.mockImplementation(async (roots) => ({ roots }))
    api.pickMediaFolder.mockResolvedValue({ cancelled: false, path: 'D:\\Movies' })
  })

  it('shows empty state', () => {
    render(<MediaFoldersEditor roots={[]} onChange={vi.fn()} />)
    expect(screen.getByTestId('settings-media-folders-empty')).toBeInTheDocument()
  })

  it('adds a folder from manual path input', async () => {
    const onChange = vi.fn()
    render(<MediaFoldersEditor roots={[]} onChange={onChange} />)

    fireEvent.change(screen.getByTestId('settings-media-path-input'), {
      target: { value: 'D:\\Movies' },
    })
    fireEvent.click(screen.getByTestId('settings-media-path-add'))

    await waitFor(() => {
      expect(api.updateMediaRoots).toHaveBeenCalledWith([
        { path: 'D:\\Movies', type: 'movies' },
      ])
    })
    expect(onChange).toHaveBeenCalledWith([{ path: 'D:\\Movies', type: 'movies' }])
  })

  it('removes a configured folder', async () => {
    const onChange = vi.fn()
    render(
      <MediaFoldersEditor
        roots={[{ path: 'D:\\TV', type: 'tv' }]}
        onChange={onChange}
      />
    )

    fireEvent.click(screen.getByTestId('settings-remove-media-root-0'))

    await waitFor(() => {
      expect(api.updateMediaRoots).toHaveBeenCalledWith([])
    })
  })
})
