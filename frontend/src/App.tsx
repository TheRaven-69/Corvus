import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import './App.css'

import {
  logout,
  restoreCurrentSession,
  type AuthenticatedSession,
} from './api/auth'
import { AuthPanel } from './features/auth/AuthPanel'
import { Dashboard } from './features/dashboard/Dashboard'
import { CorvusBrand } from './components/CorvusBrand'
import { LanguageSwitcher } from './components/LanguageSwitcher'

function App() {
  const { t } = useTranslation()
  const [session, setSession] = useState<AuthenticatedSession | null>(null)
  const [isCheckingSession, setIsCheckingSession] = useState(true)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)

  useEffect(() => {
    let isCancelled = false

    async function restoreSession() {
      try {
        const restoredSession = await restoreCurrentSession()

        if (!isCancelled) {
          setSession(restoredSession)
        }
      } catch {
        // A missing or expired refresh cookie means the user is signed out.
      } finally {
        if (!isCancelled) {
          setIsCheckingSession(false)
        }
      }
    }

    void restoreSession()

    return () => {
      isCancelled = true
    }
  }, [])

  async function handleLogout() {
    setLogoutError(null)
    setIsLoggingOut(true)

    try {
      await logout()
      setSession(null)
    } catch {
      setLogoutError(t('auth.errors.logout'))
    } finally {
      setIsLoggingOut(false)
    }
  }

  const handleAccessTokenChange = useCallback((accessToken: string) => {
    setSession((currentSession) =>
      currentSession
        ? { ...currentSession, accessToken }
        : currentSession,
    )
  }, [])

  const handleSessionExpired = useCallback(() => {
    setSession(null)
  }, [])

  if (!isCheckingSession && session) {
    return (
      <Dashboard
        accessToken={session.accessToken}
        currentUser={session.user}
        isLoggingOut={isLoggingOut}
        logoutError={logoutError}
        onAccessTokenChange={handleAccessTokenChange}
        onLogout={handleLogout}
        onSessionExpired={handleSessionExpired}
      />
    )
  }

  return (
    <main className="app-shell">
      <section className="intro" aria-labelledby="welcome-title">
        <div className="intro__topline">
          <CorvusBrand />
          <LanguageSwitcher />
        </div>
        <div className="intro__body">
          <h1 id="welcome-title">{t('landing.title')}</h1>
          <p className="intro__copy">{t('landing.copy')}</p>
        </div>
        <span className="intro__measure" aria-hidden="true" />
      </section>

      <section className="auth-card" aria-live="polite">
        {isCheckingSession ? (
          <div className="session-loading" role="status">
            <span className="spinner" aria-hidden="true" />
            <p>{t('landing.checkingSession')}</p>
          </div>
        ) : (
          <AuthPanel onAuthenticated={setSession} />
        )}
      </section>
    </main>
  )
}

export default App
