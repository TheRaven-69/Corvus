import { useState, type FormEvent } from 'react'

import { register } from '../../api/auth'
import { ApiError } from '../../api/http'

type RegisterFormProps = {
  onRegistered: (username: string) => void
}

function readableRegistrationError(error: unknown): string {
  if (
    error instanceof ApiError &&
    error.message === 'Email is already registered'
  ) {
    return 'An account with this email already exists.'
  }

  if (
    error instanceof ApiError &&
    error.message === 'Username is already registered'
  ) {
    return 'This username is already taken.'
  }

  if (error instanceof ApiError && error.status === 422) {
    return 'Check that every field is filled in correctly.'
  }

  if (error instanceof ApiError) {
    return `The server could not complete the request: ${error.message}`
  }

  return 'Could not connect to the server. Please try again.'
}

export function RegisterForm({ onRegistered }: RegisterFormProps) {
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [passwordMismatch, setPasswordMismatch] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)

    if (password !== passwordConfirmation) {
      setPasswordMismatch(true)
      setErrorMessage('Passwords do not match.')
      return
    }

    setPasswordMismatch(false)
    setIsSubmitting(true)

    try {
      const user = await register({
        email,
        username,
        first_name: firstName,
        last_name: lastName,
        password,
      })
      onRegistered(user.username)
    } catch (error) {
      setErrorMessage(readableRegistrationError(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="form-row">
        <div className="form-field">
          <label htmlFor="first-name">First name</label>
          <input
            id="first-name"
            name="firstName"
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
            autoComplete="given-name"
            required
            maxLength={50}
          />
        </div>

        <div className="form-field">
          <label htmlFor="last-name">Last name</label>
          <input
            id="last-name"
            name="lastName"
            value={lastName}
            onChange={(event) => setLastName(event.target.value)}
            autoComplete="family-name"
            required
            maxLength={50}
          />
        </div>
      </div>

      <div className="form-field">
        <label htmlFor="register-email">Email</label>
        <input
          id="register-email"
          name="email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
          maxLength={320}
        />
      </div>

      <div className="form-field">
        <label htmlFor="register-username">Username</label>
        <input
          id="register-username"
          name="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          required
          minLength={3}
          maxLength={50}
          pattern="[a-zA-Z0-9_]+"
          title="Use only Latin letters, numbers, and underscores"
        />
        <span className="field-hint">
          3–50 characters: Latin letters, numbers, and underscores.
        </span>
      </div>

      <div className="form-field">
        <label htmlFor="register-password">Password</label>
        <input
          id="register-password"
          name="password"
          type="password"
          value={password}
          onChange={(event) => {
            setPassword(event.target.value)
            setPasswordMismatch(false)
          }}
          autoComplete="new-password"
          aria-describedby={
            passwordMismatch
              ? 'password-requirements registration-error'
              : 'password-requirements'
          }
          aria-invalid={passwordMismatch}
          required
          minLength={8}
          maxLength={128}
        />
        <span className="field-hint" id="password-requirements">
          At least 8 characters.
        </span>
      </div>

      <div className="form-field">
        <label htmlFor="password-confirmation">Confirm password</label>
        <input
          id="password-confirmation"
          name="passwordConfirmation"
          type="password"
          value={passwordConfirmation}
          onChange={(event) => {
            setPasswordConfirmation(event.target.value)
            setPasswordMismatch(false)
          }}
          autoComplete="new-password"
          aria-describedby={passwordMismatch ? 'registration-error' : undefined}
          aria-invalid={passwordMismatch}
          required
          maxLength={128}
        />
      </div>

      {errorMessage ? (
        <p className="form-error" id="registration-error" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <button className="submit-button" type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating account…' : 'Create account'}
      </button>
    </form>
  )
}
