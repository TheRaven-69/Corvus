import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import i18n from './i18n'

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

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

const muscleGroupsResponse = [
  {
    code: 'chest',
    names: { en: 'Chest', uk: 'Груди' },
  },
  {
    code: 'triceps',
    names: { en: 'Triceps', uk: 'Трицепс' },
  },
]

const exerciseResponse = {
  id: '319f4e2f-cd97-4070-8846-85f62b95cb43',
  code: 'barbell_bench_press',
  names: { en: 'Barbell bench press', uk: 'Жим штанги лежачи' },
  muscle_groups: muscleGroupsResponse,
  created_at: '2026-08-22T12:00:00Z',
  updated_at: '2026-08-22T12:00:00Z',
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
      `${apiBaseUrl}/auth/refresh`,
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `${apiBaseUrl}/auth/me`,
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
      `${apiBaseUrl}/auth/login`,
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
      `${apiBaseUrl}/auth/register`,
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
      `${apiBaseUrl}/auth/logout`,
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
  })
})

describe('exercise catalog', () => {
  it('loads protected exercise URLs and shows localized catalog data', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(tokenResponse))
      .mockResolvedValueOnce(jsonResponse(userResponse))
      .mockResolvedValueOnce(jsonResponse([exerciseResponse]))
      .mockResolvedValueOnce(jsonResponse(muscleGroupsResponse))

    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: 'Exercises' }),
    )

    expect(
      await screen.findByRole('heading', { name: 'Barbell bench press' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Chest')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `${apiBaseUrl}/exercises`,
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token',
        }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      `${apiBaseUrl}/muscle-groups`,
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token',
        }),
      }),
    )
  })

  it('creates a personal exercise with the current locale and selected groups', async () => {
    const user = userEvent.setup()
    const customExercise = {
      ...exerciseResponse,
      id: 'a36df674-59bb-4713-8f65-9fd2bc51bc8d',
      code: null,
      names: { en: 'Incline dumbbell press' },
      muscle_groups: [muscleGroupsResponse[0]],
    }
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(tokenResponse))
      .mockResolvedValueOnce(jsonResponse(userResponse))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(muscleGroupsResponse))
      .mockResolvedValueOnce(jsonResponse(customExercise, 201))

    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: 'Exercises' }),
    )
    await screen.findByText('No exercises yet')
    await user.click(screen.getByRole('button', { name: 'Add exercise' }))
    await user.type(screen.getByLabelText('Exercise name'), 'Incline dumbbell press')
    await user.click(screen.getByRole('checkbox', { name: 'Chest' }))
    await user.click(screen.getByRole('button', { name: 'Create exercise' }))

    expect(
      await screen.findByText('“Incline dumbbell press” was added to your catalog.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Your exercise')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      `${apiBaseUrl}/exercises`,
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          name: 'Incline dumbbell press',
          locale: 'en',
          muscle_group_codes: ['chest'],
        }),
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token',
        }),
      }),
    )
  })

  it('keeps form input and explains missing muscle-group validation', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(tokenResponse))
      .mockResolvedValueOnce(jsonResponse(userResponse))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(muscleGroupsResponse))

    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: 'Exercises' }),
    )
    await screen.findByText('No exercises yet')
    await user.click(screen.getByRole('button', { name: 'Add exercise' }))
    await user.type(screen.getByLabelText('Exercise name'), 'Cable fly')
    await user.click(screen.getByRole('button', { name: 'Create exercise' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Select at least one muscle group.',
    )
    const muscleGroup = screen.getByRole('group', { name: 'Muscle groups' })
    expect(muscleGroup).toHaveAttribute('aria-invalid', 'true')
    expect(muscleGroup).toHaveAttribute(
      'aria-describedby',
      'exercise-muscle-groups-hint exercise-muscle-groups-error',
    )
    expect(screen.getByRole('checkbox', { name: 'Chest' })).toHaveFocus()
    expect(screen.getByLabelText('Exercise name')).toHaveValue('Cable fly')
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it('searches across localized names and muscle groups, then offers recovery', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(tokenResponse))
      .mockResolvedValueOnce(jsonResponse(userResponse))
      .mockResolvedValueOnce(jsonResponse([exerciseResponse]))
      .mockResolvedValueOnce(jsonResponse(muscleGroupsResponse))

    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: 'Exercises' }),
    )
    await screen.findByRole('heading', { name: 'Barbell bench press' })
    const searchInput = screen.getByRole('searchbox', {
      name: 'Search exercises',
    })
    await user.type(searchInput, 'bench груди')

    expect(
      screen.getByRole('heading', { name: 'Barbell bench press' }),
    ).toBeInTheDocument()
    expect(screen.getByText('1 of 1 exercises')).toBeInTheDocument()

    await user.clear(searchInput)
    await user.type(searchInput, 'squat')

    expect(screen.getByText('0 of 1 exercises')).toBeInTheDocument()
    expect(screen.getByText('No matching exercises')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Clear search' }))

    expect(
      screen.getByRole('heading', { name: 'Barbell bench press' }),
    ).toBeInTheDocument()
    expect(screen.getByText('1 available exercise')).toBeInTheDocument()
  })

  it('offers a retry when the exercise catalog request fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(tokenResponse))
      .mockResolvedValueOnce(jsonResponse(userResponse))
      .mockResolvedValueOnce(jsonResponse({ detail: 'Unavailable' }, 503))
      .mockResolvedValueOnce(jsonResponse(muscleGroupsResponse))
      .mockResolvedValueOnce(jsonResponse([exerciseResponse]))
      .mockResolvedValueOnce(jsonResponse(muscleGroupsResponse))

    render(<App />)

    await user.click(
      await screen.findByRole('button', { name: 'Exercises' }),
    )
    expect(
      await screen.findByText('The catalog could not be loaded'),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Try again' }))

    expect(
      await screen.findByRole('heading', { name: 'Barbell bench press' }),
    ).toBeInTheDocument()
  })
})
