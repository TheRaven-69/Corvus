import { useState, type FormEvent } from 'react'

import { getCurrentUser, login, type User } from '../../api/auth'
import { ApiError } from '../../api/http'

type LoginFormProps = {
  initialLogin?: string
  successMessage?: string | null
  onAuthenticated: (user: User) => void
}

function readableLoginError(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) {
    return 'Incorrect email, username, or password.'
  }

  if (error instanceof ApiError) {
    return `The server could not complete the request: ${error.message}`
  }

  return 'Could not connect to the server. Please try again.'
}

export function LoginForm({
  initialLogin = '',
  successMessage = null,
  onAuthenticated,
}: LoginFormProps) {
  const [loginValue, setLoginValue] = useState(initialLogin)
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)
    setIsSubmitting(true)

    try {
      const token = await login({ login: loginValue, password })
      const user = await getCurrentUser(token.access_token)
      onAuthenticated(user)
    } catch (error) {
      setErrorMessage(readableLoginError(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <p className="eyebrow">Your training space</p>
      <h2>Sign in to Corvus</h2>
      <p className="auth-card__hint">
        Use the email or username you chose during registration.
      </p>

      {successMessage ? (
        <p className="form-success" role="status">
          {successMessage}
        </p>
      ) : null}

      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="login">Email or username</label>
          <input
            id="login"
            name="login"
            value={loginValue}
            onChange={(event) => setLoginValue(event.target.value)}
            autoComplete="username"
            required
            maxLength={320}
          />
        </div>

        <div className="form-field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
            maxLength={128}
          />
        </div>

        {errorMessage ? (
          <p className="form-error" role="alert">
            {errorMessage}
          </p>
        ) : null}

        <button className="submit-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </>
  )
}
