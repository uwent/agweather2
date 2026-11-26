import { fireEvent, render, screen } from '@testing-library/svelte'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ShareButton from './ShareButton.svelte'

afterEach(() => vi.unstubAllGlobals())

function stubClipboard(writeText: (text: string) => Promise<void>) {
  vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
}

describe('ShareButton', () => {
  it('shows the view’s link as it opens, focused, and copies it', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    stubClipboard(writeText)
    let zoom = 6
    render(ShareButton, { url: () => `https://example.org/map?z=${zoom}` })
    zoom = 9

    await fireEvent.click(screen.getByRole('button', { name: 'Share' }))
    const link = await screen.findByRole('textbox', { name: 'Link to this view' })
    expect(link).toHaveValue('https://example.org/map?z=9')
    await vi.waitFor(() => expect(link).toHaveFocus())

    await fireEvent.click(screen.getByRole('button', { name: 'Copy' }))
    expect(writeText).toHaveBeenCalledWith('https://example.org/map?z=9')
    expect(await screen.findByRole('status')).toHaveTextContent('Copied the link.')
  })

  it('says how to copy when the browser refuses', async () => {
    stubClipboard(() => Promise.reject(new Error('denied')))
    render(ShareButton, { url: '/map?z=9' })
    await fireEvent.click(screen.getByRole('button', { name: 'Share' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Copy' }))
    await vi.waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('copy it with Ctrl+C'))
  })

  it('closes on Escape and returns focus to the button', async () => {
    render(ShareButton, { url: '/map' })
    const button = screen.getByRole('button', { name: 'Share' })
    button.focus() // as a click does in a browser
    await fireEvent.click(button)
    const link = await screen.findByRole('textbox', { name: 'Link to this view' })
    await fireEvent.keyDown(link, { key: 'Escape' })
    await vi.waitFor(() => expect(screen.queryByRole('textbox')).not.toBeInTheDocument())
    await vi.waitFor(() => expect(button).toHaveFocus())
  })
})
