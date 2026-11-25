// Ported from WISP 3 (adapted): app/frontend/lib/components/TextField.test.ts
import { render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'

import TextField from './TextField.svelte'

describe('TextField', () => {
  it('labels the input and submits under the given name', () => {
    render(TextField, { label: 'Email', name: 'email', value: 'pat@example.com' })
    const input = screen.getByLabelText('Email')
    expect(input).toHaveAttribute('name', 'email')
    expect(input).toHaveValue('pat@example.com')
  })

  it('shows the first server error and marks the input invalid', () => {
    render(TextField, {
      label: 'Email',
      name: 'email',
      error: ['Enter your email address.', 'Enter a valid email address.'],
      hint: 'ignored',
    })
    const input = screen.getByLabelText('Email')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAccessibleDescription('Enter your email address.')
    expect(screen.queryByText('Enter a valid email address.')).not.toBeInTheDocument()
  })

  it('shows the hint when there is no error', () => {
    render(TextField, { label: 'Password', name: 'password', hint: 'At least 8 characters' })
    expect(screen.getByLabelText('Password')).toHaveAccessibleDescription('At least 8 characters')
  })
})
