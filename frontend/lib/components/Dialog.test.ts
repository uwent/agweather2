// Ported from WISP 3: app/frontend/lib/components/Dialog.test.ts
import { fireEvent, render, screen } from '@testing-library/svelte'
import { createRawSnippet, tick } from 'svelte'
import { describe, expect, it, vi } from 'vitest'

import Dialog from './Dialog.svelte'

// A guarded dialog asks before dropping a form's changes
const children = createRawSnippet(() => ({
  render: () => '<form><label for="area">Area</label><input id="area" type="text" value="40" data-unit="ac"></form>',
}))

async function openDialog(guard = true) {
  const view = render(Dialog, { open: true, title: 'Edit North 40', guard, children })
  await tick()
  return view
}

async function changeArea(to: string) {
  const area = screen.getByLabelText('Area')
  await fireEvent.pointerDown(area)
  await fireEvent.input(area, { target: { value: to } })
}

const escape = () => fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' })

describe('Dialog with guard', () => {
  it('closes on Escape when nothing changed', async () => {
    await openDialog()
    await escape()
    await vi.waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('asks on Escape with changes, listing them in place of the form', async () => {
    await openDialog()
    await changeArea('30')
    await escape()
    const question = await screen.findByRole('heading', { name: 'Save your changes?' })
    expect(question).toHaveFocus()
    expect(screen.getByText('Area: 40 ac → 30 ac')).toBeInTheDocument()
    expect(screen.getByLabelText('Area').closest('[hidden]')).not.toBeNull()
  })

  it('asks from ✕ too, and Discard closes', async () => {
    await openDialog()
    await changeArea('30')
    await fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Discard' }))
    await vi.waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('Keep editing brings the form back with its value, focused on what changed', async () => {
    await openDialog()
    await changeArea('30')
    await escape()
    await fireEvent.click(await screen.findByRole('button', { name: 'Keep editing' }))
    await tick()
    const area = screen.getByLabelText('Area')
    expect(area).toHaveValue('30')
    expect(area).toHaveFocus()
    expect(screen.queryByText('Save your changes?')).not.toBeInTheDocument()
  })

  it('Save changes submits the form', async () => {
    await openDialog()
    const submitted = vi.fn((event: Event) => event.preventDefault())
    screen.getByLabelText('Area').closest('form')!.addEventListener('submit', submitted)
    await changeArea('30')
    await escape()
    await fireEvent.click(await screen.findByRole('button', { name: 'Save changes' }))
    await vi.waitFor(() => expect(submitted).toHaveBeenCalledOnce())
    expect(screen.getByLabelText('Area').closest('[hidden]')).toBeNull()
  })

  it('without guard, closes whatever changed', async () => {
    await openDialog(false)
    await changeArea('30')
    await escape()
    await vi.waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })
})
