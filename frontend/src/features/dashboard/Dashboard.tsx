import type { ReactNode } from 'react'

import type { User } from '../../api/auth'

type DashboardProps = {
  currentUser: User
  isLoggingOut: boolean
  logoutError: string | null
  onLogout: () => void
}

type IconName =
  | 'calendar'
  | 'dashboard'
  | 'dumbbell'
  | 'exercise'
  | 'history'
  | 'progress'
  | 'search'
  | 'settings'
  | 'user'

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    calendar: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="3" />
        <path d="M8 3v4M16 3v4M3 10h18" />
      </>
    ),
    dashboard: (
      <>
        <path d="M4 11 12 4l8 7v9a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1Z" />
      </>
    ),
    dumbbell: <path d="M6 8v8M3.5 9.5v5M18 8v8M20.5 9.5v5M6 12h12" />,
    exercise: (
      <>
        <rect x="4" y="6" width="16" height="13" rx="3" />
        <path d="M9 6V4h6v2M8 11h8" />
      </>
    ),
    history: (
      <>
        <path d="M4 12a8 8 0 1 0 2.35-5.65L4 8.7" />
        <path d="M4 4v4.7h4.7M12 8v4l2.5 1.5" />
      </>
    ),
    progress: <path d="M4 19V9M10 19V5M16 19v-7M22 19H2" />,
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 4.5 4.5" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19 12a7 7 0 0 0-.13-1.34l2-1.55-2-3.46-2.47 1a7 7 0 0 0-2.32-1.34L13.7 3h-4l-.38 2.31A7 7 0 0 0 7 6.65l-2.47-1-2 3.46 2 1.55A7 7 0 0 0 4.4 12c0 .46.04.91.13 1.34l-2 1.55 2 3.46 2.47-1a7 7 0 0 0 2.32 1.34L9.7 21h4l.38-2.31a7 7 0 0 0 2.32-1.34l2.47 1 2-3.46-2-1.55c.09-.43.13-.88.13-1.34Z" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="3" />
        <path d="M5 20v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2" />
      </>
    ),
  }

  return (
    <svg
      className="dashboard-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  )
}

const trainingLinks: Array<{ icon: IconName; label: string }> = [
  { icon: 'dumbbell', label: 'Workouts' },
  { icon: 'calendar', label: 'Templates' },
  { icon: 'exercise', label: 'Exercises' },
  { icon: 'history', label: 'Sessions' },
  { icon: 'history', label: 'History' },
  { icon: 'progress', label: 'Progress' },
]

export function Dashboard({
  currentUser,
  isLoggingOut,
  logoutError,
  onLogout,
}: DashboardProps) {
  return (
    <div className="fitness-dashboard">
      <aside className="fitness-sidebar">
        <div className="fitness-brand">
          <span className="fitness-brand__bird" aria-hidden="true">C</span>
          <span>CORVUS</span>
        </div>

        <nav className="fitness-nav" aria-label="Primary navigation">
          <a className="fitness-nav__link fitness-nav__link--active" href="#dashboard">
            <Icon name="dashboard" />
            Dashboard
          </a>

          <p className="fitness-nav__label">Training</p>
          {trainingLinks.map((link) => (
            <span className="fitness-nav__link fitness-nav__link--disabled" aria-disabled="true" key={link.label}>
              <Icon name={link.icon} />
              {link.label}
            </span>
          ))}
        </nav>

        <div className="fitness-sidebar__footer">
          <span className="fitness-nav__link fitness-nav__link--disabled" aria-disabled="true">
            <Icon name="settings" />
            Settings
          </span>
          <div className="fitness-profile">
            <span className="fitness-profile__avatar" aria-hidden="true">
              {currentUser.first_name.charAt(0).toUpperCase()}
            </span>
            <div>
              <strong>{currentUser.first_name} {currentUser.last_name}</strong>
              <span>@{currentUser.username}</span>
            </div>
            <button type="button" disabled={isLoggingOut} onClick={onLogout}>
              {isLoggingOut ? 'Leaving…' : 'Log out'}
            </button>
          </div>
        </div>
      </aside>

      <main className="fitness-main" id="dashboard">
        <header className="fitness-topbar">
          <div>
            <p>Dashboard</p>
            <h1>Good to see you, {currentUser.first_name}</h1>
            <span>Ready to make today count?</span>
          </div>
          <div className="fitness-topbar__actions">
            <button className="icon-action" type="button" disabled aria-label="Search coming soon">
              <Icon name="search" />
            </button>
            <button className="icon-action" type="button" disabled aria-label="Calendar coming soon">
              <Icon name="calendar" />
            </button>
            <button className="fitness-primary" type="button" disabled title="Workout sessions are not implemented yet">
              + Start workout
            </button>
          </div>
        </header>

        {logoutError ? <p className="form-error fitness-error" role="alert">{logoutError}</p> : null}

        <div className="fitness-grid">
          <section className="dark-card weekly-card" aria-labelledby="week-title">
            <h2 id="week-title"><Icon name="progress" /> This week</h2>
            <div className="weekly-metrics">
              <article><span>Workouts</span><strong>0</strong><small>No sessions yet</small></article>
              <article><span>Volume</span><strong>0 kg</strong><small>Waiting for data</small></article>
              <article><span>Duration</span><strong>0m</strong><small>No training logged</small></article>
              <article><span>Sets</span><strong>0</strong><small>Nothing recorded</small></article>
            </div>
          </section>

          <section className="dark-card up-next-card" aria-labelledby="up-next-title">
            <h2 id="up-next-title"><Icon name="calendar" /> Up next</h2>
            <div className="dark-empty dark-empty--compact">
              <strong>No workout scheduled</strong>
              <p>Create a template to prepare your next session.</p>
              <button type="button" disabled>Create template</button>
            </div>
          </section>

          <section className="dark-card volume-card" aria-labelledby="volume-title">
            <div className="dark-card__heading">
              <h2 id="volume-title">Training volume</h2>
              <span>This week</span>
            </div>
            <div className="volume-chart" aria-label="No training volume data yet">
              <div className="chart-y"><span>20k</span><span>15k</span><span>10k</span><span>5k</span><span>0</span></div>
              <div className="chart-area">
                <i /><i /><i /><i /><i />
                <svg viewBox="0 0 700 190" preserveAspectRatio="none" aria-hidden="true">
                  <path className="chart-placeholder" d="M0 174 L700 174" />
                </svg>
                <div className="chart-days"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span></div>
              </div>
            </div>
          </section>

          <section className="dark-card progress-card" aria-labelledby="progress-title">
            <div className="dark-card__heading">
              <h2 id="progress-title"><Icon name="progress" /> Progress overview</h2>
              <span>This month</span>
            </div>
            <div className="progress-list">
              {['Volume', 'Strength', 'Workouts'].map((label) => (
                <div key={label}><span>{label}</span><strong>—</strong><small>No data</small></div>
              ))}
            </div>
          </section>

          <section className="dark-card recent-card" aria-labelledby="recent-title">
            <h2 id="recent-title">Recent workouts</h2>
            <div className="dark-empty">
              <Icon name="dumbbell" />
              <strong>No completed workouts</strong>
              <p>Your latest sessions will appear here.</p>
            </div>
          </section>

          <section className="dark-card achievement-card" aria-labelledby="achievement-title">
            <h2 id="achievement-title">Achievements</h2>
            <div className="dark-empty">
              <span className="achievement-badge" aria-hidden="true">★</span>
              <strong>Your first milestone awaits</strong>
              <p>Complete workouts to unlock achievements.</p>
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}
