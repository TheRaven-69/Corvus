import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import i18n from '../../i18n'
import { Dashboard } from './Dashboard'

afterEach(cleanup)

it('toggles the menu with the keyboard without changing the current page', async () => {
  await i18n.changeLanguage('en')
  const user = userEvent.setup()
  render(<Dashboard accessToken="test" currentUser={{id:'test', username:'tester', first_name:'Test', last_name:'User', email:'test@example.invalid', created_at:''}} isLoggingOut={false} logoutError={null} onAccessTokenChange={vi.fn()} onSessionExpired={vi.fn()} onLogout={vi.fn()} />)
  const toggle = screen.getByRole('button', {name:'Hide menu'})
  expect(toggle).toHaveAttribute('aria-expanded', 'true')
  expect(document.getElementById(toggle.getAttribute('aria-controls')!)).not.toBeNull()
  toggle.focus()
  await user.keyboard('{Enter}')
  expect(screen.getByRole('button', {name:'Show menu'})).toHaveAttribute('aria-expanded', 'false')
  expect(toggle).toHaveFocus()
  expect(screen.getByRole('button', {name:'Templates'})).toBeInTheDocument()
  expect(screen.getByRole('button', {name:'Log out'})).toBeInTheDocument()
  expect(screen.getByRole('heading', {name:'Good to see you, Test'})).toBeInTheDocument()
  await user.keyboard(' ')
  expect(toggle).toHaveAttribute('aria-expanded', 'true')
})
