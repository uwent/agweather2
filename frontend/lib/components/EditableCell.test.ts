// Ported from WISP 3: app/frontend/lib/components/EditableCell.test.ts
import { fireEvent, render, screen } from '@testing-library/svelte'
import { createRawSnippet, tick } from 'svelte'
import { describe, expect, it, vi } from 'vitest'

import EditableCell from './EditableCell.svelte'

const children = createRawSnippet(() => ({ render: () => '<span>0.50</span>' }))
const props = (onsave: (text: string) => Promise<string | null>) => ({
  text: '0.5',
  label: 'Rain, Wed, Jul 1',
  grid: 'days',
  row: 0,
  col: 0,
  onsave,
  children,
})

describe('EditableCell', () => {
  it('opens an input on click and saves the edited text on Enter', async () => {
    const onsave = vi.fn().mockResolvedValue(null)
    render(EditableCell, props(onsave))
    await fireEvent.click(screen.getByRole('button', { name: /^Rain, Wed, Jul 1/ }))
    const input = screen.getByRole('textbox', { name: /^Rain, Wed, Jul 1/ })
    expect(input).toHaveValue('0.5')
    await fireEvent.input(input, { target: { value: '0.8' } })
    await fireEvent.keyDown(input, { key: 'Enter' })
    await vi.waitFor(() => expect(onsave).toHaveBeenCalledWith('0.8'))
    await vi.waitFor(() => expect(screen.getByRole('button')).toHaveTextContent('0.50'))
  })

  it('starts editing with the key typed on a focused cell', async () => {
    render(EditableCell, props(vi.fn().mockResolvedValue(null)))
    await fireEvent.keyDown(screen.getByRole('button'), { key: '7' })
    await tick()
    expect(screen.getByRole('textbox')).toHaveValue('7')
  })

  it("doesn't save unchanged text, and Escape cancels", async () => {
    const onsave = vi.fn()
    render(EditableCell, props(onsave))
    await fireEvent.click(screen.getByRole('button'))
    await fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' })
    await fireEvent.click(screen.getByRole('button'))
    await fireEvent.input(screen.getByRole('textbox'), { target: { value: '3' } })
    await fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' })
    expect(onsave).not.toHaveBeenCalled()
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it("doesn't save on the blur that follows Escape (Chromium blurs the input as it's removed)", async () => {
    const onsave = vi.fn()
    render(EditableCell, props(onsave))
    await fireEvent.click(screen.getByRole('button'))
    const input = screen.getByRole('textbox')
    await fireEvent.input(input, { target: { value: '3' } })
    await fireEvent.keyDown(input, { key: 'Escape' })
    await fireEvent.blur(input)
    expect(onsave).not.toHaveBeenCalled()
  })

  it('keeps the input open and shows the error when saving fails', async () => {
    render(EditableCell, props(vi.fn().mockResolvedValue('Enter a number')))
    await fireEvent.click(screen.getByRole('button'))
    await fireEvent.input(screen.getByRole('textbox'), { target: { value: 'lots' } })
    await fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' })
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter a number')
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true')
  })

  describe('as a grid', () => {
    const cell = (col: number, onsave = vi.fn().mockResolvedValue(null)) =>
      render(EditableCell, { ...props(onsave), label: `Col ${col}`, col })
    const button = (col: number) => screen.getByRole('button', { name: new RegExp(`^Col ${col}`) })

    it('is one tab stop, which follows the focused cell', async () => {
      cell(0)
      cell(1)
      cell(2)
      expect([0, 1, 2].map((col) => button(col).tabIndex)).toEqual([0, -1, -1])
      button(2).focus()
      expect([0, 1, 2].map((col) => button(col).tabIndex)).toEqual([-1, -1, 0])
    })

    it('saves on Tab and moves to the next cell in the row, without opening it', async () => {
      const onsave = vi.fn().mockResolvedValue(null)
      cell(0, onsave)
      cell(1)
      await fireEvent.click(button(0))
      await fireEvent.input(screen.getByRole('textbox'), { target: { value: '0.8' } })
      await fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Tab' })
      await vi.waitFor(() => expect(button(1)).toHaveFocus())
      expect(onsave).toHaveBeenCalledWith('0.8')
      expect(screen.queryByRole('textbox')).toBeNull()
      expect(button(1).tabIndex).toBe(0)
    })
  })

  it('shows plain text when read-only, with nothing to edit', () => {
    render(EditableCell, { ...props(vi.fn()), readOnly: true })
    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.getByText('0.50')).toBeInTheDocument()
  })
})
