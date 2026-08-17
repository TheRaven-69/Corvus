import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { User } from '../../api/auth'
import { LoginForm } from './LoginForm'
import { RegisterForm } from './RegisterForm'

type AuthMode = 'login' | 'register'

type AuthPanelProps = {
  onAuthenticated: (user: User) => void
}

export function AuthPanel({ onAuthenticated }: AuthPanelProps) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<AuthMode>('login')
  const [registeredUsername, setRegisteredUsername] = useState('')

  function showLoginAfterRegistration(username: string) {
    setRegisteredUsername(username)
    setMode('login')
  }

  return (
    <>
      <div className="auth-tabs" aria-label={t('auth.tabsLabel')}>
        <button
          type="button"
          className={mode === 'login' ? 'auth-tab auth-tab--active' : 'auth-tab'}
          aria-label={t('auth.showLogin')}
          aria-pressed={mode === 'login'}
          onClick={() => setMode('login')}
        >
          {t('auth.signIn')}
        </button>
        <button
          type="button"
          className={
            mode === 'register' ? 'auth-tab auth-tab--active' : 'auth-tab'
          }
          aria-label={t('auth.showRegistration')}
          aria-pressed={mode === 'register'}
          onClick={() => setMode('register')}
        >
          {t('auth.register')}
        </button>
      </div>

      {mode === 'login' ? (
        <div className="auth-view" key="login">
          <LoginForm
            initialLogin={registeredUsername}
            successMessage={
              registeredUsername
                ? t('auth.accountCreated')
                : null
            }
            onAuthenticated={onAuthenticated}
          />
        </div>
      ) : (
        <div className="auth-view" key="register">
          <h2>{t('auth.registration.title')}</h2>
          <p className="auth-card__hint">{t('auth.registration.hint')}</p>
          <RegisterForm onRegistered={showLoginAfterRegistration} />
        </div>
      )}
    </>
  )
}
