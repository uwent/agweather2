// Ported from WISP 3 (adapted): app/frontend/lib/components/FlashMessages.test.ts
import { fireEvent, render, screen } from '@testing-library/svelte'
import { flushSync } from 'svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { page } from '@/test/page.svelte'
vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

import FlashMessages from './FlashMessages.svelte'

// jsdom has no Web Animations; Svelte's out transition waits on one, so finish it at once
Element.prototype.animate ??= function () {
  const animation = { cancel() {}, currentTime: 0, effect: null } as unknown as Animation
  let finish: (() => void) | null = null
  Object.defineProperty(animation, 'onfinish', {
    set(fn) {
      finish = fn
      queueMicrotask(() => finish?.())
    },
  })
  return animation
}

const countdown = (message: HTMLElement) => message.querySelector('.countdown')

describe('FlashMessages', () => {
  beforeEach(() => {
    page.flash = {}
  })

  it('dismisses a notice when its countdown ends', async () => {
    page.flash = { messages: [{ level: 'success', message: 'Site saved.' }] }
    render(FlashMessages)
    const message = screen.getByRole('status')
    expect(message).toHaveTextContent('Site saved.')

    await fireEvent.animationEnd(countdown(message)!)
    await vi.waitFor(() => expect(screen.queryByText('Site saved.')).not.toBeInTheDocument())
  })

  it('keeps a notice that was clicked until it is dismissed', async () => {
    page.flash = { messages: [{ level: 'info', message: 'Signed in.' }] }
    render(FlashMessages)
    const message = screen.getByRole('status')

    await fireEvent.click(screen.getByText('Signed in.'))
    expect(countdown(message)).toBeNull()

    await fireEvent.click(screen.getByRole('button', { name: 'Dismiss message' }))
    await vi.waitFor(() => expect(screen.queryByText('Signed in.')).not.toBeInTheDocument())
  })

  it('reuses the box for a new flash and restarts its countdown', async () => {
    page.flash = { messages: [{ level: 'info', message: 'Signed in.' }] }
    render(FlashMessages)
    const message = screen.getByRole('status')
    const bar = countdown(message)
    await fireEvent.click(screen.getByText('Signed in.'))
    expect(countdown(message)).toBeNull()

    page.flash = { messages: [{ level: 'info', message: 'Signed out.' }] }
    flushSync()
    expect(screen.getByRole('status')).toBe(message)
    expect(message).toHaveTextContent('Signed out.')
    expect(countdown(message)).not.toBeNull()
    expect(countdown(message)).not.toBe(bar)
  })

  it('leaves alerts up with no countdown', () => {
    page.flash = {
      messages: [
        { level: 'error', message: 'Something went wrong.' },
        { level: 'success', message: 'Saved.' },
      ],
    }
    render(FlashMessages)
    expect(countdown(screen.getByRole('alert'))).toBeNull()
    expect(countdown(screen.getByRole('status'))).not.toBeNull()
  })
})
