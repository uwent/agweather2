// Ported from WISP 3: app/frontend/lib/components/Button.test.ts
import { render, screen } from '@testing-library/svelte'
import { createRawSnippet } from 'svelte'
import { describe, expect, it } from 'vitest'

import Button from './Button.svelte'

const children = createRawSnippet(() => ({ render: () => '<span>Edit</span>' }))
const classes = (className?: string) => {
  render(Button, { class: className, children })
  return screen.getByRole('button').className.split(/\s+/)
}

describe('Button', () => {
  it('has the default padding and text size', () => {
    expect(classes()).toEqual(expect.arrayContaining(['px-4', 'py-2', 'text-sm']))
  })

  it('takes a class setting them in place of the defaults', () => {
    const list = classes('px-2 py-1 text-xs')
    expect(list).toEqual(expect.arrayContaining(['px-2', 'py-1', 'text-xs']))
    expect(list).not.toContain('px-4')
    expect(list).not.toContain('py-2')
    expect(list).not.toContain('text-sm')
  })

  it('keeps the defaults beside a class that sets them only at some widths', () => {
    expect(classes('md:px-2')).toEqual(expect.arrayContaining(['px-4', 'py-2', 'md:px-2']))
  })
})
