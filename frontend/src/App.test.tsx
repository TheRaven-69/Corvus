import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import i18n from './i18n'

const userResponse = {
  id: '7bed0f31-0bb0-4957-881b-3c57aa2a8044',
  email: 'vadim@example.com',
  username: 'vadim',
  first_name: 'Vadim',
  last_name: 'Test',
  created_at: '2026-08-12T12:00:00Z',
}

const tokenResponse = {
  access_token: 'access-token',
  token_type: 'bearer',
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

beforeEach(async () => {
  window.localStorage.clear()
  document.documentElement.lang = 'en'
  await i18n.changeLanguage('en')
})

describe('authentication flow', () => {
  it('switches to Ukrainian and remembers the selected language', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse({ detail: 'Invalid refresh token' }, 401),
    )

    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: 'Ukrainian' }),
    )

    expect(
      await screen.findByRole('heading', { name: 'Тренування без хаосу' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Українська' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(document.documentElement).toHaveAttribute('lang', 'uk')
    expect(window.localStorage.getItem('corvus.language')).toBe('uk')
  })

  it('restores an existing session when the application opens', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(tokenResponse))
      .mockResolvedValueOnce(jsonResponse(userResponse))

    render(<App />)

    expect(screen.getByText('Checking your session…')).toBeInTheDocument()
    expect(await screen.findByText('Good to see you, Vadim')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'http://localhost:8000/auth/refresh',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'http://localhost:8000/auth/me',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token',
        }),
      }),
    )
  })

  it('logs in and shows the authenticated user', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        jsonResponse({ detail: 'Invalid refresh token' }, 401),
      )
      .mockResolvedValueOnce(jsonResponse(tokenResponse))
      .mockResolvedValueOnce(jsonResponse(userResponse))

    render(<App />)

    await user.type(
      await screen.findByLabelText(/email or username/i),
      'vadim',
    )
    await user.type(screen.getByLabelText('Password'), 'strong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Good to see you, Vadim')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'http://localhost:8000/auth/login',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          login: 'vadim',
          password: 'strong-password',
        }),
      }),
    )
  })

  it('shows a useful message for invalid credentials', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        jsonResponse({ detail: 'Invalid refresh token' }, 401),
      )
      .mockResolvedValueOnce(
        jsonResponse({ detail: 'Invalid credentials' }, 401),
      )

    render(<App />)

    await user.type(
      await screen.findByLabelText(/email or username/i),
      'unknown@example.com',
    )
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Incorrect email, username, or password.',
    )
  })

  it('registers a user and returns to a prefilled login form', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        jsonResponse({ detail: 'Invalid refresh token' }, 401),
      )
      .mockResolvedValueOnce(jsonResponse(userResponse, 201))

    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: 'Show registration form' }),
    )
    await user.type(screen.getByLabelText('First name'), 'Vadim')
    await user.type(screen.getByLabelText('Last name'), 'Test')
    await user.type(screen.getByLabelText('Email'), 'vadim@example.com')
    await user.type(screen.getByLabelText('Username'), 'vadim')
    await user.type(screen.getByLabelText('Password'), 'strong-password')
    await user.type(
      screen.getByLabelText('Confirm password'),
      'strong-password',
    )
    await user.click(
      screen.getByRole('button', { name: 'Create account' }),
    )

    expect(
      await screen.findByText('Account created. You can now sign in to Corvus.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/email or username/i)).toHaveValue('vadim')
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'http://localhost:8000/auth/register',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          email: 'vadim@example.com',
          username: 'vadim',
          first_name: 'Vadim',
          last_name: 'Test',
          password: 'strong-password',
        }),
      }),
    )
  })

  it('does not register when password confirmation differs', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse({ detail: 'Invalid refresh token' }, 401),
    )

    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: 'Show registration form' }),
    )
    await user.type(screen.getByLabelText('First name'), 'Vadim')
    await user.type(screen.getByLabelText('Last name'), 'Test')
    await user.type(screen.getByLabelText('Email'), 'vadim@example.com')
    await user.type(screen.getByLabelText('Username'), 'vadim')
    await user.type(screen.getByLabelText('Password'), 'strong-password')
    await user.type(
      screen.getByLabelText('Confirm password'),
      'different-password',
    )
    await user.click(
      screen.getByRole('button', { name: 'Create account' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Passwords do not match.',
    )
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('logs out and returns to the login form', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(tokenResponse))
      .mockResolvedValueOnce(jsonResponse(userResponse))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Log out' }))

    expect(
      await screen.findByRole('heading', { name: 'Sign in to Corvus' }),
    ).toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      'http://localhost:8000/auth/logout',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
  })
})
