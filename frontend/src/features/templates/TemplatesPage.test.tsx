import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import i18n from '../../i18n'
import type { TemplateInput, WorkoutTemplate } from '../../api/workoutTemplates'
import { TemplatesPage } from './TemplatesPage'
import { Dashboard } from '../dashboard/Dashboard'

const bench = {
  id: 'bench',
  code: 'bench',
  names: { en: 'Bench press', uk: 'Жим лежачи' },
  muscle_groups: [],
  created_at: '',
  updated_at: '',
}
const squat = {
  ...bench,
  id: 'squat',
  code: 'squat',
  names: { en: 'Squat', uk: 'Присідання' },
}
const template: WorkoutTemplate = {
  id: 'plan',
  name: 'Push day',
  description: 'Chest and triceps',
  created_at: '',
  updated_at: '',
  exercises: [
    {
      id: 'plan-ex',
      exercise_id: bench.id,
      exercise: bench,
      position: 0,
      notes: 'Slow tempo',
      sets: [
        {
          id: 'set',
          position: 0,
          set_type: 'working',
          target_reps: 8,
          target_weight_kg: '42.50',
        },
      ],
    },
  ],
}
const props = {
  accessToken: 'token',
  onAccessTokenChange: vi.fn(),
  onSessionExpired: vi.fn(),
  onDirtyChange: vi.fn(),
  onBusyChange: vi.fn(),
}
function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
function setupApi(list: WorkoutTemplate[] = []) {
  return vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation(async (url, options) => {
      const path = String(url)
      if (path.endsWith('/exercises')) return json([bench, squat])
      if (options?.method === 'DELETE')
        return new Response(null, { status: 204 })
      if (options?.method === 'POST' || options?.method === 'PATCH') {
        const data = JSON.parse(String(options.body)) as Partial<TemplateInput>
        return json({
          ...template,
          ...data,
          exercises:
            data.exercises?.map((ex, index) => ({
              ...ex,
              id: `ex-${index}`,
              exercise: ex.exercise_id === bench.id ? bench : squat,
              sets: ex.sets.map((set, i) => ({ ...set, id: `s-${i}` })),
            })) ?? template.exercises,
        })
      }
      return json(list)
    })
}
beforeEach(async () => {
  vi.clearAllMocks()
  await i18n.changeLanguage('en')
})
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('workout templates', () => {
  it('creates a plan with ordered exercises, set types and decimal weights', async () => {
    const fetch = setupApi()
    const user = userEvent.setup()
    render(<TemplatesPage {...props} />)
    await screen.findByText('Your first training plan starts here')
    await user.click(
      screen.getAllByRole('button', { name: 'Create template' })[0],
    )
    await user.click(screen.getByRole('button', { name: 'Add exercise' }))
    expect(screen.getByRole('searchbox', { name: 'Add exercise' })).toHaveFocus()
    await user.type(screen.getByLabelText('Template name'), 'Upper body')
    await user.click(screen.getByRole('button', { name: 'Add Bench press' }))
    await user.selectOptions(
      screen.getByLabelText('Exercise 1, set 1 type'),
      'warmup',
    )
    await user.type(
      screen.getByLabelText('Exercise 1, set 1 weight (kg)'),
      '20,50',
    )
    await user.click(screen.getByRole('button', { name: 'Add set' }))
    await user.click(screen.getByRole('button', { name: 'Add Squat' }))
    expect(screen.getByText('2 exercises · 3 planned sets')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Move Squat up' }))
    await user.click(screen.getByRole('button', { name: 'Save template' }))
    await screen.findByText('Template saved.')
    const call = fetch.mock.calls.find(([, init]) => init?.method === 'POST')!
    const body = JSON.parse(String(call[1]?.body))
    expect(body).toMatchObject({
      name: 'Upper body',
      description: null,
      exercises: [
        {
          exercise_id: 'squat',
          position: 0,
          sets: [{ position: 0, target_reps: 8, target_weight_kg: null }],
        },
        {
          exercise_id: 'bench',
          position: 1,
          sets: [
            { position: 0, set_type: 'warmup', target_weight_kg: '20.50' },
            { position: 1, set_type: 'working', target_weight_kg: null },
          ],
        },
      ],
    })
    expect(call[1]?.headers).toMatchObject({ Authorization: 'Bearer token' })
    expect(body).not.toHaveProperty('user_id')
    expect(
      screen.getByRole('heading', { name: 'Upper body' }),
    ).toBeInTheDocument()
  })

  it('changes only metadata without replacing exercise history identifiers', async () => {
    const fetch = setupApi([template])
    const user = userEvent.setup()
    render(<TemplatesPage {...props} />)
    await user.click(
      await screen.findByRole('button', { name: 'Edit Push day' }),
    )
    expect(screen.getByLabelText('Exercise 1, set 1 weight (kg)')).toHaveValue(
      '42.50',
    )
    await user.clear(screen.getByLabelText('Template name'))
    await user.type(screen.getByLabelText('Template name'), 'Push A')
    await user.clear(screen.getByLabelText('Description (optional)'))
    await user.click(screen.getByRole('button', { name: 'Save template' }))
    await screen.findByText('Template saved.')
    const call = fetch.mock.calls.find(([, init]) => init?.method === 'PATCH')!
    expect(JSON.parse(String(call[1]?.body))).toEqual({
      name: 'Push A',
      description: null,
    })
  })

  it('keeps valid edited values after a failed save and retries', async () => {
    const fetch = setupApi([template])
    const user = userEvent.setup()
    render(<TemplatesPage {...props} />)
    await user.click(
      await screen.findByRole('button', { name: 'Edit Push day' }),
    )
    await user.type(screen.getByLabelText('Template name'), ' B')
    fetch.mockResolvedValueOnce(json({ detail: 'Unavailable exercises' }, 422))
    await user.click(screen.getByRole('button', { name: 'Save template' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Some targets or exercises',
    )
    expect(screen.getByLabelText('Template name')).toHaveValue('Push day B')
    await user.click(screen.getByRole('button', { name: 'Save template' }))
    await screen.findByText('Template saved.')
  })

  it('rejects invalid weight and protects an unsaved draft when cancelled', async () => {
    const fetch = setupApi([template])
    const user = userEvent.setup()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<TemplatesPage {...props} />)
    await user.click(
      await screen.findByRole('button', { name: 'Edit Push day' }),
    )
    await user.clear(screen.getByLabelText('Exercise 1, set 1 weight (kg)'))
    await user.type(
      screen.getByLabelText('Exercise 1, set 1 weight (kg)'),
      '-1',
    )
    await user.click(screen.getByRole('button', { name: 'Save template' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Check the highlighted fields',
    )
    const invalidWeight = screen.getByLabelText('Exercise 1, set 1 weight (kg)')
    expect(invalidWeight).toHaveAttribute('aria-invalid', 'true')
    expect(invalidWeight).toHaveAccessibleDescription(
      'Enter 0–999999.99 kg, with at most two decimal places, or leave this empty.',
    )
    expect(invalidWeight).toHaveFocus()
    expect(fetch.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(
      false,
    )
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(confirm).toHaveBeenCalled()
    expect(screen.getByLabelText('Template name')).toBeInTheDocument()
    confirm.mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByLabelText('Template name')).not.toBeInTheDocument()
  })

  it('requires confirmation before deletion and handles 204', async () => {
    const fetch = setupApi([template])
    const user = userEvent.setup()
    render(<TemplatesPage {...props} />)
    await user.click(
      await screen.findByRole('button', { name: 'Delete Push day' }),
    )
    expect(fetch.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(
      false,
    )
    const confirmation = screen.getByRole('group', { name: 'Delete Push day' })
    await user.click(
      within(confirmation).getByRole('button', { name: 'Delete template' }),
    )
    await screen.findByText('Template deleted.')
    expect(
      screen.queryByRole('heading', { name: 'Push day' }),
    ).not.toBeInTheDocument()
  })

  it('recovers from list failures', async () => {
    const fetch = setupApi()
    fetch.mockResolvedValueOnce(json({}, 500))
    const user = userEvent.setup()
    render(<TemplatesPage {...props} />)
    await user.click(await screen.findByRole('button', { name: 'Try again' }))
    await screen.findByText('Your first training plan starts here')
  })

  it('expires the session if refreshing authentication fails', async () => {
    setupApi().mockResolvedValue(json({}, 401))
    render(<TemplatesPage {...props} />)
    await waitFor(() => expect(props.onSessionExpired).toHaveBeenCalled())
  })

  it('uses Ukrainian names and interface copy', async () => {
    setupApi([template])
    await i18n.changeLanguage('uk')
    render(<TemplatesPage {...props} />)
    expect(await screen.findByText('Жим лежачи')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Створити шаблон' }),
    ).toBeInTheDocument()
    expect(screen.getByText('1 запланований підхід')).toBeInTheDocument()
  })

  it.each([403, 404])(
    'retains the draft when the API returns %s',
    async (status) => {
      const fetch = setupApi([template])
      const user = userEvent.setup()
      render(<TemplatesPage {...props} />)
      await user.click(
        await screen.findByRole('button', { name: 'Edit Push day' }),
      )
      await user.type(screen.getByLabelText('Template name'), ' B')
      fetch.mockResolvedValueOnce(json({}, status))
      await user.click(screen.getByRole('button', { name: 'Save template' }))
      expect(await screen.findByRole('alert')).toHaveTextContent(
        status === 403 ? 'permission' : 'no longer available',
      )
      expect(screen.getByLabelText('Template name')).toHaveValue('Push day B')
    },
  )

  it('sends the complete remaining plan when removing a set', async () => {
    const fetch = setupApi([
      {
        ...template,
        exercises: [
          {
            ...template.exercises[0],
            sets: [
              {
                ...template.exercises[0].sets[0],
                id: 'warmup',
                set_type: 'warmup',
                position: 0,
              },
              { ...template.exercises[0].sets[0], id: 'working', position: 1 },
            ],
          },
        ],
      },
    ])
    const user = userEvent.setup()
    render(<TemplatesPage {...props} />)
    await user.click(
      await screen.findByRole('button', { name: 'Edit Push day' }),
    )
    await user.click(
      screen.getByRole('button', { name: 'Remove exercise 1, set 1' }),
    )
    await user.click(screen.getByRole('button', { name: 'Save template' }))
    await screen.findByText('Template saved.')
    const call = fetch.mock.calls.find(([, init]) => init?.method === 'PATCH')!
    expect(JSON.parse(String(call[1]?.body))).toEqual({
      exercises: [
        {
          exercise_id: 'bench',
          position: 0,
          notes: 'Slow tempo',
          sets: [
            {
              position: 0,
              set_type: 'working',
              target_reps: 8,
              target_weight_kg: '42.50',
            },
          ],
        },
      ],
    })
  })

  it('warns before navigating away from unsaved changes', async () => {
    setupApi([template])
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    render(
      <Dashboard
        accessToken="token"
        currentUser={{
          id: 'user',
          first_name: 'Test',
          last_name: 'User',
          username: 'test',
          email: 'test@example.invalid',
          created_at: '',
        }}
        isLoggingOut={false}
        logoutError={null}
        onAccessTokenChange={props.onAccessTokenChange}
        onSessionExpired={props.onSessionExpired}
        onLogout={vi.fn()}
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Templates' }))
    await user.click(
      await screen.findByRole('button', { name: 'Edit Push day' }),
    )
    await user.type(screen.getByLabelText('Template name'), ' B')
    await user.click(screen.getByRole('button', { name: 'Dashboard' }))
    expect(confirm).toHaveBeenCalled()
    expect(screen.getByLabelText('Template name')).toHaveValue('Push day B')
    confirm.mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: 'Dashboard' }))
    expect(screen.queryByLabelText('Template name')).not.toBeInTheDocument()
  })

  it('restores keyboard focus after removing a middle or last set and the last exercise', async () => {
    setupApi([
      {
        ...template,
        exercises: [
          {
            ...template.exercises[0],
            sets: [0, 1, 2].map((position) => ({
              ...template.exercises[0].sets[0],
              id: `set-${position}`,
              position,
            })),
          },
        ],
      },
    ])
    const user = userEvent.setup()
    render(<TemplatesPage {...props} />)
    await user.click(
      await screen.findByRole('button', { name: 'Edit Push day' }),
    )
    screen.getByRole('button', { name: 'Remove exercise 1, set 2' }).focus()
    await user.keyboard('{Enter}')
    expect(screen.getByLabelText('Exercise 1, set 2 reps')).toHaveFocus()
    expect(screen.getByRole('status')).toHaveTextContent(
      'Set 2 removed from Bench press.',
    )
    screen.getByRole('button', { name: 'Remove exercise 1, set 2' }).focus()
    await user.keyboard('{Enter}')
    expect(screen.getByLabelText('Exercise 1, set 1 reps')).toHaveFocus()
    screen.getByRole('button', { name: 'Remove Bench press' }).focus()
    await user.keyboard('{Enter}')
    expect(
      screen.getByRole('searchbox', { name: 'Add exercise' }),
    ).toHaveFocus()
  })

  it('validates required name, exercises and reps with linked errors', async () => {
    const fetch = setupApi()
    const user = userEvent.setup()
    render(<TemplatesPage {...props} />)
    await screen.findByText('Your first training plan starts here')
    await user.click(
      screen.getAllByRole('button', { name: 'Create template' })[0],
    )
    await user.click(screen.getByRole('button', { name: 'Save template' }))
    expect(screen.getByLabelText('Template name')).toHaveFocus()
    expect(screen.getByLabelText('Template name')).toHaveAccessibleDescription(
      'Enter a template name (1–120 characters).',
    )
    await user.type(screen.getByLabelText('Template name'), 'Plan')
    expect(screen.getByLabelText('Template name')).not.toHaveAttribute(
      'aria-invalid',
    )
    await user.click(screen.getByRole('button', { name: 'Save template' }))
    expect(
      screen.getByRole('searchbox', { name: 'Add exercise' }),
    ).toHaveFocus()
    await user.click(screen.getByRole('button', { name: 'Add Bench press' }))
    await user.clear(screen.getByLabelText('Exercise 1, set 1 reps'))
    await user.click(screen.getByRole('button', { name: 'Save template' }))
    expect(screen.getByLabelText('Exercise 1, set 1 reps')).toHaveFocus()
    expect(
      screen.getByLabelText('Exercise 1, set 1 reps'),
    ).toHaveAccessibleDescription('Enter a positive whole number of reps.')
    expect(fetch.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(
      false,
    )
  })
})
