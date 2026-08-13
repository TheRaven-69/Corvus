import { useState } from 'react'

import type { User } from '../../api/auth'
import { LoginForm } from './LoginForm'
import { RegisterForm } from './RegisterForm'

type AuthMode = 'login' | 'register'

type AuthPanelProps = {
  onAuthenticated: (user: User) => void
}

export function AuthPanel({ onAuthenticated }: AuthPanelProps) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [registeredUsername, setRegisteredUsername] = useState('')

  function showLoginAfterRegistration(username: string) {
    setRegisteredUsername(username)
    setMode('login')
  }

  return (
    <>
      <div className="auth-tabs" aria-label="Authentication">
        <button
          type="button"
          className={mode === 'login' ? 'auth-tab auth-tab--active' : 'auth-tab'}
          aria-label="Show sign-in form"
          aria-pressed={mode === 'login'}
          onClick={() => setMode('login')}
        >
          Sign in
        </button>
        <button
          type="button"
          className={
            mode === 'register' ? 'auth-tab auth-tab--active' : 'auth-tab'
          }
          aria-label="Show registration form"
          aria-pressed={mode === 'register'}
          onClick={() => setMode('register')}
        >
          Register
        </button>
      </div>

      {mode === 'login' ? (
        <LoginForm
          initialLogin={registeredUsername}
          successMessage={
            registeredUsername
              ? 'Account created. You can now sign in to Corvus.'
              : null
          }
          onAuthenticated={onAuthenticated}
        />
      ) : (
        <>
          <p className="eyebrow">New account</p>
          <h2>Create your profile</h2>
          <p className="auth-card__hint">
            Fill in the short form to start planning your workouts.
          </p>
          <RegisterForm onRegistered={showLoginAfterRegistration} />
        </>
      )}
    </>
  )
}
