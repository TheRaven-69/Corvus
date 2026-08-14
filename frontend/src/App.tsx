import { useEffect, useState } from 'react'

import {
  logout,
  restoreCurrentUser,
  type User,
} from './api/auth'
import { AuthPanel } from './features/auth/AuthPanel'
import { Dashboard } from './features/dashboard/Dashboard'
import './App.css'

function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [isCheckingSession, setIsCheckingSession] = useState(true)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)

  useEffect(() => {
    let isCancelled = false

    async function restoreSession() {
      try {
        const user = await restoreCurrentUser()

        if (!isCancelled) {
          setCurrentUser(user)
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
      setCurrentUser(null)
    } catch {
      setLogoutError('Could not log out. Check your connection and try again.')
    } finally {
      setIsLoggingOut(false)
    }
  }

  if (!isCheckingSession && currentUser) {
    return (
      <Dashboard
        currentUser={currentUser}
        isLoggingOut={isLoggingOut}
        logoutError={logoutError}
        onLogout={handleLogout}
      />
    )
  }

  return (
    <main className="app-shell">
      <section className="intro" aria-labelledby="welcome-title">
        <p className="eyebrow">Corvus</p>
        <h1 id="welcome-title">Training without the clutter</h1>
        <p className="intro__copy">
          Plan your workouts, record completed sets, and follow your progress
          in one focused place.
        </p>
      </section>

      <section className="auth-card" aria-live="polite">
        {isCheckingSession ? (
          <div className="session-loading" role="status">
            <span className="spinner" aria-hidden="true" />
            <p>Checking your session…</p>
          </div>
        ) : (
          <AuthPanel onAuthenticated={setCurrentUser} />
        )}
      </section>
    </main>
  )
}

export default App
