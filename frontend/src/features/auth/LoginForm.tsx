import { useState, type FormEvent } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import { getCurrentUser, login, type User } from '../../api/auth'
import { ApiError } from '../../api/http'

type LoginFormProps = {
  initialLogin?: string
  successMessage?: string | null
  onAuthenticated: (user: User) => void
}

function readableLoginError(error: unknown, t: TFunction): string {
  if (error instanceof ApiError && error.status === 401) {
    return t('auth.errors.invalidCredentials')
  }

  if (error instanceof ApiError) {
    return t('auth.errors.server', { message: error.message })
  }

  return t('auth.errors.connection')
}

export function LoginForm({
  initialLogin = '',
  successMessage = null,
  onAuthenticated,
}: LoginFormProps) {
  const { t } = useTranslation()
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
      setErrorMessage(readableLoginError(error, t))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <h2>{t('auth.login.title')}</h2>
      <p className="auth-card__hint">{t('auth.login.hint')}</p>

      {successMessage ? (
        <p className="form-success" role="status">
          {successMessage}
        </p>
      ) : null}

      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="login">{t('auth.login.loginLabel')}</label>
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
          <label htmlFor="password">{t('auth.login.passwordLabel')}</label>
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
          {isSubmitting ? t('auth.login.submitting') : t('auth.signIn')}
        </button>
      </form>
    </>
  )
}
